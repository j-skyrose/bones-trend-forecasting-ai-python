import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, math, gc, time, numpy, tensorflow, copy
from numpy.lib.function_base import median
from tensorflow.keras.optimizers import Adam
from tqdm.std import trange
from datetime import datetime
from typing import Dict

from globalConfig import config as gconfig
# import interfaces.predictor as predictorModule
from managers.databaseManager import DatabaseManager
from managers.neuralNetworkManager import NeuralNetworkManager
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.EvaluationDataHandler import EvaluationDataHandler
from structures.EvaluationResultsObj import EvaluationResultsObj
from constants.exceptions import NoData
from managers.dataManager import DataManager
from structures.trainingInstance import TrainingInstance
from managers.inputVectorFactory import InputVectorFactory
from utils.support import Singleton, recdotdict, shortc
from utils.other import determinePrecedingRangeType
from constants.enums import AccuracyAnalysisTypes, AccuracyType, LossAccuracy, PrecedingRangeType, CorrBool

dbm = DatabaseManager()
nnm = NeuralNetworkManager()
ivf: InputVectorFactory = InputVectorFactory()

def breakdownWeightsByInputSection(nn: NeuralNetworkInstance):
    ws = nn.model.get_weights()
    precRange = nn.stats.precedingRange

    # print(ws[0])
    # print(len(ws[0]))
    # print(len(ws[0][0]))
    # print(ws[0][0][0])

    inpVecStats = ivf.getStats()

    wstats = {}
    offset = 0
    for k in tqdm.tqdm(inpVecStats.keys(), desc='Gathering stats'):
        r = wstats[k] = {
            'vals': []
            # 'sum': 0,
            # 'maxPositive': 0,
            # 'maxNegative': 0,
            # 'sumPositive': 0,
            # 'sumNegative': 0,
        }

        newend = inpVecStats[k] * precRange
        for l in tqdm.tqdm(range(offset, newend + offset), leave=False):
            for v in ws[0][l]:
                r['vals'].append(v)
        #         r['sum'] += v
        #         if v > 0:
        #             if v > r['maxPositive']:
        #                 r['maxPositive'] = v
        #             r['sumPositive'] += v
        #         else:
        #             if v < r['maxNegative']:
        #                 r['maxNegative'] = v
        #             r['sumNegative'] += v
        # r['relativeSumPositive'] = r['sumPositive'] / newend if newend != 0 else 1
        # r['relativeSumNegative'] = r['sumNegative'] / newend if newend != 0 else 1
        # r['relativeSum'] = r['sum'] / newend if newend != 0 else 1
        # r['count'] = newend

        offset += newend

        if len(r['vals']) > 0:
            r['count'] = len(r['vals'])
            # r['sum'] = sum(r['vals'])
            # r['relativeSum'] = r['sum'] / len(r['vals']) if len(r['vals']) != 0 else 1
            r['absSum'] = sum([abs(x) for x in r['vals']])
            r['relAbsSum'] = r['absSum'] / len(r['vals']) if len(r['vals']) != 0 else 1
            len13 = math.floor(r['count']/3)
            len23 = math.floor(2*r['count']/3)
            abssum13 = sum([abs(x) for x in (r['vals'])[:len13]])
            abssum23 = sum([abs(x) for x in (r['vals'])[len13:len23]])
            abssum33 = sum([abs(x) for x in (r['vals'])[len23:]])
            r['relAbS13'] = abssum13 / len13
            r['relAbS23'] = abssum23 / (len23-len13)
            r['relAbS33'] = abssum33 / (r['count']-len23)

            # r['max'] = max(r['vals'])
            # r['min'] = min(r['vals'])
            # r['median'] = median(r['vals'])
        del r['vals']
    
    return wstats

def prettyPrintStats(s):
    rowkeys = list(s[list(s.keys())[0]].keys())
    rowstr = '{: <20} {: <15}' + '{: <20.10} '*(len(rowkeys)-1)
    print(rowstr.format('key', *rowkeys))
    for k in s.keys():
        try:
            print(rowstr.format(k, *s[k].values()))
        except IndexError:
            pass    

def analyzeInputSectionWeight(dm: DataManager):
    t, v, ts = dm.getKerasSets()
    inputSize = t[0][0].shape[0]

    stats = []
    for ci in range(c):
        if ci != 0:
            del nn
            gc.collect()

            dm.setupSets(setCount, setSplitTuple, minimumSetsPerSymbol)
            t, v, ts = dm.getKerasSets()

        optimizer = Adam(amsgrad=True)
        layers = [
            { 'units': math.floor(inputSize / 1.5), 'dropout': False, 'dropoutRate': 0.001 },
        ]
        nn = NeuralNetworkInstance.new(ci, optimizer, layers, inputSize)

        ti = TrainingInstance(
            nn, { 'epochs': epochs, 'batchSize': 16 },
            trainingSet=t, validationSet=v, testingSet=ts
        )

        ti.train(2, True)

        stats.append(breakdownWeightsByInputSection(nn))



    # for s in stats:
    #     prettyPrintStats(s)
    avgstats= {}
    for inputGroup in stats[0]:
        avgstats[inputGroup] = {}
        for stat in stats[0][inputGroup]:
            avgstats[inputGroup][stat] = 0
            for s in stats:
                avgstats[inputGroup][stat] += s[inputGroup][stat]
            avgstats[inputGroup][stat] /= len(stats)

    print('### Averages')
    prettyPrintStats(avgstats)

class NetworkAnalysisManager(Singleton):
    nn: NeuralNetworkInstance = None
    dm: DataManager = None
    latestUpdateRows: Dict[AccuracyAnalysisTypes, Dict] = None
    predictor = None
    maxSliceSize = 200000
    accuracies: Dict[AccuracyAnalysisTypes, Dict] = recdotdict({ e: {} for e in PrecedingRangeType })

    def __init__(self, nn, **kwargs) -> None:
        super().__init__()
        self.resetTestTimes()
        self.setNetwork(nn)
    
    def setNetwork(self, nn):
        if type(nn) == NeuralNetworkInstance:
            self.nn = nn
        else:
            self.nn = nnm.get(nn) # id
        self.nn.load()
        self.latestUpdateRows = recdotdict({ AccuracyAnalysisTypes[r.accuracy_type]: { 
            'data_count': r.data_count, 'min_date': r.min_date, 'last_exchange': r.last_exchange, 'last_symbol': r.last_symbol
            } for r in dbm.getAccuracyLastUpdates_basic(networkId=self.nn.id) })

    def resetTestTimes(self):
        self.testing_getKerasSetsTime = 0
        self.testing_evaluateAllTime = 0

    def printTestTimes(self):
        print('    testing_getKerasSetsTime', self.testing_getKerasSetsTime, 'seconds')
        print('    testing_evaluateAllTime', self.testing_evaluateAllTime, 'seconds')

    def outOfDate(self, acctype: AccuracyAnalysisTypes):
        return dbm._getHistoricalDataCount() > self.latestUpdateRows[acctype].data_count

    def bringAccuraciesUpToDate(self, acctype: AccuracyAnalysisTypes):
        datacount = dbm._getHistoricalDataCount()
        haslastticker = self.latestUpdateRows[acctype].last_exchange and self.latestUpdateRows[acctype].last_symbol

        if self.outOfDate(acctype) or haslastticker:
            dm = DataManager.forAnalysis(self.nn, minDate=self.latestUpdateRows[acctype].min_date) ## skip already done tickers?
            _,_, seriesSize = self.nn.inputVectorFactory.getInputSize() ## eval
            accuracies = recdotdict({ e: { c: 0 for c in CorrBool } for e in PrecedingRangeType })
            newaccuracies = copy.deepcopy(accuracies)
            newmindate = list(dm.stockDataHandlers.values())[0].data[-(self.nn.stats.precedingRange+self.nn.stats.followingRange+1)].period_date
            lastexchange = None
            lastsymbol = None
            interrupted = False

            startt = time.time()
            try:
                for (exchange, symbol), sdh in tqdm.tqdm(dm.stockDataHandlers.items(), desc='Updating accuracies'):
                    if haslastticker:
                        if self.latestUpdateRows[acctype].last_exchange == exchange and self.latestUpdateRows[acctype].last_symbol == symbol:
                            haslastticker = False
                            lastexchange = exchange
                            lastsymbol = symbol
                        continue
                    if acctype == AccuracyAnalysisTypes.STOCK:
                        validationSet = dm.getKerasSets(exchange=exchange, symbol=symbol, validationSetOnly=True, verbose=0.5)
                        if len(validationSet) > 0:
                            vhandler: EvaluationDataHandler = EvaluationDataHandler(overallValidationSet=validationSet)

                            if gconfig.testing.predictor:
                                startt = time.time()
                            res = vhandler.evaluateAll(self.nn.model, verbose=0)
                            if gconfig.testing.predictor:
                                self.testing_evaluateAllTime += time.time() - startt
                            
                            dbm.updateStockAccuracyForNetwork(self.nn.id, exchange, symbol, res[AccuracyType.OVERALL][LossAccuracy.ACCURACY], len(validationSet))
                        
                    elif acctype == AccuracyAnalysisTypes.PRECEDING_RANGE:
                        # ## predict method-1 >> ~11% slower than evaluate method-2, perhaps low enough that some fixes to method-1 might help
                        # selectionsEndIndex = 100 if gconfig.testing.enabled else None
                        # anchorDates = [sdh.data[di].period_date for di in sdh.selections]
                        # if gconfig.testing.enabled: anchorDates = anchorDates[:selectionsEndIndex]
                        # predictions = predictorModule.Predictor.predict(kexchange, symbol, anchorDates=anchorDates, network=nn, verbose=0)

                        # for dindex in tqdm.tqdm(sdh.selections[:selectionsEndIndex], desc='Predicting ' + str(key)):
                        #     prectype = self.__determinePrecedingRangeType(sdh.data[dindex - nn.stats.precedingRange:dindex])
                        #     # prediction = predictorModule.Predictor.predict(kexchange, symbol, sdh.data[dindex].period_date, network=nn, verbose=0)
                        #     dt, prediction = predictions[dindex-nn.stats.precedingRange]
                        #     try:
                        #         change = (sdh.data[dindex + nn.stats.followingRange].low / sdh.data[dindex - 1].high) - 1
                        #     except ZeroDivisionError:
                        #         change = 0
                        #     actual = 1 if change >= nn.stats.changeThreshold else 0
                        #     if prediction == actual:    accuracies[prectype][CorrBool.CORRECT] += 1
                        #     else:                       accuracies[prectype][CorrBool.INCORRECT] += 1
                        # ## predict end
                        pass
                        # ## evaluate method-2 >> ~2900% slower than method-3
                        # ksets = dm.getKerasSets(validationSetOnly=True, exchange=exchange, symbol=symbol, verbose=0.5)
                        # for dindex in trange(len(ksets[1]), desc='Evaluating ' + exchange + ':' + symbol, leave=False):
                        #     prectype = determinePrecedingRangeType(sdh.data[dindex:dindex + self.nn.stats.precedingRange])
                
                        #     oup = numpy.array([ksets[1][dindex]])
                        #     ndprime = ksets[0][1][dindex]
                        #     nd2 = numpy.reshape(ndprime, (1, self.nn.stats.precedingRange, seriesSize))
                        #     inp = [tensorflow.experimental.numpy.vstack(numpy.reshape(ksets[0][0][dindex], (1, ksets[0][0][dindex].size))), nd2]
                        #     _, accuracy = self.nn.model.evaluate(inp, oup, verbose=0)
                        #     if accuracy == 1:   accuracies[prectype][CorrBool.CORRECT] += 1
                        #     else:               accuracies[prectype][CorrBool.INCORRECT] += 1
                        # ## evaluate2 end
                        pass
                        ## evaluate method-3
                        ksets = dm.getKerasSets(validationSetOnly=True, exchange=exchange, symbol=symbol, verbose=0.5)
                        indexgroups = recdotdict({ e: [] for e in PrecedingRangeType })
                        for dindex in trange(len(ksets[1]), desc='Evaluating ' + exchange + ':' + symbol, leave=False):
                            prectype = determinePrecedingRangeType(sdh.data[dindex:dindex + self.nn.stats.precedingRange])
                            indexgroups[prectype].append(dindex)
                        for p in PrecedingRangeType:
                            if len(indexgroups[p]) == 0: continue
                            oup = numpy.array([ ksets[1][i] for i in indexgroups[p]])
                            inp = [  
                                tensorflow.experimental.numpy.vstack(numpy.reshape( [ksets[0][0][i] for i in indexgroups[p]],  (len(indexgroups[p]), ksets[0][0][dindex].size))),
                                numpy.reshape( [ksets[0][1][i] for i in indexgroups[p]],  (len(indexgroups[p]), self.nn.stats.precedingRange, seriesSize))
                            ]

                            _, accuracy = self.nn.model.evaluate(inp, oup, verbose=0)
                            correct = round(accuracy * len(indexgroups[p]))
                            newaccuracies[p][CorrBool.CORRECT] += correct
                            newaccuracies[p][CorrBool.INCORRECT] += len(indexgroups[p]) - correct
                        accuracies = copy.deepcopy(newaccuracies) ## ensure ticker is completely evaluated before adding to running counts, in case of interrupt
                        ## evaluate3 end

                    lastexchange = exchange
                    lastsymbol = symbol

            except (KeyboardInterrupt, Exception) as ex:
                print('interrupted:', ex)
                interrupted = True

            if gconfig.testing.enabled: 
                print('taken:', time.time() - startt)
                for p in PrecedingRangeType:
                    print(p.value, accuracies[p])
        
            if acctype == AccuracyAnalysisTypes.PRECEDING_RANGE:
                dbm.updatePrecedingRangeAccuraciesForNetwork(self.nn.id, accuracies)

            if interrupted:
                dbm.updateAccuraciesLastUpdated(self.nn.id, acctype, datacount, lastExchange=lastexchange, lastSymbol=lastsymbol)
            else:
                dbm.updateAccuraciesLastUpdated(self.nn.id, acctype, datacount, minDate=newmindate)

        else:
            print(acctype.value, 'accuracies already up to date')

    def getStockAccuracy(self, exchange, symbol) -> float:
        acctype = AccuracyAnalysisTypes.STOCK
        ticker = (exchange, symbol)
        if ticker not in self.accuracies[acctype].keys():
            if self.outOfDate(acctype):
                self.bringAccuraciesUpToDate(acctype)
            acc = dbm.getNetworkAccuracy(self.nn.id, acctype, exchange, symbol)
            self.accuracies[acctype][ticker] = acc
        
        return self.accuracies[acctype][ticker]

    def countPrecedingRangeTypes(self):
        counts = recdotdict({ e: 0 for e in PrecedingRangeType })
        for key, sdh in self.dm.stockDataHandlers.items():
            for dindex in trange(len(sdh.data), desc='Evaluating ' + str(key)):
                prectype = determinePrecedingRangeType(sdh.data[dindex:dindex + nn.stats.precedingRange])
                counts[prectype] += 1
        print(counts)

    def getStockPrecedingRangeTypesAccuracy(self, prectype: PrecedingRangeType):
        acctype = AccuracyAnalysisTypes.PRECEDING_RANGE
        if prectype not in self.accuracies[acctype].keys():
            if self.outOfDate(acctype):
                self.bringAccuraciesUpToDate(acctype)
            acc = dbm.getNetworkAccuracy(self.nn.id, acctype, prectype)
            self.accuracies[acctype][prectype] = acc
        
        return self.accuracies[acctype][prectype]

if __name__ == '__main__':

    nam = NetworkAnalysisManager(1641959005)
    nam.bringAccuraciesUpToDate(AccuracyAnalysisTypes.PRECEDING_RANGE)

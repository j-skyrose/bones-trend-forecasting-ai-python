
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, math, gc
from numpy.lib.function_base import median
from tensorflow.keras.optimizers import Adam
from datetime import datetime

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
from constants.enums import AccuracyType, LossAccuracy

nnm = NeuralNetworkManager()
ivf: InputVectorFactory = InputVectorFactory()

def breakdownWeightsByInputSection(nn: NeuralNetworkInstance):
    ws = nn.model.get_weights()
    precRange = nn.stats.precedingRange

    # print(ws[0])
    # print(len(ws[0]))
    # print(len(ws[0][0]))
    # print(ws[0][0][0])

    ivs = ivf.getStats()

    wstats = {}
    offset = 0
    for k in tqdm.tqdm(ivs.keys(), desc='Gathering stats'):
        r = wstats[k] = {
            'vals': []
            # 'sum': 0,
            # 'maxPositive': 0,
            # 'maxNegative': 0,
            # 'sumPositive': 0,
            # 'sumNegative': 0,
        }

        newend = ivs[k] * precRange
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

class Analyzer(Singleton):
    nn: NeuralNetworkInstance = None
    dm: DataManager = None
    maxSliceSize = 200000

    def __init__(self, nn, **kwargs) -> None:
        super().__init__()
        self.nn = nn
        self.dm = DataManager.forAnalysis(nn, **kwargs)

    def getStockAccuracy(self, exchange, symbol, nn: NeuralNetworkInstance=None) -> EvaluationResultsObj:
        validationSet = self.dm.getKerasSets(exchange=exchange, symbol=symbol, validationDataOnly=True, verbose=0) if nn.stats.accuracyType == AccuracyType.OVERALL else []
        negativeValidationSet = self.dm.getKerasSets(exchange=exchange, symbol=symbol, validationDataOnly=True, verbose=0, classification=1) if nn.stats.accuracyType == AccuracyType.NEGATIVE else []
        positiveValidationSet = self.dm.getKerasSets(exchange=exchange, symbol=symbol, validationDataOnly=True, verbose=0, classification=2) if nn.stats.accuracyType == AccuracyType.POSITIVE else []
        if len(validationSet[0]) > 0 or len(negativeValidationSet) > 0 or len(positiveValidationSet) > 0:
            vhandler: EvaluationDataHandler = EvaluationDataHandler(validationSet, negativeValidationSet=negativeValidationSet, positiveValidationSet=positiveValidationSet)
            res = vhandler.evaluateAll(getattr(shortc(nn, self.nn), 'model'), verbose=0)
            # print(exchange, symbol, ':', res[AccuracyType.OVERALL][LossAccuracy.ACCURACY] *100, '%')
            return res
        else:
            # print(exchange, symbol, ': no data')
            # return -1
            raise NoData

        

if __name__ == '__main__':
    starttime = datetime.now()
    print('starting')

    ## real
    # setCount = 25000
    # minimumSetsPerSymbol = 10
    # epochs = 50
    ## testing
    setCount = 250
    minimumSetsPerSymbol = 0
    epochs = 5

    setSplitTuple = (0.95,0.05)

    # c = 5
    # dm = DataManager(400, 20, setCount=setCount, threshold=0.2, setSplitTuple=setSplitTuple, minimumSetsPerSymbol=minimumSetsPerSymbol)
    # t, v, ts = dm.getKerasSets()
    # inputSize = t[0][0].shape[0]


    ## breakdown by symbol
    maxSize = 200000
    nn = nnm.get(1623156322)
    dm: DataManager = DataManager.forAnalysis(nn, exchanges=['NYSE'])
    
    for s in dm.symbolList:
        _, validationSet, _ = dm.getKerasSets(exchange=s.exchange, symbol=s.symbol, verbose=0)
        if len(validationSet[0]) > 0:
            vhandler: EvaluationDataHandler = EvaluationDataHandler(validationSet)
            res = vhandler.evaluateAll(nn.model, verbose=0)
            print(s.exchange, s.symbol, ':', res[AccuracyType.OVERALL][LossAccuracy.ACCURACY] *100, '%')
        else:
            print(s.exchange, s.symbol, ': no data')


    ## breakdown by sector?
    # accuracies = []
    # _, validationSet, _ = dm.getKerasSets(maxSize=maxSize)
    # while len(validationSet) > 0:
    #     print('Analyzing slice', len(accuracies), '...')
    #     # inputSize = testingSet[0][0].shape[0]
    #     vhandler: EvaluationDataHandler = EvaluationDataHandler(validationSet)
    #     res = vhandler.evaluateAll(nn.model)
    #     accuracies.append(res[AccuracyType.OVERALL][LossAccuracy.ACCURACY])
        
    #     _, validationSet, _ = dm.getKerasSets(maxSize=maxSize, index=len(accuracies))

    # print(accuracies)
    # print(sum(accuracies) / len(accuracies) * 100, '%')



    # res = nn.predict(dm.instances[list(dm.instances.keys())[0]].getInputVector())
    # print(res)

    # correct = 0
    # for k in list(dm.instances.keys()):
    #     i = dm.instances[k]
    #     if i.getOutputVector() == nn.predict(i.getInputVector()):
    #         correct += 1
    
    # print(correct, 'correct out of', len(dm.instances.keys()))
    # print(correct / len(dm.instances.keys()) * 100, '%')


    
    endtime = datetime.now()
    print('Start:', starttime)
    print('End:', endtime)
    print('Elapsed:', endtime-starttime)

    print('done')

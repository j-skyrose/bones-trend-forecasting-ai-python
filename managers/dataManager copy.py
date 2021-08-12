import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import random, math, numpy, tqdm, time, pickle
from tensorflow import keras
from timeit import default_timer as timer
from multiprocessing import Pool, cpu_count
from datetime import date
from typing import List

from globalConfig import config
from constants.enums import SeriesType, SetType
from utils.support import Singleton, recdotdict
from constants.values import testingSymbols, unusableSymbols
from managers.databaseManager import DatabaseManager
from structures.stockDataHandler import StockDataHandler
from structures.dataPointInstance import DataPointInstance, numOutputClasses, positiveClass, negativeClass
from structures.api.googleTrends.request import GoogleAPI

DEBUG = True
MULTITHREAD = False
picklepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debugpickle.pkl')
dumppickles = False
usepickles = False
picklepoint_normalizationdata = False
picklepoint_normalizationdata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'picklepoint_normalizationdata.pkl')
picklepoint_selectedinstances = False
picklepoint_selectedinstances_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'picklepoint_selectedinstances.pkl')

dbi = DatabaseManager()

def setupHandlerWorker(
    processid, 
    symbolList: List[dict], 
    seriesType: SeriesType, 
    normalizationMaxes: List[float], 
    precedingRange: int, 
    followingRange: int
) -> List[StockDataHandler]:
    # try:
        handlers = []
        for s in tqdm.tqdm(symbolList, desc='Creating handlers') if processid == 0 else symbolList:   
            if (s.exchange, s.symbol) in testingSymbols + unusableSymbols: continue
            data = dbi.getData(s.exchange, s.symbol, seriesType)
            if len(data) >= precedingRange + followingRange + 1:
                handlers.append(StockDataHandler(
                    s,
                    seriesType,
                    data,
                    *normalizationMaxes,
                    precedingRange,
                    followingRange
                ))
        return handlers
    # except:
    #     print("Unexpected error:", sys.exc_info()[0])

class DataManager(Singleton):
    handlers = []
    selectedInstances = []
    # unselectedInstances = []
    unselectedInstances = {}
    trainingInstances = []
    validationInstances = []
    testingInstances = []

    def __init__(self, seriesType=SeriesType.DAILY):
        self.kerasSetCaches = {}

        ## initialize VIX data
        self.vixRef = {r.date: r for r in dbi.getVIXData()}

        self.seriesType = seriesType
        normalizationColumns, normalizationMaxes, self.symbolList = dbi.getNormalizationData(seriesType)
        norminfo = {}
        for c in range(len(normalizationColumns)):
            norminfo[normalizationColumns[c]] = normalizationMaxes[c]
        self.normalizationInfo = recdotdict(norminfo)

    def _buildInstanceSet_setupInstances(self, precedingRange, followingRange):
        handlers = []
        instances = []
        normalizationMaxes = [x for x in self.normalizationInfo.values()]
        if MULTITHREAD:
            ### multi-process setup of handlers, appears to get stuck once all processes are complete and starts chugging CPU, taking same or more time as sequential. Does not run
            s = timer()
            with Pool() as pool:
                self.handlers = pool.starmap(setupHandlerWorker, [
                        (
                            i,
                            self.symbolList[i::cpu_count()],
                            self.seriesType,
                            normalizationMaxes,
                            precedingRange,
                            followingRange,
                            # 3
                        ) for i in range(cpu_count())
                    ])
            handlers = [i for sublist in self.handlers for i in sublist]    # flatten back into a single list
            e = timer()
            if DEBUG: print(len(self.handlers), f'handlers setup in {e-s} seconds')
        else:
            handlers = setupHandlerWorker(0, self.symbolList, self.seriesType, normalizationMaxes, precedingRange, followingRange)

        if DEBUG: print(len(self.handlers), 'handlers setup')
        ## handlers initialized
        ## exclusions also done (price/volume limits, topicID presence, etc.)

        if not usepickles or not picklepoint_selectedinstances:
            ## initialize instances
            for h in tqdm.tqdm(self.handlers, desc='Initializing instances'):
                for s in h.getAvailableSelections():
                    # self.unselectedInstances.append(self._buildInstance(h, s))
                    instances[(h.symbolData.exchange, h.symbolData.symbol, h.data[s].date)] = self._buildInstance(h, s)    

        return handlers, instances

    def buildInstanceSet(self, precedingRange, followingRange, setCount, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0):
        handlers, unselectedInstances = self._buildInstanceSet_setupInstances(precedingRange, followingRange)
        if not usepickles or not picklepoint_selectedinstances:
            ## begin selecting instances
            ## cover minimums
            # if not usepickle:
            movingKeyStart = 0
            keys = list(self.unselectedInstances)
            for h in self.handlers: 
            # for h in tqdm.tqdm(self.handlers, desc='Covering minimums'):
                # selectIndexes = random.sample(
                #     [x for x in range( len(self.unselectedInstances) - len(h.getAvailableSelections()), len(self.unselectedInstances))],
                #     min(minimumSetsPerSymbol, len(h.getAvailableSelections()))
                # )
                # for i in sorted(selectIndexes, reverse=True):
                #     self.selectedInstances.append(self.unselectedInstances.pop(i))

                availableCount = len(h.getAvailableSelections())
                sampleSize = min(minimumSetsPerSymbol, availableCount)
                # print(movingKeyStart, availableCount, sampleSize, len(list(self.unselectedInstances)))
                selectKeys = random.sample(
                    keys[movingKeyStart : movingKeyStart + availableCount],
                    sampleSize
                )
                movingKeyStart += availableCount # - sampleSize
                for k in selectKeys:
                    self.selectedInstances.append(self.unselectedInstances.pop(k))
            if DEBUG: 
                print(len(self.selectedInstances), 'instances selected to cover minimums')
                print(len(self.unselectedInstances), 'instances available for remaining selection')

            ## check balance
            psints, nsints = self._getInstancesByClass(self.selectedInstances)
            puints, nuints = self._getInstancesByClass(self.unselectedInstances.values())
            # select remaining
            if len(self.selectedInstances) < setCount:
                pusamplesize = int(min(len(puints), setCount / 2 - len(psints)) if setCount / 2 - len(psints) > 0 else len(puints))
                self.selectedInstances.extend(random.sample(puints, pusamplesize))
                nusamplesize = int(min(len(nuints), setCount - len(self.selectedInstances)) if setCount - len(self.selectedInstances) > 0 else len(nuints))
                self.selectedInstances.extend(random.sample(nuints, nusamplesize))
            else:
                if DEBUG: print('Warning: setCount too low for minimum sets per symbol')
            if DEBUG:
                psints, nsints = self._getInstancesByClass(self.selectedInstances)
                print('All instances selected\nFinal balance:', len(psints), '/', len(nsints))

            if len(self.selectedInstances) < setCount: raise IndexError('Not enough sets available: %d vs %d' % (len(self.selectedInstances) + len(self.unselectedInstances), setCount))
            ## instance selection done
            
            if dumppickles: 
                print('pickling... ', end='')
                with open(picklepoint_selectedinstances_path, 'wb') as f: pickle.dump(self.selectedInstances, f, protocol=4)
                print('done')
        else:
            with open(picklepoint_selectedinstances_path,'rb') as f: 
                print('loading selected instances pickle... ', end='')
                self.selectedInstances = pickle.load(f)
                print('done')
                for i in self.selectedInstances:
                    i.setVIXRef(self.vixRef)


        ## retrieve Google interests for each selected set
        if config.feature.googleInterests.enabled:
            gapi = GoogleAPI()
            dg = True
            dg2 = True
            for s in tqdm.tqdm(self.selectedInstances, desc='Getting Google interests data'):
                dset = s.handler.getPrecedingSet(s.index)
                start_dt = date.fromisoformat(dset[0].date)
                end_dt = date.fromisoformat(dset[-1].date)
                
                if dg:
                    print('sdata', s.handler.symbolData)
                    dg = False
                gdata = gapi.get_historical_interest(s.handler.symbolData.google_topic_id, 
                    year_start=start_dt.year, month_start=start_dt.month, day_start=start_dt.day,
                    year_end=end_dt.year, month_end=end_dt.month, day_end=end_dt.day
                )
                if dg2:
                    print(gdata)
                    dg2 = False

                s.setGoogleInterestData(gdata)


        ## shuffle and distribute instances
        random.shuffle(self.selectedInstances)
        c1, c2 = self._getInstancesByClass(self.selectedInstances)
        # b = self._checkSelectedBalance()
        trnStop = setSplitTuple[0]
        vldStop = setSplitTuple[1] + trnStop
        if DEBUG: print('stops', trnStop, vldStop)
        trainingSet = c1[:math.floor(trnStop*len(c1))] + c2[:math.floor(trnStop*len(c2))]
        validationSet = c1[math.floor(trnStop*len(c1)):math.floor(vldStop*len(c1))] + c2[math.floor(trnStop*len(c2)):math.floor(vldStop*len(c2))]
        testingSet = c1[math.floor(vldStop*len(c1)):] + c2[math.floor(vldStop*len(c2)):]
        if DEBUG: print('Sets split into', len(self.trainingSet), '/', len(self.validationSet), '/', len(self.testingSet))

        return trainingSet, validationSet, testingSet

    def buildInstanceSetFromSave(self, id, setid=1):
        dataset = dbi.getDataSet(id, setid)
        trainingSet = [s for s in dataset if s.set_type == SetType.TRAINING.name]
        validationSet = [s for s in dataset if s.set_type == SetType.VALIDATION.name]
        testingSet = [s for s in dataset if s.set_type == SetType.TESTING.name]

        return trainingSet, validationSet, testingSet

    def __init__(self,
        seriesType,
        precedingRange,
        followingRange,
        setSplitTuple,
        threshold=0.1,
        normalizationColumns=[],
        normalizationMaxes=[],
        symbolList=[],
        trainingSet=[],
        validationSet=[],
        testingSet=[]
    ):
        self.seriesType = seriesType
        self.precedingRange = precedingRange
        self.followingRange = followingRange
        self.setSplit = setSplitTuple
        self.threshold = threshold

        ## initialize VIX data
        self.vixRef = {r.date: r for r in dbi.getVIXData()}

        ## begin initializing (stockData)handlers
        if usepickles and (picklepoint_normalizationdata or picklepoint_selectedinstances):
            print('loading normalization data pickle... ', end='')
            with open(picklepoint_normalizationdata_path,'rb') as f: 
                self.normalizationInfo, self.handlers = pickle.load(f)
            print('done')
        else:
            if not (normalizationColumns and normalizationMaxes and symbolList):
                normalizationColumns, normalizationMaxes, symbolList = dbi.getNormalizationData(seriesType)
                print('got normalization data, lists')

            norminfo = {}
            for c in range(len(normalizationColumns)):
                norminfo[normalizationColumns[c]] = normalizationMaxes[c]
            self.normalizationInfo = recdotdict(norminfo)


            if MULTITHREAD:
                ### multi-process setup of handlers, appears to get stuck once all processes are complete and starts chugging CPU, taking same or more time as sequential. Does not run
                s = timer()
                with Pool() as pool:
                    self.handlers = pool.starmap(setupHandlerWorker, [
                            (
                                i,
                                symbolList[i::cpu_count()],
                                self.seriesType,
                                normalizationMaxes,
                                precedingRange,
                                followingRange,
                                # 3
                            ) for i in range(cpu_count())
                        ])
                self.handlers = [i for sublist in self.handlers for i in sublist]    # flatten back into a single list
                e = timer()
                if DEBUG: print(len(self.handlers), f'handlers setup in {e-s} seconds')
            else:
                self.handlers = setupHandlerWorker(0, symbolList, seriesType, normalizationMaxes, precedingRange, followingRange)
                if dumppickles:
                    print('pickling... ', end='')
                    with open(picklepoint_normalizationdata_path, 'wb') as f: pickle.dump([self.normalizationInfo, self.handlers], f, protocol=4)
                    print('done')

        if DEBUG: print(len(self.handlers), 'handlers setup')
        ## handlers initialized
        ## exclusions also done (price/volume limits, topicID presence, etc.)

        if not usepickles or not picklepoint_selectedinstances:
            ## initialize instances
            for h in tqdm.tqdm(self.handlers, desc='Initializing instances'):
                for s in h.getAvailableSelections():
                    # self.unselectedInstances.append(self._buildInstance(h, s))
                    self.unselectedInstances[(h.symbolData.exchange, h.symbolData.symbol, h.data[s].date)] = self._buildInstance(h, s)

    @classmethod
    def new(cls,
        seriesType,
        precedingRange,
        followingRange,
        setCount,
        setSplitTuple=(1/3,1/3),
        threshold=0.1,
        minimumSetsPerSymbol=5
    ):
        c = cls(
            seriesType,
            precedingRange,
            followingRange,
            setSplitTuple,
            threshold
        )
        
        if not usepickles or not picklepoint_selectedinstances:
            ## begin selecting instances
            ## cover minimums
            # if not usepickle:
            movingKeyStart = 0
            keys = list(c.unselectedInstances)
            for h in c.handlers: 
            # for h in tqdm.tqdm(c.handlers, desc='Covering minimums'):
                # selectIndexes = random.sample(
                #     [x for x in range( len(c.unselectedInstances) - len(h.getAvailableSelections()), len(c.unselectedInstances))],
                #     min(minimumSetsPerSymbol, len(h.getAvailableSelections()))
                # )
                # for i in sorted(selectIndexes, reverse=True):
                #     c.selectedInstances.append(c.unselectedInstances.pop(i))

                availableCount = len(h.getAvailableSelections())
                sampleSize = min(minimumSetsPerSymbol, availableCount)
                # print(movingKeyStart, availableCount, sampleSize, len(list(c.unselectedInstances)))
                selectKeys = random.sample(
                    keys[movingKeyStart : movingKeyStart + availableCount],
                    sampleSize
                )
                movingKeyStart += availableCount # - sampleSize
                for k in selectKeys:
                    c.selectedInstances.append(c.unselectedInstances.pop(k))
            if DEBUG: 
                print(len(c.selectedInstances), 'instances selected to cover minimums')
                print(len(c.unselectedInstances), 'instances available for remaining selection')

            ## check balance
            psints, nsints = c._getInstancesByClass(c.selectedInstances)
            puints, nuints = c._getInstancesByClass(c.unselectedInstances.values())
            # select remaining
            if len(c.selectedInstances) < setCount:
                pusamplesize = int(min(len(puints), setCount / 2 - len(psints)) if setCount / 2 - len(psints) > 0 else len(puints))
                c.selectedInstances.extend(random.sample(puints, pusamplesize))
                nusamplesize = int(min(len(nuints), setCount - len(c.selectedInstances)) if setCount - len(c.selectedInstances) > 0 else len(nuints))
                c.selectedInstances.extend(random.sample(nuints, nusamplesize))
            else:
                if DEBUG: print('Warning: setCount too low for minimum sets per symbol')
            if DEBUG:
                psints, nsints = c._getInstancesByClass(c.selectedInstances)
                print('All instances selected\nFinal balance:', len(psints), '/', len(nsints))

            if len(c.selectedInstances) < setCount: raise IndexError('Not enough sets available: %d vs %d' % (len(c.selectedInstances) + len(c.unselectedInstances), setCount))
            ## instance selection done
            
            if dumppickles: 
                print('pickling... ', end='')
                with open(picklepoint_selectedinstances_path, 'wb') as f: pickle.dump(c.selectedInstances, f, protocol=4)
                print('done')
        else:
            with open(picklepoint_selectedinstances_path,'rb') as f: 
                print('loading selected instances pickle... ', end='')
                c.selectedInstances = pickle.load(f)
                print('done')
                for i in c.selectedInstances:
                    i.setVIXRef(c.vixRef)


        ## retrieve Google interests for each selected set
        if config.feature.googleInterests.enabled:
            gapi = GoogleAPI()
            dg = True
            dg2 = True
            for s in tqdm.tqdm(c.selectedInstances, desc='Getting Google interests data'):
                dset = s.handler.getPrecedingSet(s.index)
                start_dt = date.fromisoformat(dset[0].date)
                end_dt = date.fromisoformat(dset[-1].date)
                
                if dg:
                    print('sdata', s.handler.symbolData)
                    dg = False
                gdata = gapi.get_historical_interest(s.handler.symbolData.google_topic_id, 
                    year_start=start_dt.year, month_start=start_dt.month, day_start=start_dt.day,
                    year_end=end_dt.year, month_end=end_dt.month, day_end=end_dt.day
                )
                if dg2:
                    print(gdata)
                    dg2 = False

                s.setGoogleInterestData(gdata)


        ## shuffle and distribute instances
        random.shuffle(c.selectedInstances)
        c1, c2 = c._getInstancesByClass(c.selectedInstances)
        # b = c._checkSelectedBalance()
        trnStop = setSplitTuple[0]
        vldStop = setSplitTuple[1] + trnStop
        if DEBUG: print('stops', trnStop, vldStop)
        c.trainingSet = c1[:math.floor(trnStop*len(c1))] + c2[:math.floor(trnStop*len(c2))]
        c.validationSet = c1[math.floor(trnStop*len(c1)):math.floor(vldStop*len(c1))] + c2[math.floor(trnStop*len(c2)):math.floor(vldStop*len(c2))]
        c.testingSet = c1[math.floor(vldStop*len(c1)):] + c2[math.floor(vldStop*len(c2)):]
        if DEBUG: print('Sets split into', len(c.trainingSet), '/', len(c.validationSet), '/', len(c.testingSet))

        return c

    @classmethod
    def fromSave(cls, id, setid=1):
        setinfo = dbi.getSetInfo(id)
        dataset = dbi.getDataSet(id, setid)

        trainingSet = [s for s in dataset if s.set_type == SetType.TRAINING.name]
        validationSet = [s for s in dataset if s.set_type == SetType.VALIDATION.name]
        testingSet = [s for s in dataset if s.set_type == SetType.TESTING.name]

        symbolList = set()
        for s in dataset:
            symbolList.add((s.exchange, s.symbol))

        c = cls(
            dataset[0].series_type,
            setinfo.precedingRange,
            setinfo.followingRange,
            (
                len(trainingSet) / len(dataset),
                len(validationSet) / len(dataset)
            ),
            setinfo.changeThreshold,
            [x.replace('Max', '') for x in setinfo.keys() if 'Max' in x],
            [setinfo[x] for x in setinfo.keys() if 'Max' in x],
            symbolList,
            trainingSet,
            validationSet,
            testingSet
        )

        ## map training/validation/testing sets back to their instance lists
        c.trainingSet = []
        c.validationSet = []
        c.testingSet = []
        def _findSetInstances(tset, cset):
            # for s in tqdm.tqdm(tset, desc='For data set'):
            for s in tset:
                # i = __findInstance(s)
                i = c.unselectedInstances[(s.exchange, s.symbol, s.date)]
                if i:
                    c.selectedInstances.append(i)
                    # c.unselectedInstances.remove(i)
                    del c.unselectedInstances[(i.handler.exchange, i.handler.symbol, i.handler.data[i.index].date)]
                    cset.append(i)
                else:
                    print('instance not found', s)

        ## decommission
        def __findInstance(aset):
            for i in c.unselectedInstances:
                if aset.exchange == i.handler.exchange and aset.symbol == i.handler.symbol:

                    # print(aset.date, i.handler.data[i.index].date, i.index)
                    if i.handler.data[i.index].date == aset.date:
                        return i

                    # index = 0
                    # for d in tqdm.tqdm(i.handler.data, desc='Checking handler data'):
                    #     if aset.date == d.date and index == i.index:
                    #         return i
                    #     index += 1
        
        _findSetInstances(trainingSet, c.trainingSet)
        _findSetInstances(validationSet, c.validationSet)
        _findSetInstances(testingSet, c.testingSet)

        return c


    def _buildInstance(self, handler, index):
        d = handler.data
        try:
            change = 1 - d[index + self.followingRange].low / d[index - 1].high
        except ZeroDivisionError:
            change = 0

        return DataPointInstance(handler, index, self.vixRef,
            positiveClass if change >= 1 + self.threshold else negativeClass
        )

    def _checkSelectedBalance(self):
        pclass, nclass = self._getInstancesByClass(self.selectedInstances)
        return len(pclass) / (len(pclass) + len(nclass))

    def _getInstancesByClass(self, ins):
        pclass = []
        nclass = []
        for i in ins:
            try:
                if i.outputClass == positiveClass: pclass.append(i)
                else: nclass.append(i)
            except:
                print(i)
        return pclass, nclass

    def getKerasSets(self, classification=0, validationDataOnly=False):
        def constrList_helper(set: List[DataPointInstance], isInput):
            retList = []
            for i in tqdm.tqdm(set, desc='Building input vector array') if isInput else set:
                retList.append(i.getInputVector() if isInput else i.getOutputVector())
            return retList

        # def constrList_multicore(set, isInput):
        #     MAX_WORKERS = 4
        #     retList = []
        #     stime = int(time.time())
        #     with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as execu:
        #         splice = len(set)/MAX_WORKERS
        #         splits = [set[0 + int(splice*i) : int(splice*(i+1))] for i in range(MAX_WORKERS)]
        #         future_retlist = {execu.submit(constrList_helper, splits[i], isInput): i for i in range(MAX_WORKERS)}
        #         for future in concurrent.futures.as_completed(future_retlist):
        #             retList.append(future.result())
        #     print("Spent ", str(int(time.time()) - stime),' seconds looping in constrList')
        #     return numpy.asarray(retList)

        def constrList(set: List, isInput: bool) -> numpy.array:
            # USE_MULTICORE = False
            # USE_MULTICORE = True
            # if (USE_MULTICORE): return constrList_multicore(set, isInput)
            # else: 
            return numpy.asarray(constrList_helper(set, isInput))

        def constructDataSet(lst):
            return [constrList(lst, True), keras.utils.to_categorical(constrList(lst, False), num_classes=numOutputClasses)]

        trainingSet = self.trainingSet
        validationSet = self.validationSet
        testingSet = self.testingSet
        ## only select from certain class if specified
        if classification:
            trainingSet = self._getInstancesByClass(self.trainingSet)[classification-1]
            validationSet = self._getInstancesByClass(self.validationSet)[classification-1]
            testingSet = self._getInstancesByClass(self.testingSet)[classification-1]


        validationData = constructDataSet(validationSet)
        if validationDataOnly: return validationData
        trainingData = constructDataSet(trainingSet)
        testingData = constructDataSet(testingSet)

        return [trainingData, validationData, testingData]

    def save(self, networkId, setId=None):
        dbi.saveDataSet(networkId, self.trainingSet, self.validationSet, self.testingSet, setId)


if __name__ == '__main__':
    s = DataManager.new(
        SeriesType.DAILY,
        90,
        30,
        250000,
        setSplitTuple=(1/3,1/3),
        threshold=0.1
    )
    s.getKerasSets(classification=1)

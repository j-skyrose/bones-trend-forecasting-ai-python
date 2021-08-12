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

from globalConfig import config as gconfig
from constants.enums import SeriesType, SetType
from utils.support import Singleton, recdotdict, shortc
from constants.values import testingSymbols, unusableSymbols
from managers.stockDataManager import StockDataManager
from managers.databaseManager import DatabaseManager
from managers.vixManager import VIXManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
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

dbm: DatabaseManager = DatabaseManager()

# def setupHandlerWorker(
#     processid, 
#     symbolList: List[dict], 
#     seriesType: SeriesType, 
#     normalizationMaxes: List[float], 
#     precedingRange: int, 
#     followingRange: int
# ) -> List[StockDataHandler]:
#     # try:
#         handlers = []
#         for s in tqdm.tqdm(symbolList, desc='Creating handlers') if processid == 0 else symbolList:
#             if (s.exchange, s.symbol) in testingSymbols + unusableSymbols: continue
#             data = dbm.getData(s.exchange, s.symbol, seriesType)
#             if len(data) >= precedingRange + followingRange + 1:
#                 handlers.append(StockDataHandler(
#                     s,
#                     seriesType,
#                     data,
#                     *normalizationMaxes,
#                     precedingRange,
#                     followingRange
#                 ))
#         return handlers
#     # except:
#     #     print("Unexpected error:", sys.exc_info()[0])



## each session should only rely on one (precedingRange, followingRange) combination due to the way the handlers are setup
## not sure how new exchange/symbol handler setups would work with normalization info, if not initialized when datamanager is created

class DataManager():
    stockDataManager: StockDataManager = None
    instances: dict = {}
    selectedInstances = []
    # unselectedInstances = []
    unselectedInstances = {}
    trainingInstances = []
    validationInstances = []
    testingInstances = []
    inputVectorFactory = None

    def __init__(self, 
        precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, threshold=0,
        setCount=None, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0, inputVectorFactory=InputVectorFactory(),
        normalizationInfo={}, symbolList=[],
        analysis=False,
        **kwargs
        # precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, setCount=None, threshold=0, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0, inputVectorFactory=InputVectorFactory(),
        # neuralNetwork: NeuralNetworkInstance=None, exchanges=[], excludeExchanges=[], sectors=[], excludeSectors=[]
    ):
        self.config = inputVectorFactory.config
        self.inputVectorFactory = inputVectorFactory
        self.precedingRange = precedingRange
        self.followingRange = followingRange
        self.seriesType = seriesType
        self.threshold = threshold
        self.setCount = setCount
        self.kerasSetCaches = {}
        self.normalizationInfo = recdotdict(normalizationInfo)
        self.symbolList = symbolList

        ## pull and setup financial reports ref
        ## todo
        self.financialDataHandler

        self.stockDataManager = StockDataManager(
            self.normalizationInfo,
            self.symbolList,
            self.precedingRange,
            self.followingRange,
            self.seriesType,
            self.inputVectorFactory,
            self.threshold
        )

        if setCount is not None:
            self.setupSets(self.setCount, setSplitTuple, minimumSetsPerSymbol)
        elif analysis:
            # if gconfig.testing.enabled:
            #     c = 5000
            #     for x in list(self.stockDataManager.instances.keys()):
            #         if c and self.stockDataManager.instances[x].handler.symbolData.exchange == gconfig.testing.exchange:
            #             c -= 1
            #         elif len(self.stockDataManager.instances) == c:
            #             break
            #         else:
            #             self.stockDataManager.instances.pop(x)
            self.setupSets(len(self.stockDataManager.instances.values()), (0,1))

    @classmethod
    def forTraining(cls, seriesType=SeriesType.DAILY, **kwargs):
        normalizationColumns, normalizationMaxes, symbolList = dbm.getNormalizationData(seriesType)
        
        normalizationInfo = {}
        for c in range(len(normalizationColumns)):
            normalizationInfo[normalizationColumns[c]] = normalizationMaxes[c]
        
        return cls(
            seriesType=seriesType,
            normalizationInfo=normalizationInfo, symbolList=symbolList, 
            **kwargs
        )

    @classmethod
    def forAnalysis(cls, nn: NeuralNetworkInstance, **kwargs):
        normalizationInfo = nn.stats.getNormalizationInfo()
        _, _, symbolList = dbm.getNormalizationData(nn.stats.seriesType, normalizationInfo=normalizationInfo, **kwargs) #exchanges=exchanges, excludeExchanges=excludeExchanges, sectors=sectors, excludeSectors=excludeSectors)

        return cls(
            precedingRange=nn.stats.precedingRange, followingRange=nn.stats.followingRange, seriesType=nn.stats.seriesType, threshold=nn.stats.changeThreshold, inputVectorFactory=nn.inputVectorFactory,
            normalizationInfo=normalizationInfo, symbolList=symbolList,
            analysis=True,
            **kwargs
        )

    def setupSets(self, setCount, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0):
        self.unselectedInstances = self.stockDataManager.instances.values()
        self.selectedInstances = []

        if DEBUG: print('Selecting', setCount, 'instances')

        ## cover minimums
        if minimumSetsPerSymbol > 0:
            self.unselectedInstances = []
            for h in self.stockDataManager.getAll():
                available = h.getAvailableSelections()
                sampleSize = min(minimumSetsPerSymbol, len(available))
                if sampleSize > 0:
                    selectDates = [h.data[d].date for d in available]
                    # print('preshuffle')
                    # print(available)
                    # print(sampleSize)
                    # print(selectDates)
                    random.shuffle(selectDates)
                    for d in selectDates[:sampleSize]:
                        self.selectedInstances.append(self.stockDataManager.instances[(h.symbolData.exchange, h.symbolData.symbol, d)])
                    for d in selectDates[sampleSize:]:
                        self.unselectedInstances.append(self.stockDataManager.instances[(h.symbolData.exchange, h.symbolData.symbol, d)])
            if DEBUG: 
                print(len(self.selectedInstances), 'instances selected to cover minimums')
                print(len(self.unselectedInstances), 'instances available for remaining selection')

        ## check balance
        psints, nsints = self._getInstancesByClass(self.selectedInstances)
        puints, nuints = self._getInstancesByClass(self.unselectedInstances)
        if DEBUG: print('sel rem', len(self.selectedInstances), setCount, len(self.selectedInstances) < setCount)
        # select remaining
        if len(self.selectedInstances) < setCount:
            if DEBUG:
                print('Positive selected instances', len(psints))
                print('Negative selected instances', len(nsints))
                print('Available positive instances', len(puints))
                print('Available negative instances', len(nuints))

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

        ## retrieve Google interests for each selected set
        if self.config.feature.googleInterests.enabled:
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
        self.trainingSet = c1[:math.floor(trnStop*len(c1))] + c2[:math.floor(trnStop*len(c2))]
        self.validationSet = c1[math.floor(trnStop*len(c1)):math.floor(vldStop*len(c1))] + c2[math.floor(trnStop*len(c2)):math.floor(vldStop*len(c2))]
        self.testingSet = c1[math.floor(vldStop*len(c1)):] + c2[math.floor(vldStop*len(c2)):]
        if DEBUG: print('Sets split into', len(self.trainingSet), '/', len(self.validationSet), '/', len(self.testingSet))

        # return trainingSet, validationSet, testingSet

    def setupSetsFromSave(self, id, setid=1):
        dataset = dbm.getDataSet(id, setid)
        self.trainingSet = [s for s in dataset if s.set_type == SetType.TRAINING.name]
        self.validationSet = [s for s in dataset if s.set_type == SetType.VALIDATION.name]
        self.testingSet = [s for s in dataset if s.set_type == SetType.TESTING.name]

        # return trainingSet, validationSet, testingSet

    # def _buildInstance(self, handler, index):
    #     d = handler.data
    #     try:
    #         change = (d[index + self.followingRange].low / d[index - 1].high) - 1
    #     except ZeroDivisionError:
    #         change = 0

    #     return DataPointInstance(shortc(self.inputVectorFactory, InputVectorFactory()), handler, index, self.vixm,
    #         positiveClass if change >= self.threshold else negativeClass
    #     )

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

    def _getSetSlice(self, set, maxSize, index):
        start = min(maxSize * index, len(set))
        end = min(maxSize * (index + 1), len(set))
        return set[start:end]

    def _getSubset(self, sourceSet, exchange, symbol):
        ret = [x for x in sourceSet if (exchange == x.handler.symbolData.exchange and (not symbol or symbol == x.handler.symbolData.symbol))]
        print(exchange, symbol, ':', len(sourceSet), '->', len(ret))
        # ret = []
        # for x in set:
        #     if exchange == x.handler.symbolData.exchange and (not symbol or symbol == x.handler.symbolData.symbol):
        #         ret.append(x)
        return ret

    def getKerasSets(self, classification=0, validationDataOnly=False, maxSize=0, index=0, exchange=None, symbol=None, verbose=1):
        def constrList_helper(set: List[DataPointInstance], isInput):
            retList = []
            for i in tqdm.tqdm(set, desc='Building input vector array') if isInput and verbose != 0 else set:
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

        ## only select from certain class if specified
        if classification:
            trainingSet = self._getInstancesByClass(self.trainingSet)[classification-1]
            validationSet = self._getInstancesByClass(self.validationSet)[classification-1]
            testingSet = self._getInstancesByClass(self.testingSet)[classification-1]
        elif maxSize:
            trainingSet = self._getSetSlice(self.trainingSet, maxSize, index)
            validationSet = self._getSetSlice(self.validationSet, maxSize, index)
            testingSet = self._getSetSlice(self.testingSet, maxSize, index)
        elif exchange or symbol:
            trainingSet = self._getSubset(self.trainingSet, exchange, symbol)
            validationSet = self._getSubset(self.validationSet, exchange, symbol)
            testingSet = self._getSubset(self.testingSet, exchange, symbol)
        else:
            trainingSet = self.trainingSet
            validationSet = self.validationSet
            testingSet = self.testingSet

        validationData = constructDataSet(validationSet)
        if validationDataOnly: return validationData
        trainingData = constructDataSet(trainingSet)
        testingData = constructDataSet(testingSet)

        return [trainingData, validationData, testingData]

    def save(self, networkId, setId=None):
        dbm.saveDataSet(networkId, self.trainingSet, self.validationSet, self.testingSet, setId)


if __name__ == '__main__':
    s = DataManager(
        90,
        30,
        SeriesType.DAILY,
        2500,
        setSplitTuple=(1/3,1/3),
        threshold=0.1,
        minimumSetsPerSymbol=1
    )
    # s.getKerasSets(classification=1)

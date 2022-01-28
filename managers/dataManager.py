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
from datetime import date
from typing import Dict, List
from tqdm.contrib.concurrent import process_map
from functools import partial

from globalConfig import config as gconfig
from constants.enums import DataFormType, OperatorDict, OutputClass, SeriesType, SetType
from utils.support import Singleton, flatten, getAdjustedSlidingWindowSize, recdotdict, recdotlist, shortc, multicore_poolIMap, processDBQuartersToDicts
from utils.other import getInstancesByClass, maxQuarters
from constants.values import unusableSymbols
from managers.stockDataManager import StockDataManager
from managers.databaseManager import DatabaseManager
from managers.vixManager import VIXManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.financialDataHandler import FinancialDataHandler
from structures.stockDataHandler import StockDataHandler
from structures.dataPointInstance import DataPointInstance
from structures.api.googleTrends.request import GoogleAPI

DEBUG = True

dbm: DatabaseManager = DatabaseManager()

def multicore_getFinancialDataTickerTuples(ticker):
    return (ticker, DatabaseManager().getFinancialData(ticker.exchange, ticker.symbol))

def multicore_getStockDataTickerTuples(ticker, seriesType, minDate):
    return (ticker, DatabaseManager().getStockData(ticker.exchange, ticker.symbol, seriesType, minDate))

## each session should only rely on one (precedingRange, followingRange) combination due to the way the handlers are setup
## not sure how new exchange/symbol handler setups would work with normalization info, if not initialized when datamanager is created

class DataManager():
    # stockDataManager: StockDataManager = None
    stockDataHandlers = {}
    vixDataHandler = VIXManager().data
    financialDataHandlers: Dict[tuple, FinancialDataHandler] = {}
    stockDataInstances = {}
    selectedInstances = []
    # unselectedInstances = []
    unselectedInstances = {}
    trainingInstances = []
    validationInstances = []
    testingInstances = []
    trainingSet = []
    validationSet = []
    testingSet = []
    inputVectorFactory = None
    setsSlidingWindowSize = 0
    useAllSets = False

    def __init__(self,
        precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, threshold=0,
        setCount=None, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0, useAllSets=False,
        inputVectorFactory=InputVectorFactory(), normalizationInfo={}, symbolList:List=[],
        analysis=False, statsOnly=False, 
        anchorDate=None, forPredictor=False,
        minDate=None,
        **kwargs
        # precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, setCount=None, threshold=0, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0, inputVectorFactory=InputVectorFactory(),
        # neuralNetwork: NeuralNetworkInstance=None, exchanges=[], excludeExchanges=[], sectors=[], excludeSectors=[]
    ):
        startt = time.time()
        self.config = inputVectorFactory.config
        self.inputVectorFactory = inputVectorFactory
        self.precedingRange = precedingRange
        # self.followingRange = followingRange
        # self.seriesType = seriesType
        # self.threshold = threshold
        # self.setCount = setCount
        self.kerasSetCaches = {}
        self.normalizationInfo = recdotdict(normalizationInfo)
        # self.symbolList = symbolList
        self.useAllSets = useAllSets

        ## purge invalid tickers
        for s in symbolList:
            if (s.exchange, s.symbol) in unusableSymbols:
                symbolList.remove(s)

        ## pull and setup financial reports ref
        if gconfig.feature.financials.enabled:
            startt2 = time.time()
            self.initializeFinancialDataHandlers(symbolList)
            print('Financial data handler initialization time:', time.time() - startt2, 'seconds')

        startt2 = time.time()
        self.initializeStockDataHandlers(symbolList, self.normalizationInfo, precedingRange, followingRange, seriesType, threshold, minDate)
        print('Stock data handler initialization time:', time.time() - startt2, 'seconds')

        if setCount is not None:
            self.setupSets(setCount, setSplitTuple, minimumSetsPerSymbol)
        elif analysis or forPredictor:
            self.setupSets(len(self.stockDataInstances.values()), (0,1), selectAll=True)
        elif statsOnly:
            self.setupSets(1, (1,0), 0)

        print('DataManager init complete. Took', time.time() - startt, 'seconds')

    @classmethod
    def forTraining(cls, seriesType=SeriesType.DAILY, **kwargs):
        print('forTraining starting')
        normalizationColumns, normalizationMaxes, symbolList = dbm.getNormalizationData(seriesType)
        print('got normalization data')
        
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

    @classmethod
    def forPredictor(cls, nn: NeuralNetworkInstance, **kwargs):
        normalizationInfo = nn.stats.getNormalizationInfo()
        qualifyingSymbolList = dbm.getLastUpdatedInfo(nn.stats.seriesType, kwargs['anchorDate'], OperatorDict.LESSTHANOREQUAL, **kwargs)

        print('qualifying list length', len(qualifyingSymbolList))

        symbolList = []
        for t in qualifyingSymbolList:
            symbolList.append(dbm.getSymbols(exchange=t.exchange, symbol=t.symbol)[0])

        return cls(
            precedingRange=nn.stats.precedingRange, followingRange=nn.stats.followingRange, seriesType=nn.stats.seriesType, threshold=nn.stats.changeThreshold, inputVectorFactory=nn.inputVectorFactory,
            normalizationInfo=normalizationInfo, symbolList=symbolList,
            forPredictor=True,
            **kwargs
        )


    ## basically just to run through initialization to get all the print() info on pos/neg split counts
    @classmethod
    def forStats(cls, seriesType=SeriesType.DAILY, **kwargs):
        # mocknormalizationInfo = { 'highMax': sys.maxsize, 'volumeMax': sys.maxsize }
        # _, _, symbolList = dbm.getNormalizationData(seriesType, normalizationInfo=mocknormalizationInfo, **kwargs)

        # return cls(
        #     precedingRange=precedingRange, followingRange=followingRange, seriesType=seriesType, threshold=threshold,
        #     symbolList=symbolList, normalizationInfo=mocknormalizationInfo,
        #     statsOnly=True
        # )
        return cls.forTraining(seriesType, statsOnly=True, **kwargs)

    def buildInputVector(self, stockDataSet: StockDataHandler, stockDataIndex, googleInterestData, symbolData):
        startt = time.time()
        precset = stockDataSet.getPrecedingSet(stockDataIndex)
        self.getprecstocktime += time.time() - startt

        if gconfig.feature.financials.enabled:
            startt = time.time()
            precfinset = self.financialDataHandlers[(symbolData.exchange, symbolData.symbol)].getPrecedingReports(date.fromisoformat(stockDataSet.data[stockDataIndex].date), self.precedingRange)
            self.getprecfintime += time.time() - startt
        else:
            precfinset = []

        startt = time.time()
        ret = self.inputVectorFactory.build(
            precset,
            self.vixDataHandler,
            precfinset,
            googleInterestData,
            symbolData.founded,
            'todo',
            symbolData.sector,
            symbolData.exchange
        )
        self.actualbuildtime += time.time() - startt

        return ret

    def initializeStockDataHandlers(self, symbolList: List, normalizationInfo, precedingRange, followingRange, seriesType, threshold, minDate):
        ## purge unusable symbols
        for s in symbolList:
            if (s.exchange, s.symbol) in unusableSymbols: symbolList.remove(s)

        if gconfig.multicore:
            for ticker, data in tqdm.tqdm(process_map(partial(multicore_getStockDataTickerTuples, seriesType=seriesType, minDate=minDate), symbolList, chunksize=1, desc='Getting stock data'), desc='Creating stock handlers'):
                if len(data) >= precedingRange + followingRange + 1:
                    self.stockDataHandlers[(ticker.exchange, ticker.symbol)] = StockDataHandler(
                        ticker,
                        seriesType,
                        data,
                        *normalizationInfo.values(),
                        precedingRange,
                        followingRange
                    )
            
            h: StockDataHandler
            for h in tqdm.tqdm(self.stockDataHandlers.values(), desc='Initializing stock instances'):
                for sindex in h.getAvailableSelections():
                    try:
                        change = (h.data[sindex + followingRange].low / h.data[sindex - 1].high) - 1
                    except ZeroDivisionError:
                        change = 0

                    self.stockDataInstances[(h.symbolData.exchange, h.symbolData.symbol, h.data[sindex].date)] = DataPointInstance(
                        self.buildInputVector,
                        h, sindex,
                        OutputClass.POSITIVE if change >= threshold else OutputClass.NEGATIVE
                    )

        else:
            for s in tqdm.tqdm(symbolList, desc='Creating stock handlers'):   
                if (s.exchange, s.symbol) in unusableSymbols: continue
                data = dbm.getStockData(s.exchange, s.symbol, seriesType, minDate=minDate)
                if len(data) >= precedingRange + followingRange + 1:
                    self.stockDataHandlers[(s.exchange, s.symbol)] = StockDataHandler(
                        s,
                        seriesType,
                        data,
                        *normalizationInfo.values(),
                        precedingRange,
                        followingRange
                    )
        
            h: StockDataHandler
            for h in tqdm.tqdm(self.stockDataHandlers.values(), desc='Initializing stock instances'):
                for sindex in h.getAvailableSelections():
                    try:
                        change = (h.data[sindex + followingRange].low / h.data[sindex - 1].high) - 1
                    except ZeroDivisionError:
                        change = 0

                    self.stockDataInstances[(h.symbolData.exchange, h.symbolData.symbol, h.data[sindex].date)] = DataPointInstance(
                        self.buildInputVector,
                        h, sindex,
                        OutputClass.POSITIVE if change >= threshold else OutputClass.NEGATIVE
                    )
        
    def initializeFinancialDataHandlers(self, symbolList):
        ANALYZE1 = False
        ANALYZE2 = False
        ANALYZE3 = False

        if gconfig.multicore:
            for ticker, data in tqdm.tqdm(process_map(multicore_getFinancialDataTickerTuples, symbolList, chunksize=1, desc='Getting financial data'), desc='Creating financial handlers'):
                self.financialDataHandlers[(ticker.exchange, ticker.symbol)] = FinancialDataHandler(ticker, data)  

        else:
            gettingtime = 0
            massagingtime = 0
            creatingtime = 0
            insertingtime = 0
            

            restotal = []
            if not ANALYZE2:
                for s in tqdm.tqdm(symbolList, desc='Creating financial handlers'):  
                    if (s.exchange, s.symbol) in unusableSymbols: continue
                    if not ANALYZE1 and not ANALYZE2 and not ANALYZE3:
                        self.financialDataHandlers[(s.exchange, s.symbol)] = FinancialDataHandler(s, dbm.getFinancialData(s.exchange, s.symbol))
                    else:

                        if ANALYZE3:
                            startt = time.time()

                            # data = dbm.getFinancialData(s.exchange, s.symbol)
                            stmt = 'SELECT * FROM vwtb_edgar_financial_nums n JOIN vwtb_edgar_quarters q ON n.exchange = q.exchange AND n.symbol = q.symbol AND n.ddate = q.period WHERE n.exchange=? AND n.symbol=? ORDER BY q.period'
                            restotal.append((s, dbm.dbc.execute(stmt, (s.exchange, s.symbol)).fetchall()))
                            gettingtime += time.time() - startt
                        elif ANALYZE1:
                            startt = time.time()

                            # data = dbm.getFinancialData(s.exchange, s.symbol)
                            stmt = 'SELECT * FROM vwtb_edgar_financial_nums n JOIN vwtb_edgar_quarters q ON n.exchange = q.exchange AND n.symbol = q.symbol AND n.ddate = q.period WHERE n.exchange=? AND n.symbol=? ORDER BY q.period'
                            res = dbm.dbc.execute(stmt, (s.exchange, s.symbol)).fetchall()
                            gettingtime += time.time() - startt

                            startt = time.time()
                            ## format results, maybe need new layer
                            createQuarterObj = lambda rw: { 'period': rw.period, 'quarter': rw.quarter, 'filed': rw.filed, 'nums': { rw.tag: rw.value }}
                            ret = []
                            curquarter = createQuarterObj(res[0])
                            for r in res[1:]:
                                if curquarter['period'] != r.period:
                                    ret.append(curquarter)
                                    curquarter = createQuarterObj(r)
                                else:
                                    curquarter['nums'][r.tag] = r.value
                            ret.append(curquarter)

                            data = recdotlist(ret)
                            massagingtime += time.time() - startt


                            startt = time.time()
                            fdh = FinancialDataHandler(s, data)
                            creatingtime += time.time() - startt
                            
                            startt = time.time()
                            self.financialDataHandlers[(s.exchange, s.symbol)] = fdh
                            insertingtime += time.time() - startt
            elif ANALYZE2:
                startt = time.time()

                # data = dbm.getFinancialData(s.exchange, s.symbol)
                stmt = 'SELECT * FROM vwtb_edgar_financial_nums n JOIN vwtb_edgar_quarters q ON n.exchange = q.exchange AND n.symbol = q.symbol AND n.ddate = q.period ORDER BY n.exchange, n.symbol, q.period'
                res = dbm.dbc.execute(stmt).fetchall()
                gettingtime += time.time() - startt

                startt = time.time()
                ## format results, maybe need new layer
                createQuarterObj = lambda rw: { 'period': rw.period, 'quarter': rw.quarter, 'filed': rw.filed, 'nums': { rw.tag: rw.value }}

                ret = []
                curquarter = createQuarterObj(res[0])
                curticker = (res[0].exchange, res[0].symbol)
                for r in res[1:]:
                    if (r.exchange, r.symbol) in unusableSymbols: continue


                    if (r.exchange, r.symbol) != curticker:
                        if curticker in unusableSymbols:
                            pass
                        else:
                            ret.append(curquarter)
                            s = next((x for x in symbolList if x.exchange == r.exchange and x.symbol == r.symbol), None)
                            if s: 
                                
                                # raise IndexError
                                self.financialDataHandlers[(r.exchange, r.symbol)] = FinancialDataHandler(s, recdotlist(ret))
                            
                        ret = []
                        curquarter = createQuarterObj(r)
                        curticker = (r.exchange, r.symbol)
                        continue

                    if curquarter['period'] != r.period:
                        ret.append(curquarter)
                        curquarter = createQuarterObj(r)
                    else:
                        curquarter['nums'][r.tag] = r.value
                massagingtime += time.time() - startt
            
            if ANALYZE3:
                    
                startt = time.time()
                fdhs = multicore_poolIMap(parseResAndCreateFDH, restotal)
                creatingtime += time.time() - startt

                for fdh in fdhs:
                    startt = time.time()
                    self.financialDataHandlers[(fdh.symbolData.exchange, fdh.symbolData.symbol)] = fdh
                    insertingtime += time.time() - startt


            if ANALYZE1 or ANALYZE2 or ANALYZE3:
                print('initializeFinancialDataHandlers stats')
                print('gettingtime',gettingtime,'seconds')
                print('massagingtime',massagingtime,'seconds')
                print('creatingtime',creatingtime,'seconds')
                print('insertingtime',insertingtime,'seconds')
                print('total',gettingtime+massagingtime+creatingtime+insertingtime,'seconds')

    def setupSets(self, setCount, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0, selectAll=False):
        if self.useAllSets or selectAll:
            self.unselectedInstances = []
            self.selectedInstances = list(self.stockDataInstances.values())

            ## determine window size for iterating through all sets            
            psints, nsints = getInstancesByClass(self.selectedInstances)
            print('Class split ratio:', len(psints) / len(self.selectedInstances))
            if not selectAll:
                if len(psints) / len(self.selectedInstances) < gconfig.sets.minimumClassSplitRatio: raise ValueError('Positive to negative set ratio below minimum threshold')
                self.setsSlidingWindowSize = getAdjustedSlidingWindowSize(len(self.selectedInstances), setCount) 
                print('Adjusted sets window size from', setCount, 'to', int(len(self.selectedInstances)*self.setsSlidingWindowSize))

        else:
            self.unselectedInstances = list(self.stockDataInstances.values())
            self.selectedInstances = []

            if DEBUG: print('Selecting', setCount, 'instances')

            ## cover minimums
            if minimumSetsPerSymbol > 0 and not self.useAllSets:
                self.unselectedInstances = []
                for h in self.stockDataHandlers.values():
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
                            self.selectedInstances.append(self.stockDataInstances[(h.symbolData.exchange, h.symbolData.symbol, d)])
                        for d in selectDates[sampleSize:]:
                            self.unselectedInstances.append(self.stockDataInstances[(h.symbolData.exchange, h.symbolData.symbol, d)])
                if DEBUG: 
                    print(len(self.selectedInstances), 'instances selected to cover minimums')
                    print(len(self.unselectedInstances), 'instances available for remaining selection')

            ## check balance
            psints, nsints = getInstancesByClass(self.selectedInstances)
            puints, nuints = getInstancesByClass(self.unselectedInstances)
            if DEBUG: print('sel rem', len(self.selectedInstances), setCount, len(self.selectedInstances) < setCount)
            # select remaining
            if len(self.selectedInstances) < setCount and not self.useAllSets:
                if DEBUG:
                    print('Positive selected instances', len(psints))
                    print('Negative selected instances', len(nsints))
                    print('Available positive instances', len(puints))
                    print('Available negative instances', len(nuints))

                pusamplesize = int(min(len(puints), setCount * gconfig.sets.positiveSplitRatio - len(psints)) if setCount / 2 - len(psints) > 0 else len(puints))
                self.selectedInstances.extend(random.sample(puints, pusamplesize))
                nusamplesize = int(min(len(nuints), setCount - len(self.selectedInstances)) if setCount - len(self.selectedInstances) > 0 else len(nuints))
                self.selectedInstances.extend(random.sample(nuints, nusamplesize))
            else:
                if DEBUG: print('Warning: setCount too low for minimum sets per symbol')
            if DEBUG:
                psints, nsints = getInstancesByClass(self.selectedInstances)
                print('All instances selected\nFinal balance:', len(psints), '/', len(nsints))

            if len(self.selectedInstances) < setCount: raise IndexError('Not enough sets available: %d vs %d' % (len(self.selectedInstances), setCount))
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
        c1, c2 = getInstancesByClass(self.selectedInstances)
        # b = self._checkSelectedBalance()
        trnStop = setSplitTuple[0]
        vldStop = setSplitTuple[1] + trnStop
        if DEBUG: print('stops', trnStop, vldStop)
        self.trainingSet = c1[:math.floor(trnStop*len(c1))] + c2[:math.floor(trnStop*len(c2))]
        self.validationSet = c1[math.floor(trnStop*len(c1)):math.floor(vldStop*len(c1))] + c2[math.floor(trnStop*len(c2)):math.floor(vldStop*len(c2))]
        self.testingSet = c1[math.floor(vldStop*len(c1)):] + c2[math.floor(vldStop*len(c2)):]

        random.shuffle(self.trainingSet)
        random.shuffle(self.validationSet)
        random.shuffle(self.testingSet)
        if DEBUG: print('Sets split into', len(self.trainingSet), '/', len(self.validationSet), '/', len(self.testingSet))

        # return trainingSet, validationSet, testingSet

    def setupSetsFromSave(self, id, setid=1):
        dataset = dbm.getDataSet(id, setid)
        self.trainingSet = [s for s in dataset if s.set_type == SetType.TRAINING.name]
        self.validationSet = [s for s in dataset if s.set_type == SetType.VALIDATION.name]
        self.testingSet = [s for s in dataset if s.set_type == SetType.TESTING.name]

        # return trainingSet, validationSet, testingSet

    def getNumberOfWindowIterations(self):
        return math.ceil(1 / self.setsSlidingWindowSize)

    def _checkSelectedBalance(self):
        pclass, nclass = getInstancesByClass(self.selectedInstances)
        return len(pclass) / (len(pclass) + len(nclass))

    def _getSetSlice(self, set, index):
        if index is None:
            return set

        sz = len(set) * self.setsSlidingWindowSize
        start = min(int(sz * index), len(set))
        end = min(int(sz * (index + 1)), len(set))

        if self.useAllSets and index == self.getNumberOfWindowIterations() - 1:
            return set[start:]
        else:
            return set[start:end]

    def _getSubset(self, sourceSet, exchange=None, symbol=None, verbose=0):
        ret = [x for x in sourceSet 
            if (not exchange and not symbol) or (exchange and exchange == x.stockDataHandler.symbolData.exchange and (not symbol or symbol == x.stockDataHandler.symbolData.symbol))
        ]
        if verbose >= 1: print(exchange, symbol, ':', len(sourceSet), '->', len(ret))
        # ret = []
        # for x in set:
        #     if exchange == x.handler.symbolData.exchange and (not symbol or symbol == x.handler.symbolData.symbol):
        #         ret.append(x)
        return ret

    def getKerasSets(self, classification=0, validationDataOnly=False, exchange=None, symbol=None, slice=None, verbose=1):
        if self.useAllSets and slice > self.getNumberOfWindowIterations() - 1: raise IndexError()
        if self.setsSlidingWindowSize and slice is None: raise ValueError('Keras set setup will overload memory, useAllSets set but not slice indicated')

        self.getprecstocktime = 0
        self.getprecfintime = 0
        self.actualbuildtime = 0

        staticSize, semiseriesSize, seriesSize = self.inputVectorFactory.getInputSize()
        def constrList_helper(set: List[DataPointInstance], isInput, showProgress=True):
            retList = []
            for i in tqdm.tqdm(set, desc='Building {} vector array'.format('input' if isInput else 'output'), leave=(verbose > 0.5)) if showProgress and isInput and verbose != 0 else set:
                retList.append(i.getInputVector() if isInput else i.getOutputVector())
            return retList

        def constrList(set: List, isInput: bool) -> numpy.array:
            return numpy.asarray(constrList_helper(set, isInput))

        def constrList_recurrent(set: List[DataPointInstance], showProgress=True) -> List:
            staticList = []
            semiseriesList = []
            seriesList = []
            for i in tqdm.tqdm(set, desc='Building input vector array', leave=(verbose > 0.5)) if showProgress and verbose != 0 else set:
                staticArr, semiseriesArr, seriesArr = i.getInputVector()
                staticList.append(staticArr)
                semiseriesList.append(numpy.reshape(semiseriesArr, (maxQuarters(self.precedingRange), semiseriesSize)))
                seriesList.append(numpy.reshape(seriesArr, (self.precedingRange, seriesSize)))

            return [
                numpy.array(staticList),
                *([numpy.array(semiseriesList)] if gconfig.feature.financials.enabled else []),
                numpy.array(seriesList)
            ]


        def constructDataSet(lst):
            # inp = constrList(lst, True)
            # ouplist = constrList(lst, False)
            # oup = keras.utils.to_categorical(ouplist, num_classes=numOutputClasses)
            # return [inp, oup]
            if gconfig.network.recurrent:
                # inp = numpy.reshape(inp, (len(inp), self.precedingRange, self.inputVectorFactory.getInputSize()[2])) ## rows, time_steps, features
                inp = constrList_recurrent(lst)
            else:
                inp = constrList(lst, True)
            oup = constrList(lst, False)
            return [
                inp, 
                keras.utils.to_categorical(oup, num_classes=OutputClass.__len__()) if gconfig.dataForm.outputVector == DataFormType.CATEGORICAL else oup
            ]


        trainingSet = self.trainingSet
        validationSet = self.validationSet
        testingSet = self.testingSet

        if exchange or symbol:
            trainingSet = self._getSubset(self.trainingSet, exchange, symbol, verbose)
            validationSet = self._getSubset(self.validationSet, exchange, symbol, verbose)
            testingSet = self._getSubset(self.testingSet, exchange, symbol, verbose)

        ## only select from certain class if specified
        if classification:
            trainingSet = self._getSetSlice(getInstancesByClass(trainingSet)[classification-1], slice)
            validationSet = self._getSetSlice(getInstancesByClass(validationSet)[classification-1], slice)
            testingSet = self._getSetSlice(getInstancesByClass(testingSet)[classification-1], slice)
        elif slice is not None:
            trainingSet = self._getSetSlice(trainingSet, slice)
            validationSet = self._getSetSlice(validationSet, slice)
            testingSet = self._getSetSlice(testingSet, slice)

        validationData = constructDataSet(validationSet)
        if validationDataOnly: return validationData
        trainingData = constructDataSet(trainingSet)
        testingData = constructDataSet(testingSet)

        if gconfig.testing.enabled:
            print('Stock data handler build time', self.getprecstocktime)
            print('Financial reports build time', self.getprecfintime)
            print('Total vector build time', self.actualbuildtime)

        return [trainingData, validationData, testingData]

    def save(self, networkId, setId=None):
        dbm.saveDataSet(networkId, self.trainingSet, self.validationSet, self.testingSet, setId)


if __name__ == '__main__':
    s = DataManager.forTraining(
        SeriesType.DAILY,
        precedingRange=90,
        followingRange=30,
        threshold=0.1,
        setCount=25000,
        setSplitTuple=(1/3,1/3),
        minimumSetsPerSymbol=1,
        useAllSets=True
    )
    # s.getKerasSets(classification=1)
    s.getKerasSets(slice=2)


    # s=DataManager.forStats(
    #     precedingRange=100,
    #     followingRange=30,
    #     seriesType=SeriesType.DAILY,
    #     threshold=0.1
    # )
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import random, math, numpy, tqdm, time, pickle, gc
from tensorflow import keras
from timeit import default_timer as timer
from datetime import date
from typing import Dict, List, Tuple
from tqdm.contrib.concurrent import process_map
from functools import partial
from argparse import ArgumentError

from globalConfig import config as gconfig
from constants.enums import DataFormType, OperatorDict, OutputClass, SeriesType, SetType
from utils.support import Singleton, flatten, getAdjustedSlidingWindowPercentage, recdotdict, recdotlist, shortc, multicore_poolIMap, processDBQuartersToDicts
from utils.other import getInstancesByClass, maxQuarters
from constants.values import unusableSymbols
from managers.stockDataManager import StockDataManager
from managers.databaseManager import DatabaseManager
from managers.vixManager import VIXManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.financialDataHandler import FinancialDataHandler
from structures.stockDataHandler import StockDataHandler
from structures.dataPointInstance import DataPointInstance
from structures.stockSplitsHandler import StockSplitsHandler
from structures.api.googleTrends.request import GoogleAPI

DEBUG = True

dbm: DatabaseManager = DatabaseManager()

def multicore_getFinancialDataTickerTuples(ticker):
    return (ticker, DatabaseManager().getFinancialData(ticker.exchange, ticker.symbol))

def multicore_getStockDataTickerTuples(ticker, seriesType, minDate):
    return (ticker, DatabaseManager().getStockData(ticker.exchange, ticker.symbol, seriesType, minDate))

def multicore_getStockSplitsTickerTuples(ticker):
    return (ticker, DatabaseManager().getStockSplits(ticker.exchange, ticker.symbol))

## each session should only rely on one (precedingRange, followingRange) combination due to the way the handlers are setup
## not sure how new exchange/symbol handler setups would work with normalization info, if not initialized when datamanager is created

class DataManager():
    # stockDataManager: StockDataManager = None
    stockDataHandlers: Dict[Tuple[str,str], StockDataHandler] = {}
    explicitValidationStockDataHandlers: Dict[Tuple[str,str], StockDataHandler] = {}
    vixDataHandler = VIXManager().data
    financialDataHandlers: Dict[Tuple[str, str], FinancialDataHandler] = {}
    stockSplitsHandlers: Dict[Tuple[str, str], StockSplitsHandler] = {}
    stockDataInstances: Dict[Tuple[str,str,str], DataPointInstance] = {}
    explicitValidationStockDataInstances: Dict[Tuple[str,str,str], DataPointInstance] = {}
    selectedInstances = []
    # unselectedInstances = []
    unselectedInstances = {}
    setSplitTuple = None
    trainingInstances = []
    validationInstances = []
    testingInstances = []
    trainingSet = []
    validationSet = []
    explicitValidationSet = []
    testingSet = []
    inputVectorFactory = None
    setsSlidingWindowPercentage = 0
    useAllSets = False
    shouldNormalize = False
    normalized = False

    def __init__(self,
        precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, threshold=0,
        setCount=None, setSplitTuple=None, minimumSetsPerSymbol=0, useAllSets=False,
        inputVectorFactory=InputVectorFactory(), normalizationInfo={}, symbolList:List=[],
        analysis=False, statsOnly=False, initializeStockDataHandlersOnly=False, useOptimizedSplitMethodForAllSets=True,
        anchorDate=None, forPredictor=False,
        minDate=None,
        explicitValidationSymbolList:List=[],
        normalize=False,
        **kwargs
        # precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, setCount=None, threshold=0, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0, inputVectorFactory=InputVectorFactory(),
        # neuralNetwork: NeuralNetworkInstance=None, exchanges=[], excludeExchanges=[], sectors=[], excludeSectors=[]
    ):
        startt = time.time()
        self.config = inputVectorFactory.config
        self.inputVectorFactory = inputVectorFactory
        self.precedingRange = precedingRange
        self.followingRange = followingRange
        self.seriesType = seriesType
        self.threshold = threshold
        self.minDate = minDate
        # self.setCount = setCount
        self.kerasSetCaches = {}
        self.normalizationInfo = recdotdict(normalizationInfo)
        # self.symbolList = symbolList
        self.useAllSets = useAllSets
        self.useOptimizedSplitMethodForAllSets = useOptimizedSplitMethodForAllSets
        self.initializedWindow = None
        self.shouldNormalize = normalize
        # self.explicitValidationSymbolList = explicitValidationSymbolList

        ## check for inappropriate argument combinations
        if useAllSets and not useOptimizedSplitMethodForAllSets:
            raise ArgumentError("Optimized split took lots of calculation and should be cached/saved, this should not be available yet")
        if explicitValidationSymbolList and setSplitTuple and setSplitTuple[1] != 0:
            raise ArgumentError('Cannot use an explicit validation set and a validation split')

        ## default setSplitTuple determination
        if not setSplitTuple:
            if explicitValidationSymbolList:
                self.setSplitTuple = (2/3,0)
            else:
                self.setSplitTuple = (1/3,1/3)
        else:
            if not explicitValidationSymbolList and setSplitTuple[1] == 0:
                raise ValueError('No validation set messes things up')
            self.setSplitTuple = setSplitTuple

        ## purge invalid/inappropriate tickers
        for s in explicitValidationSymbolList:
            if (s.exchange, s.symbol) in unusableSymbols:
                explicitValidationSymbolList.remove(s)
        inappropriateSymbols = [(s.exchange, s.symbol) for s in explicitValidationSymbolList]
        for s in symbolList:
            if (s.exchange, s.symbol) in unusableSymbols + inappropriateSymbols:
                symbolList.remove(s)


        if explicitValidationSymbolList:
            print('Initializing explicit validation stuff')
            self.initializeExplicitValidationStockDataHandlers(explicitValidationSymbolList)
            self.initializeExplicitValidationStockDataInstances()
            self.setupExplicitValidationSet()
            print('Initializing regular stock data stuff')


        if useAllSets and useOptimizedSplitMethodForAllSets:
            self.windows = dbm.getTickerSplit(1641959005, 25000)
            for windex in range(len(self.windows)):
                for i in range(len(self.windows[windex])):
                    self.windows[windex][i] = dbm.getSymbols(exchange=self.windows[windex][i].exchange, symbol=self.windows[windex][i].symbol)[0]
        ## not useAllSets and not useOptimizedSplitMethodForAllSets
        else:
            ## pull and setup financial reports ref
            if gconfig.feature.financials.enabled:
                startt2 = time.time()
                self.initializeFinancialDataHandlers(symbolList, explicitValidationSymbolList)
                print('Financial data handler initialization time:', time.time() - startt2, 'seconds')

            startt2 = time.time()
            self.initializeStockDataHandlers(symbolList)

            print('Stock data handler initialization time:', time.time() - startt2, 'seconds')

            if not initializeStockDataHandlersOnly:
                self.initializeStockSplitsHandlers(symbolList, explicitValidationSymbolList)

                startt3 = time.time()
                self.initializeStockDataInstances()
                print('Stock data instance initialization time:', time.time() - startt3, 'seconds')

                if setCount is not None:
                    self.setupSets(setCount, setSplitTuple, minimumSetsPerSymbol)
                elif analysis or forPredictor:
                    self.setupSets(len(self.stockDataInstances.values()), (0,1), selectAll=True)
                elif statsOnly:
                    self.setupSets(1, (1,0), 0)

        print('DataManager init complete. Took', time.time() - startt, 'seconds')

    ## TODO: optimized class methods, forTraining needs to have option of providing a networkid for use in getting the ticker window split
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
            if len(symbolList) == gconfig.testing.REDUCED_SYMBOL_SCOPE: break
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
    
    @classmethod
    def determineAllSetsTickerSplit(cls, nn: NeuralNetworkInstance, setCount, **kwargs):
        normalizationInfo = nn.stats.getNormalizationInfo()
        _, _, symbolList = dbm.getNormalizationData(nn.stats.seriesType, normalizationInfo=normalizationInfo, **kwargs) #exchanges=exchanges, excludeExchanges=excludeExchanges, sectors=sectors, excludeSectors=excludeSectors)



        self = cls(
            precedingRange=nn.stats.precedingRange, followingRange=nn.stats.followingRange, seriesType=nn.stats.seriesType, threshold=nn.stats.changeThreshold, inputVectorFactory=nn.inputVectorFactory,
            normalizationInfo=normalizationInfo, symbolList=symbolList,
            initializeStockDataHandlersOnly=True,
            **kwargs
        )

        ## catalog output classes for all instances for all handlers
        outputClassCountsDict = {}
        for k,v in tqdm.tqdm(self.stockDataHandlers.items(), desc='Collecting output class counts'):
            outputClassCountsDict[k] = self.initializeStockDataInstances([v], collectOutputClassesOnly=True, verbose=0)

        instanceCount = 0
        for v in outputClassCountsDict.values():
            for o in OutputClass:
                instanceCount += v[o]

        windowPercentage = getAdjustedSlidingWindowPercentage(instanceCount, setCount)
        windowSize = int(instanceCount*windowPercentage)
        numberOfWindows = math.ceil(1 / windowPercentage)
        windows = [[] for i in range(numberOfWindows)]
        tickerWindows = [[] for i in range(numberOfWindows)]
        splitRatio = gconfig.sets.minimumClassSplitRatio

        ## catalog tickers in optimal-level buckets
        optimals = [[] for i in range(3)]
        nonOptimals = []
        for k,v in outputClassCountsDict.items():
            splt = v[OutputClass.POSITIVE] / (v[OutputClass.POSITIVE] + v[OutputClass.NEGATIVE])
            for i in range(len(optimals)):
                if splitRatio - 0.01*(i+1) <= splt and splt < splitRatio + 0.02*(i+1):
                    optimals[i].append(k)
                    break
                if i == len(optimals)-1:
                    nonOptimals.append(k)
            
        def getWindowCountTotal(w):
            try:
                return sum([ sum([ wi[o] for o in OutputClass ]) for wi in w ])
            except TypeError:
                return 0
        
        ## distribute all tickers from tlist in the window buckets, attempting to stay within setCount
        def fitTickerListToWindows(tlist: List, additionalToleranceFactor=1, label=None):
            startingwindex = windows.index(min(windows, key=len))
            skiptlistindexes = []
            breakouter = False
            with tqdm.tqdm(total=len(tlist), desc=label) as tqdmbar:
                while len(skiptlistindexes) < len(tlist):
                    startinglen = len(skiptlistindexes)
                    for windex in range(startingwindex, len(windows)+startingwindex):
                        windex = windex % len(windows)
                        for opindex in range(len(tlist)):
                            if opindex in skiptlistindexes: continue
                            if getWindowCountTotal(windows[windex]) + outputClassCountsDict[tlist[opindex]][OutputClass.POSITIVE] + outputClassCountsDict[tlist[opindex]][OutputClass.NEGATIVE] < windowSize * additionalToleranceFactor:
                                windows[windex].append(outputClassCountsDict[tlist[opindex]])
                                tickerWindows[windex].append({ 'exchange': tlist[opindex][0], 'symbol': tlist[opindex][1] })
                                skiptlistindexes.append(opindex)
                                tqdmbar.update()
                                if len(skiptlistindexes) == len(tlist):
                                    breakouter = True
                                break
                        if breakouter: break
                    
                    if len(skiptlistindexes) == startinglen:
                        print('stuck')
                        break
            for skp in reversed(sorted(skiptlistindexes)):
                tlist.pop(skp)
        
        for p in range(len(optimals)):
            fitTickerListToWindows(optimals[p], 1 + 0.03*p, label='Fitting optimals level {}'.format(p))
        fitTickerListToWindows(nonOptimals, 1.15, label='Fitting non-optimals')

        def getWindowRatio(w):
            pos = 0
            neg = 0
            for i in w:
                pos += i[OutputClass.POSITIVE]
                neg += i[OutputClass.NEGATIVE]
            return pos / (pos + neg)
        for w in range(len(windows)):
            # print('Window', w, ':', str(getWindowCountTotal(windows[w])).ljust(6), getWindowRatio(windows[w]))
            pass

        for o in range(len(optimals)):
            if len(optimals[o]) > 0:
                print('Remaining Op{}:'.format(o), optimals[o])
        if len(nonOptimals) > 0:
            print('Remaining non-optimals')
            for o in nonOptimals:
                print(o, outputClassCountsDict[o])

        return tickerWindows

    def buildInputVector(self, stockDataSet: StockDataHandler, stockDataIndex, googleInterestData, symbolData):
        startt = time.time()
        precset = stockDataSet.getPrecedingSet(stockDataIndex)
        self.getprecstocktime += time.time() - startt

        splitsset = self.stockSplitsHandlers[stockDataSet.getTickerTuple()].getForRange(precset[0].date, precset[-1].date)

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
            symbolData.exchange,
            splitsset
        )
        self.actualbuildtime += time.time() - startt

        return ret

    def initializeExplicitValidationStockDataHandlers(self, symbolList: List):
        self.initializeStockDataHandlers(symbolList, 'explicitValidationStockDataHandlers')

    def initializeStockDataHandlers(self, symbolList: List, dmProperty='stockDataHandlers'):
        ## purge unusable symbols
        for s in symbolList:
            if (s.exchange, s.symbol) in unusableSymbols: symbolList.remove(s)

        sdhArg = lambda ticker, data: [
            ticker,
            self.seriesType,
            data,
            *self.normalizationInfo.values(),
            self.precedingRange,
            self.followingRange
        ]
        if gconfig.multicore:
            for ticker, data in tqdm.tqdm(process_map(partial(multicore_getStockDataTickerTuples, seriesType=self.seriesType, minDate=self.minDate), symbolList, chunksize=1, desc='Getting stock data'), desc='Creating stock handlers'):
                if len(data) >= self.precedingRange + self.followingRange + 1:
                    # self.stockDataHandlers[(ticker.exchange, ticker.symbol)] = StockDataHandler(*sdhArg(ticker, data))
                    self.__getattribute__(dmProperty)[(ticker.exchange, ticker.symbol)] = StockDataHandler(*sdhArg(ticker, data))
                    
        else:
            for s in tqdm.tqdm(symbolList, desc='Creating stock handlers'):
                data = dbm.getStockData(s.exchange, s.symbol, self.seriesType, minDate=self.minDate)
                if len(data) >= self.precedingRange + self.followingRange + 1:
                    # self.stockDataHandlers[(s.exchange, s.symbol)] = StockDataHandler(*sdhArg(s, data))
                    self.__getattribute__(dmProperty)[(s.exchange, s.symbol)] = StockDataHandler(*sdhArg(s, data))

        if self.shouldNormalize: self.normalize()

    def initializeExplicitValidationStockDataInstances(self, **kwargs):
        self.initializeStockDataInstances(stockDataHandlers=self.explicitValidationStockDataHandlers.values(), dmProperty='explicitValidationStockDataInstances', **kwargs)

    def initializeStockDataInstances(self, stockDataHandlers: List[StockDataHandler]=None, collectOutputClassesOnly=False, dmProperty='stockDataInstances', verbose=1):
        if not stockDataHandlers:
            stockDataHandlers = self.stockDataHandlers.values()

        outputClassCounts = { o: 0 for o in OutputClass }

        h: StockDataHandler
        for h in tqdm.tqdm(stockDataHandlers, desc='Initializing stock instances') if verbose > 0 else stockDataHandlers:
            for sindex in h.getAvailableSelections():
                try:
                    change = (h.data[sindex + self.followingRange].low / h.data[sindex - 1].high) - 1
                except ZeroDivisionError:
                    change = 0
                oupclass = OutputClass.POSITIVE if change >= self.threshold else OutputClass.NEGATIVE

                if collectOutputClassesOnly:
                    outputClassCounts[oupclass] += 1
                else:
                    # self.stockDataInstances[(h.symbolData.exchange, h.symbolData.symbol, h.data[sindex].date)] = DataPointInstance(
                    self.__getattribute__(dmProperty)[(h.symbolData.exchange, h.symbolData.symbol, h.data[sindex].date)] = DataPointInstance(
                        self.buildInputVector,
                        h, sindex, oupclass
                    )

        if collectOutputClassesOnly: return outputClassCounts
        
    def initializeFinancialDataHandlers(self, symbolList, explicitValidationSymbolList):
        symbolList += explicitValidationSymbolList
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

    def initializeStockSplitsHandlers(self, symbolList, explicitValidationSymbolList):
        symbolList += explicitValidationSymbolList
        ## purge unusable symbols
        for s in symbolList:
            if (s.exchange, s.symbol) in unusableSymbols: symbolList.remove(s)

        if gconfig.multicore:
            for ticker, data in tqdm.tqdm(process_map(partial(multicore_getStockSplitsTickerTuples), symbolList, chunksize=1, desc='Getting stock splits data'), desc='Creating stock splits handlers'):
                self.stockSplitsHandlers[(ticker.exchange, ticker.symbol)] = StockSplitsHandler(ticker.exchange, ticker.symbol, data)
                    
        else:
            for s in tqdm.tqdm(symbolList, desc='Creating stock handlers'):
                self.stockSplitsHandlers[(s.exchange, s.symbol)] = StockSplitsHandler(s.exchange, s.symbol, dbm.getStockSplits(s.exchange, s.symbol))

    def initializeWindow(self, windowIndex):
        self.stockDataInstances.clear()
        self.stockDataHandlers.clear()
        self.normalized = False
        self.initializeStockDataHandlers(self.windows[windowIndex])
        self.initializeStockDataInstances()
        self.setupSets(selectAll=True)
        self.initializedWindow = windowIndex
        gc.collect()

    def setupExplicitValidationSet(self):
        self.explicitValidationSet = list(self.explicitValidationStockDataInstances.values())
        random.shuffle(self.explicitValidationSet)

    def setupSets(self, setCount=None, setSplitTuple=None, minimumSetsPerSymbol=0, selectAll=False):
        if not setSplitTuple:
            setSplitTuple = shortc(self.setSplitTuple, (1/3,1/3))

        if self.useAllSets or selectAll:
            self.unselectedInstances = []
            self.selectedInstances = list(self.stockDataInstances.values())

            ## determine window size for iterating through all sets            
            psints, nsints = getInstancesByClass(self.selectedInstances)
            print('Class split ratio:', len(psints) / len(self.selectedInstances))
            if not selectAll:
                if len(psints) / len(self.selectedInstances) < gconfig.sets.minimumClassSplitRatio: raise ValueError('Positive to negative set ratio below minimum threshold')
                self.setsSlidingWindowPercentage = getAdjustedSlidingWindowPercentage(len(self.selectedInstances), setCount) 
                print('Adjusted sets window size from', setCount, 'to', int(len(self.selectedInstances)*self.setsSlidingWindowPercentage))

        else:
            self.unselectedInstances = list(self.stockDataInstances.values())
            self.selectedInstances = []

            if DEBUG: print('Selecting', setCount, 'instances')

            ## cover minimums
            if minimumSetsPerSymbol > 0:
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
            if len(self.selectedInstances) < setCount:
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
        if self.useAllSets and self.useOptimizedSplitMethodForAllSets:
            return len(self.windows)
        return math.ceil(1 / self.setsSlidingWindowPercentage)

    def _checkSelectedBalance(self):
        pclass, nclass = getInstancesByClass(self.selectedInstances)
        return len(pclass) / (len(pclass) + len(nclass))

    def _getSetSlice(self, set, index):
        if index is None:
            return set

        sz = len(set) * self.setsSlidingWindowPercentage
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
        if self.useAllSets and not self.useOptimizedSplitMethodForAllSets and shortc(slice, 0) > self.getNumberOfWindowIterations() - 1: raise IndexError()
        # if self.setsSlidingWindowPercentage and slice is None: raise ValueError('Keras set setup will overload memory, useAllSets set but not slice indicated')

        if self.useAllSets and self.useOptimizedSplitMethodForAllSets:
            if self.initializedWindow != slice:
                self.initializeWindow(slice)
            slice = None

        ## lazily ensure slice is not used if not setup for all sets
        if not self.useAllSets:
            if shortc(slice,0) > 0: raise IndexError('Not setup to use all sets')
            else: slice = None

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
        validationSet = shortc(self.explicitValidationSet, self.validationSet)
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

        if gconfig.testing.enabled and verbose > 0.5:
            print('Stock data handler build time', self.getprecstocktime)
            print('Financial reports build time', self.getprecfintime)
            print('Total vector build time', self.actualbuildtime)

        return [trainingData, validationData, testingData]

    def normalize(self):
        if not self.normalized:
            h: StockDataHandler
            for h in self.stockDataHandlers.values():
                h.normalize()
            self.normalized=True

    def denormalize(self):
        if self.normalized:
            h: StockDataHandler
            for h in self.stockDataHandlers.values():
                h.denormalize()
            self.normalized=False

    def save(self, networkId, setId=None):
        dbm.saveDataSet(networkId, self.trainingSet, self.validationSet, self.testingSet, setId)


if __name__ == '__main__':

    tsplit = DataManager.determineAllSetsTickerSplit(
        NeuralNetworkManager().get(1641959005),
        25000,
        assetTypes=['CS','CLA','CLB','CLC']
    )
    dbm.saveTickerSplit(1641959005, 25000, tsplit)
    exit()
    
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
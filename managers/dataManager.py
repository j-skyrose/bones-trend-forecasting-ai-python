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
from typing import Dict, List, Set, Tuple
from tqdm.contrib.concurrent import process_map
from functools import partial
from argparse import ArgumentError

from globalConfig import config as gconfig
from constants.enums import DataFormType, Direction, OperatorDict, OutputClass, ReductionMethod, SeriesType, SetType, DataManagerType, IndicatorType
from utils.support import generateFibonacciSequence, getAdjustedSlidingWindowPercentage, recdotdict, recdotlist, shortc, multicore_poolIMap, someIndicatorEnabled, tqdmLoopHandleWrapper, tqdmProcessMapHandlerWrapper
from utils.other import getInstancesByClass, getMaxIndicatorPeriod, maxQuarters, getIndicatorPeriod, setKWArgsFromConfigForGetSymbols
from utils.technicalIndicatorFormulae import generateADXs_AverageDirectionalIndex
from constants.values import unusableSymbols, indicatorsKey
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
from structures.googleInterestsHandler import GoogleInterestsHandler
from structures.api.googleTrends.request import GoogleAPI
from structures.skipsObj import SkipsObj
from utils.types import TickerDateKeyType, TickerKeyType

DEBUG = True

dbm: DatabaseManager = DatabaseManager()

def multicore_getFinancialDataTickerTuples(ticker):
    return (ticker, DatabaseManager().getFinancialData(ticker.exchange, ticker.symbol))

def multicore_getStockDataTickerTuples(ticker, seriesType, minDate, queryLimit):
    return (ticker, DatabaseManager().getStockData(ticker.exchange, ticker.symbol, seriesType, minDate, queryLimit=queryLimit))

def multicore_getStockSplitsTickerTuples(ticker):
    return (ticker, DatabaseManager().getStockSplits(ticker.exchange, ticker.symbol))

def multicore_getGoogleInterestsTickerTuples(ticker, queryLimit):
    return (ticker, DatabaseManager().getGoogleInterests(ticker.exchange, ticker.symbol, queryLimit=queryLimit))

## each session should only rely on one (precedingRange, followingRange) combination due to the way the handlers are setup
## not sure how new exchange/symbol handler setups would work with normalization info, if not initialized when datamanager is created

class DataManager():
    # stockDataManager: StockDataManager = None
    stockDataHandlers: Dict[TickerKeyType, StockDataHandler] = {}
    explicitValidationStockDataHandlers: Dict[TickerKeyType, StockDataHandler] = {}
    financialDataHandlers: Dict[TickerKeyType, FinancialDataHandler] = {}
    stockSplitsHandlers: Dict[TickerKeyType, StockSplitsHandler] = {}
    googleInterestsHandlers: Dict[TickerKeyType, GoogleInterestsHandler] = {}
    stockDataInstances: Dict[TickerDateKeyType, DataPointInstance] = {}
    explicitValidationStockDataInstances: Dict[TickerDateKeyType, DataPointInstance] = {}
    selectedInstances: List[DataPointInstance] = []
    unselectedInstances: List[DataPointInstance] = []
    setSplitTuple = None
    trainingInstances: List[DataPointInstance] = []
    validationInstances: List[DataPointInstance] = []
    testingInstances: List[DataPointInstance] = []
    trainingSet: List[DataPointInstance] = []
    validationSet: List[DataPointInstance] = []
    explicitValidationSet: List[DataPointInstance] = []
    testingSet: List[DataPointInstance] = []
    inputVectorFactory = None
    setsSlidingWindowPercentage = 0
    useAllSets = False
    shouldNormalize = False
    normalized = False

    def __init__(self,
        precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, threshold=0,
        setCount=None, setSplitTuple=None, minimumSetsPerSymbol=0, useAllSets=False,
        inputVectorFactory=InputVectorFactory(), normalizationInfo={}, indicatorConfig=gconfig.defaultIndicatorFormulaConfig, symbolList:List=[],
        analysis=False, skips: SkipsObj=SkipsObj(), saveSkips=False,

        statsOnly=False, initializeStockDataHandlersOnly=False, useOptimizedSplitMethodForAllSets=True,
        anchorDate=None, forPredictor=False, postPredictionWeighting=False,
        minDate=None,
        explicitValidationSymbolList:List=[],

        maxPageSize=0, skipAllDataInitialization=False,
        maxGoogleInterestHandlers=50,
        verbose=None, **kwargs
        # precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, setCount=None, threshold=0, setSplitTuple=(1/3,1/3), minimumSetsPerSymbol=0, inputVectorFactory=InputVectorFactory(),
        # neuralNetwork: NeuralNetworkInstance=None, exchanges=[], excludeExchanges=[], sectors=[], excludeSectors=[]
    ):
        self.config = inputVectorFactory.config

        ## check for inappropriate argument combinations, and other misconfigurations
        if useAllSets and not useOptimizedSplitMethodForAllSets:
            raise ValueError("Optimized split took lots of calculation and should be cached/saved, this should not be available yet")
        if useAllSets and useOptimizedSplitMethodForAllSets and maxGoogleInterestHandlers:
            raise ValueError('Cannot use max on Google Interests handlers along with windows, behavior not tested')
        if explicitValidationSymbolList and setSplitTuple and setSplitTuple[1] != 0:
            raise ValueError('Cannot use an explicit validation set and a validation split')
        if maxPageSize and useAllSets:
            raise ValueError('Simultaneous use of pages and windows should be avoided, behavior not tested')
        if 'instanceReduction' in self.config.sets.keys() and self.config.sets.instanceReduction.enabled and self.config.sets.instanceReduction.top + self.config.sets.instanceReduction.bottom > 1:
            raise ValueError('Top + bottom cannot be greater than 1 (i.e. more then all)')
        if not forPredictor and setCount is None and not initializeStockDataHandlersOnly and not skips.sets:
            raise ValueError('setCount required when initializing sets')
        
        ## timers
        self.getprecstocktime = 0
        self.getprecindctime = 0
        self.getprecfintime = 0
        self.actualbuildtime = 0
        ##

        startt = time.time()
        self.verbose = shortc(verbose, 1)
        self.inputVectorFactory = inputVectorFactory
        self.precedingRange = precedingRange
        self.followingRange = followingRange
        self.seriesType = seriesType
        self.threshold = threshold
        self.minDate = minDate
        self.normalizationInfo = recdotdict(normalizationInfo)
        self.indicatorConfig = indicatorConfig
        self.skips = skips if saveSkips else SkipsObj()
        ## if paging for predictor remove restriction on GI handler initialization as there should be sufficient space to init them
        if forPredictor and maxPageSize:
            self.maxGoogleInterestHandlers = 0
        else:
            self.maxGoogleInterestHandlers = maxGoogleInterestHandlers

        ## (training/validation/testing) set initialization-related parameters
        self.setCount = setCount
        self.minimumSetsPerSymbol = minimumSetsPerSymbol
        self.initializeStockDataHandlersOnly = initializeStockDataHandlersOnly
        self.type: DataManagerType
        if analysis: self.type = DataManagerType.ANALYSIS
        elif forPredictor: self.type = DataManagerType.PREDICTION
        elif statsOnly: self.type = DataManagerType.STATS
        else: self.type = DataManagerType.DEFAULT
        ##

        ## purge invalid/inappropriate tickers
        explicitValidationSymbolList[:] = [s for s in explicitValidationSymbolList if (s.exchange, s.symbol) not in unusableSymbols]
        inappropriateSymbols = [(s.exchange, s.symbol) for s in explicitValidationSymbolList]
        symbolList[:] = [s for s in symbolList if (s.exchange, s.symbol) not in unusableSymbols + inappropriateSymbols]


        self.explicitValidationSymbolList = explicitValidationSymbolList
        ##

        ## for page-based initialization of all data, grouped by ticker
        self.symbolList = symbolList
        self.usePaging = maxPageSize > 0
        self.pageSize = maxPageSize
        self.currentPage = 1
        ##

        ## for page/window-based initialization of keras sets, for training
        self.useAllSets = useAllSets
        self.useOptimizedSplitMethodForAllSets = useOptimizedSplitMethodForAllSets
        self.initializedWindow = None
        self.shouldNormalize = self.config.data.normalize
        ##

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


        if explicitValidationSymbolList and not skips.stocks:
            if self.verbose>=1: print('Initializing explicit validation stuff')
            self.initializeExplicitValidationStockDataHandlers(explicitValidationSymbolList)
            if not skips.instances:
                self.initializeExplicitValidationStockDataInstances()
                if not skips.sets: self.setupExplicitValidationSet()
            if self.verbose>=1: print('Initializing regular stock data stuff')


        if useAllSets and useOptimizedSplitMethodForAllSets:
            self.windows = dbm.getTickerSplit('split1681021636', 50000)
            for windex in range(len(self.windows)):
                for i in range(len(self.windows[windex])):
                    self.windows[windex][i] = dbm.getSymbols(exchange=self.windows[windex][i].exchange, symbol=self.windows[windex][i].symbol)[0]
        ## not useAllSets and not useOptimizedSplitMethodForAllSets
        else:
            ## reduce amount of unneccessary data retrieved and maintained in memory during lifecycle
            self.queryLimit=None
            if forPredictor and not postPredictionWeighting and not someIndicatorEnabled(self.config):
                self.queryLimit = self.precedingRange + 1

            if not skipAllDataInitialization:
                initSymbolList = symbolList
                if self.usePaging:
                    initSymbolList = self.getSymbolListPage(1)
                
                self._initializeAllData(initSymbolList, self.currentPage if self.usePaging else None, skips=skips)

        self.vixDataHandler = VIXManager(self.shouldNormalize).data

        if self.verbose>=1: print('DataManager init complete. Took', time.time() - startt, 'seconds')

    def initializeAllDataForPage(self, page, verbose=None):
        if not self.usePaging: raise ArgumentError('Manager not setup with paging')
        self._initializeAllData(self.getSymbolListPage(page), refresh=True, verbose=verbose)
        gc.collect() ## help clean up old/cleared data

    def _initializeAllData(self, symbolList, refresh=False, skips: SkipsObj=None, verbose=None):
        verbose = shortc(verbose, self.verbose)

        if not skips: skips = self.skips
        ## pull and setup financial reports ref
        if gconfig.feature.financials.enabled and not skips.financials:
            startt2 = time.time()
            self.initializeFinancialDataHandlers(symbolList, self.explicitValidationSymbolList, refresh=refresh, verbose=verbose)
            if verbose>=1: print('Financial data handler initialization time:', time.time() - startt2, 'seconds')

        startt2 = time.time()
        if not skips.stocks: 
            self.initializeStockDataHandlers(symbolList, queryLimit=self.queryLimit, refresh=refresh, verbose=verbose)

            if verbose>=1: print('Stock data handler initialization time:', time.time() - startt2, 'seconds')

            if not self.initializeStockDataHandlersOnly:
                if not skips.splits: self.initializeStockSplitsHandlers(symbolList, self.explicitValidationSymbolList, refresh=refresh, verbose=verbose)
                if not skips.technicalIndicators: self.initializeTechnicalIndicators(verbose) ## needs to be done before any instance selection as the viable index pool may get reduced
                if not self.maxGoogleInterestHandlers and not skips.googleInterests:
                    self.initializeGoogleInterestsHandlers(symbolList, self.explicitValidationSymbolList, queryLimit=self.queryLimit, refresh=refresh, verbose=verbose)

                if self.type != DataManagerType.PREDICTION and not skips.instances:
                    startt3 = time.time()
                    self.initializeStockDataInstances(refresh=refresh, verbose=verbose)
                    if verbose>=1: print('Stock data instance initialization time:', time.time() - startt3, 'seconds')

                    if not skips.sets:
                        kwargs = { 'verbose': verbose }
                        if self.setCount is not None:
                            kwargs['setCount'] = self.setCount
                            kwargs['setSplitTuple'] = self.setSplitTuple
                            kwargs['minimumSetsPerSymbol'] = self.minimumSetsPerSymbol
                        elif self.type == DataManagerType.ANALYSIS:
                            kwargs['setCount'] = len(self.stockDataInstances.values())
                            kwargs['setSplitTuple'] = (0,1)
                            kwargs['selectAll'] = True
                        elif self.type == DataManagerType.STATS:
                            kwargs['setCount'] = 1
                            kwargs['setSplitTuple'] = (1,0)
                            kwargs['minimumSetsPerSymbol'] = 0
                        self.setupSets(**kwargs)

    ## TODO: optimized class methods, forTraining needs to have option of providing a networkid for use in getting the ticker window split
    @classmethod
    def forTraining(cls, seriesType=SeriesType.DAILY, **kwargs):
        config = kwargs['inputVectorFactory'].config if 'inputVectorFactory' in kwargs else gconfig
        if config.data.normalize:
            normalizationColumns, normalizationMaxes, symbolList = dbm.getNormalizationData(seriesType, **kwargs)
        
            kwargs['normalizationInfo'] = {}
            for c in range(len(normalizationColumns)):
                kwargs['normalizationInfo'][normalizationColumns[c]] = normalizationMaxes[c]
        else:
            ## replicate some of the conditions from getNormalizationData as it will not be used to retrieve a symbol list
            kwargs = setKWArgsFromConfigForGetSymbols(kwargs, config)
            kwargs['seriesType'] = seriesType
            symbolList = dbm.getSymbols(**kwargs)

        return cls(
            symbolList=symbolList, 
            **kwargs
        )

    @classmethod
    def forAnalysis(cls,
                    network: NeuralNetworkInstance=None,
                    seriesType: SeriesType=SeriesType.DAILY,
                    skips: SkipsObj=SkipsObj(),
                    **kwargs):
        
        if 'explicitValidationSymbolList' in kwargs.keys(): raise ArgumentError('Cannot define explicit validation set for analysis, behavior not tested')

        config = network.config if network else (kwargs['inputVectorFactory'].config if 'inputVectorFactory' in kwargs else gconfig)
        shouldNormalize = config.data.normalize
        if not shouldNormalize:
            ## replicate some of the conditions from getNormalizationData as it will not be used to retrieve a symbol list
            kwargs = setKWArgsFromConfigForGetSymbols(kwargs, config)

        if network:
            if shouldNormalize:
                kwargs['normalizationInfo'] = network.stats.getNormalizationInfo()
                _, _, symbolList = dbm.getNormalizationData(network.stats.seriesType, **kwargs)
            kwargs['precedingRange'] = network.stats.precedingRange
            kwargs['followingRange'] = network.stats.followingRange
            kwargs['seriesType'] = network.stats.seriesType
            kwargs['changeThreshold'] = network.stats.changeThreshold
            kwargs['inputVectorFactory'] = network.inputVectorFactory
        else:
            kwargs['seriesType'] = seriesType

            if shouldNormalize:
                normalizationColumns, normalizationMaxes, symbolList = dbm.getNormalizationData(seriesType, **kwargs)
                kwargs['normalizationInfo'] = {}
                for c in range(len(normalizationColumns)):
                    kwargs['normalizationInfo'][normalizationColumns[c]] = normalizationMaxes[c]
        
        try: symbolList
        except UnboundLocalError: ## i.e. normalize=False, never initialized
            symbolList = dbm.getSymbols(**kwargs)


        return cls(
            symbolList=symbolList,
            analysis=True, skips=skips,
            **kwargs
        )

    ## deviates from full initialization as per the below
    ''' 
        reduces symbol list based on what has up to date data
        forPredictor: 
            puts all stock data instances into the validation set
            sets a query limit to reduce data in memory if weighting is not planned after prediction 
    '''  
    @classmethod
    def forPredictor(cls, nn: NeuralNetworkInstance, anchorDate, **kwargs):
        if nn.config.data.normalize:
            kwargs['normalizationInfo'] = nn.stats.getNormalizationInfo()
        qualifyingSymbolList = dbm.getLastUpdatedInfo(nn.stats.seriesType, anchorDate, OperatorDict.LESSTHANOREQUAL, **kwargs)

        print('qualifying list length', len(qualifyingSymbolList))

        symbolList = []
        for t in qualifyingSymbolList:
            if len(symbolList) == gconfig.testing.REDUCED_SYMBOL_SCOPE: break
            symbolList.append(dbm.getSymbols(exchange=t.exchange, symbol=t.symbol)[0])

        return cls(
            precedingRange=nn.stats.precedingRange, followingRange=nn.stats.followingRange, seriesType=nn.stats.seriesType, threshold=nn.stats.changeThreshold, inputVectorFactory=nn.inputVectorFactory,
            symbolList=symbolList,
            forPredictor=True,
            **kwargs
        )


    ## basically just to run through initialization to get all the print() info on pos/neg split counts
    @classmethod
    def forStats(cls, seriesType=SeriesType.DAILY, **kwargs):
        return cls.forTraining(seriesType, statsOnly=True, **kwargs)
    
    @classmethod
    def determineAllSetsTickerSplit(cls, setCount, **kwargs):
                                    # precedingRange=0, followingRange=0, threshold=0,
        self = cls.forAnalysis(
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
                                tickerWindows[windex].append(tlist[opindex].getDict()) ## must go in as dict so unpickling and sql factory can work
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

    def buildInputVector(self, stockDataSet: StockDataHandler, stockDataIndex, symbolData):
        startt = time.time()
        precset = stockDataSet.getPrecedingSet(stockDataIndex)
        self.getprecstocktime += time.time() - startt

        startt = time.time()
        precedingIndicators: Dict = stockDataSet.getPrecedingIndicators(stockDataIndex)
        self.getprecindctime += time.time() - startt

        anchordate = date.fromisoformat(stockDataSet.data[stockDataIndex].date)

        try: splitsset = self.stockSplitsHandlers[stockDataSet.getTickerTuple()].getForRange(precset[0].date, precset[-1].date)
        except KeyError: splitsset = []

        try: googleinterests = self.googleInterestsHandlers[stockDataSet.getTickerTuple()].getPrecedingRange(anchordate.isoformat(), self.precedingRange)
        except KeyError: googleinterests = []

        if gconfig.feature.financials.enabled:
            startt = time.time()
            precfinset = self.financialDataHandlers[stockDataSet.getTickerTuple()].getPrecedingReports(anchordate, self.precedingRange)
            self.getprecfintime += time.time() - startt
        else:
            precfinset = []

        startt = time.time()
        ret = self.inputVectorFactory.build(
            stockDataSet=precset,
            vixData=self.vixDataHandler,
            financialDataSet=precfinset,
            googleInterests=googleinterests,
            stockSplits=splitsset,
            indicators=precedingIndicators,
            foundedDate=symbolData.founded,
            ipoDate='todo',
            sector=symbolData.sector,
            exchange=symbolData.exchange,
            etfFlag=symbolData.asset_type == 'ETF'
        )
        self.actualbuildtime += time.time() - startt

        return ret

    def initializeExplicitValidationStockDataHandlers(self, symbolList: List, **kwargs):
        self.initializeStockDataHandlers(symbolList, 'explicitValidationStockDataHandlers', **kwargs)

    def initializeStockDataHandlers(self, symbolList: List, dmProperty='stockDataHandlers', queryLimit: int=None, refresh=False, verbose=None):
        verbose = shortc(verbose, self.verbose)

        ## purge unusable symbols
        symbolList[:] = [s for s in symbolList if (s.exchange, s.symbol) not in unusableSymbols]

        ## purge old data
        if refresh: self.__getattribute__(dmProperty).clear()

        maxIndicatorPeriod = getMaxIndicatorPeriod(self.config.feature[indicatorsKey].keys(), self.indicatorConfig)

        ## check if there is enough stock data to fulfill (hyperparameter) requirements
        precedingFollowingShortfallCheck = lambda d: len(d) >= self.precedingRange + self.followingRange + 1
        indicatorPeriodShortfallCheck = lambda d: len(d) < maxIndicatorPeriod
        dataLengthCheck = lambda d: queryLimit or precedingFollowingShortfallCheck(d) or indicatorPeriodShortfallCheck(d)

        queryLimitSkips = 0
        precedingFollowingShortfallSkips = 0
        indicatorPeriodShortfallSkips = 0
        def updateSkipCounts(data):
            if not queryLimit: queryLimitSkips += 1
            elif not precedingFollowingShortfallCheck(data): precedingFollowingShortfallSkips += 1
            elif not indicatorPeriodShortfallCheck(data): indicatorPeriodShortfallSkips += 1


        sdhArgLambda = lambda ticker, data: [
            ticker,
            self.seriesType,
            data
        ]
        sdhKWArgs = {
            'precedingRange': self.precedingRange,
            'followingRange': self.followingRange,
            'maxIndicatorPeriod': maxIndicatorPeriod,
            'normalize': self.config.data.normalize
        }
        if self.shouldNormalize:
            ## use key loop?
            sdhKWArgs['highMax'] = self.normalizationInfo.highMax
            sdhKWArgs['volumeMax'] = self.normalizationInfo.volumeMax

        if gconfig.multicore:
            for ticker, data in tqdmLoopHandleWrapper(tqdmProcessMapHandlerWrapper(partial(multicore_getStockDataTickerTuples, seriesType=self.seriesType, minDate=self.minDate, queryLimit=queryLimit), symbolList, verbose, desc='Getting stock data'), verbose, desc='Creating stock handlers'):
                if dataLengthCheck(data):
                    self.__getattribute__(dmProperty)[TickerKeyType(ticker.exchange, ticker.symbol)] = StockDataHandler(*sdhArgLambda(ticker, data), **sdhKWArgs)
                else:
                    updateSkipCounts(data)
        else:
            for s in tqdmLoopHandleWrapper(symbolList, verbose, desc='Creating stock handlers'):
                data = dbm.getStockData(s.exchange, s.symbol, self.seriesType, minDate=self.minDate, queryLimit=queryLimit)
                if dataLengthCheck(data):
                    self.__getattribute__(dmProperty)[TickerKeyType(s.exchange, s.symbol)] = StockDataHandler(*sdhArgLambda(s, data), **sdhKWArgs)
                else:
                    updateSkipCounts(data)

        if self.shouldNormalize: self.normalize()

        if (queryLimitSkips or precedingFollowingShortfallSkips or indicatorPeriodShortfallSkips) and verbose>=1:
            print('queryLimitSkips', queryLimitSkips)
            print('precedingFollowingShortfallSkips', precedingFollowingShortfallSkips)
            print('indicatorPeriodShortfallSkips', indicatorPeriodShortfallSkips)

    def initializeExplicitValidationStockDataInstances(self, **kwargs):
        self.initializeStockDataInstances(stockDataHandlers=self.explicitValidationStockDataHandlers.values(), dmProperty='explicitValidationStockDataInstances', **kwargs)

    def initializeStockDataInstances(self, stockDataHandlers: List[StockDataHandler]=None, collectOutputClassesOnly=False, dmProperty='stockDataInstances', refresh=False, verbose=None):
        verbose = shortc(verbose, self.verbose)

        if not stockDataHandlers:
            stockDataHandlers = self.stockDataHandlers.values()

        ## purge old data
        if refresh: self.__getattribute__(dmProperty).clear()

        outputClassCounts = { o: 0 for o in OutputClass }

        instanceReductionMissingCount = 0
        totalInstanceReduction = 0
        h: StockDataHandler
        for h in tqdmLoopHandleWrapper(stockDataHandlers, verbose, desc='Initializing stock instances'):
            availableIndexes = { o: [] for o in OutputClass }
            for sindex in h.getAvailableSelections():
                try:
                    change = (h.data[sindex + self.followingRange].low / h.data[sindex - 1].high) - 1
                except ZeroDivisionError:
                    change = 0
                oupclass = OutputClass.POSITIVE if change >= self.threshold else OutputClass.NEGATIVE

                if collectOutputClassesOnly:
                    outputClassCounts[oupclass] += 1
                else:
                    availableIndexes[oupclass].append(sindex)

            if collectOutputClassesOnly: return outputClassCounts

            if self.config.sets.instanceReduction.enabled and self.config.sets.instanceReduction.method != ReductionMethod.NONE:
                def printInstanceCounts(before=True): print(f"{'Before' if before else 'After'} reduction| Total", *[o.name for o in OutputClass], sum([len(availableIndexes[o]) for o in OutputClass]), *[len(availableIndexes[o]) for o in OutputClass])
                if verbose>=2: printInstanceCounts()
                oupclass = self.config.sets.instanceReduction.classType

                similarities = dbm.getVectorSimilarity(*h.getTickerTuple(), seriesType=self.seriesType, vclass=oupclass, precedingRange=self.precedingRange, followingRange=self.followingRange, threshold=self.threshold, orderBy='value')

                if len(similarities) == 0: 
                    if verbose>=1: print('Similarities not present for', h.getTickerTuple())
                    instanceReductionMissingCount += 1
                else:
                    ## slice off top/bottom sections, leaving middle for reduction
                    topCutoff = len(similarities) - math.ceil(len(similarities)*self.config.sets.instanceReduction.top)
                    bottomCutoff = math.floor(len(similarities)*self.config.sets.instanceReduction.bottom)
                    middle = similarities[bottomCutoff:topCutoff-1]

                    ## reduce middle
                    removedDates = []
                    if self.config.sets.instanceReduction.method == ReductionMethod.FIBONACCI:
                        if self.config.sets.instanceReduction.additionalParameter == Direction.DESCENDING:
                            middle.reverse()
                        
                        fibsequence = generateFibonacciSequence(len(middle))
                        removedDates = [vs.date for indx,vs in enumerate(middle) if indx not in fibsequence]

                    elif self.config.sets.instanceReduction.method == ReductionMethod.RANDOM:
                        random.shuffle(middle)
                        selected = random.sample(middle, int(len(middle)*self.config.sets.instanceReduction.additionalParameter))
                        removedDates = [vs.date for vs in middle if vs not in selected]

                    elif self.config.sets.instanceReduction.method == ReductionMethod.ALL:
                        removedDates = [vs.date for vs in middle]

                    totalInstanceReduction += len(removedDates)

                    ## remove indexes from available selections
                    availableIndexes[oupclass][:] = [i for i in availableIndexes[oupclass] if h.data[i].date not in removedDates]
                    
                    if verbose>=2: printInstanceCounts(before=False)

            for oupclass, indexes in availableIndexes.items():
                for sindex in indexes:
                    self.__getattribute__(dmProperty)[TickerDateKeyType(*h.getTickerTuple(), h.data[sindex].date)] = DataPointInstance(
                        self.buildInputVector,
                        h, sindex, oupclass
                    )
        if instanceReductionMissingCount and verbose>=1: print(f'{instanceReductionMissingCount} tickers missing similarities data')
        if verbose>=1: print(f'{totalInstanceReduction} total instances removed')
        
    def initializeFinancialDataHandlers(self, symbolList, explicitValidationSymbolList=[], refresh=False, verbose=None):
        verbose = shortc(verbose, self.verbose)

        ## purge old data
        if refresh: self.financialDataHandlers.clear()

        symbolList += explicitValidationSymbolList
        ANALYZE1 = False
        ANALYZE2 = False
        ANALYZE3 = False

        if gconfig.multicore:
            for ticker, data in tqdmLoopHandleWrapper(tqdmProcessMapHandlerWrapper(multicore_getFinancialDataTickerTuples, symbolList, verbose, desc='Getting financial data'), verbose, desc='Creating financial handlers'):
                self.financialDataHandlers[TickerKeyType(ticker.exchange, ticker.symbol)] = FinancialDataHandler(ticker, data)  

        else:
            gettingtime = 0
            massagingtime = 0
            creatingtime = 0
            insertingtime = 0
            

            restotal = []
            if not ANALYZE2:
                for s in tqdmLoopHandleWrapper(symbolList, verbose, desc='Creating financial handlers'):  
                    if (s.exchange, s.symbol) in unusableSymbols: continue
                    if not ANALYZE1 and not ANALYZE2 and not ANALYZE3:
                        self.financialDataHandlers[TickerKeyType(s.exchange, s.symbol)] = FinancialDataHandler(s, dbm.getFinancialData(s.exchange, s.symbol))
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
                                self.financialDataHandlers[TickerKeyType(r.exchange, r.symbol)] = FinancialDataHandler(s, recdotlist(ret))
                            
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

                fdh: FinancialDataHandler
                for fdh in fdhs:
                    startt = time.time()
                    self.financialDataHandlers[fdh.getTickerKey()] = fdh
                    insertingtime += time.time() - startt


            if verbose>=1 and (ANALYZE1 or ANALYZE2 or ANALYZE3):
                print('initializeFinancialDataHandlers stats')
                print('gettingtime',gettingtime,'seconds')
                print('massagingtime',massagingtime,'seconds')
                print('creatingtime',creatingtime,'seconds')
                print('insertingtime',insertingtime,'seconds')
                print('total',gettingtime+massagingtime+creatingtime+insertingtime,'seconds')

    def initializeStockSplitsHandlers(self, symbolList, explicitValidationSymbolList=[], refresh=False, verbose=None):
        verbose = shortc(verbose, self.verbose)

        symbolList += explicitValidationSymbolList
        ## purge unusable symbols
        symbolList[:] = [s for s in symbolList if (s.exchange, s.symbol) not in unusableSymbols]

        ## purge old data
        if refresh: self.stockSplitsHandlers.clear()

        if gconfig.multicore:
            for ticker, data in tqdmLoopHandleWrapper(tqdmProcessMapHandlerWrapper(partial(multicore_getStockSplitsTickerTuples), symbolList, verbose, desc='Getting stock splits data'), verbose, desc='Creating stock splits handlers'):
                self.stockSplitsHandlers[TickerKeyType(ticker.exchange, ticker.symbol)] = StockSplitsHandler(ticker.exchange, ticker.symbol, data)
                    
        else:
            for s in tqdmLoopHandleWrapper(symbolList, verbose, desc='Creating stock splits handlers'):
                self.stockSplitsHandlers[TickerKeyType(s.exchange, s.symbol)] = StockSplitsHandler(s.exchange, s.symbol, dbm.getStockSplits(s.exchange, s.symbol))

    def initializeTechnicalIndicators(self, verbose=None):
        verbose = shortc(verbose, self.verbose)

        sdh: StockDataHandler
        indc: IndicatorType

        startt = time.time()
        indicators = self.inputVectorFactory.getIndicators()
        ## for determinubg how to handle ADX data: needs total generation, can use cached DIs values, etc
        notInitializingDIData = IndicatorType.DIS not in indicators

        genTimes = {k: [] for k in indicators}
        cachesUsed = 0
        sdhSkips = 0
        sdhs = list(self.stockDataHandlers.values()) + list(self.explicitValidationStockDataHandlers.values())
        for sdh in tqdmLoopHandleWrapper(sdhs, verbose, desc='Initializing technical indicators'):
            if len(sdh.getAvailableSelections()) == 0: 
                sdhSkips += 1
                continue

            genKeys = []
            ## gather cached data and determine what needs calculation
            for indc in indicators:
                ## pre-calculated values should be available
                if indc in self.config.cache.indicators:
                    getIndc = indc
                    if indc == IndicatorType.ADX and notInitializingDIData:
                        ## need to try and use cached DI data even if that indicator will not be used
                        getIndc = IndicatorType.DIS.key
                    indcdata = dbm.getTechnicalIndicatorData(sdh.symbolData.exchange, sdh.symbolData.symbol, getIndc, period=getIndicatorPeriod(indc, self.indicatorConfig))
                    if len(indcdata):
                        if indc == IndicatorType.ADX and notInitializingDIData:
                            ## need to generate ADX data in place off the cached DI data
                            indcdata = generateADXs_AverageDirectionalIndex(periods=self.indicatorConfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ADX], posDIs=[d[0] for d in indcdata], negDIs=[d[1] for d in indcdata])

                        sdh.setIndicatorData(indc, indcdata)
                        cachesUsed += 1
                    
                    else: ## no data, will need to calculate
                        genKeys.append(indc)
                else:
                    genKeys.append(indc)

            genTime = sdh.generateTechnicalIndicators(genKeys, self.indicatorConfig)
            for k in genKeys:
                genTimes[k].append(genTime[k])

        if verbose>=1:
            print('Technical indicator generation complete. Took', time.time() - startt, 'seconds')
            print('Skipped {} stocks'.format(sdhSkips))
            print('Used {} caches'.format(cachesUsed))
            print('Calculated {} sets'.format(sum(len(v) for v in genTimes.values())))
            print('Average calculation times:')
            for k in genTimes.keys():
                print(k.name, '{:.2f}'.format(numpy.average(genTimes[k])))

    def initializeGoogleInterestsHandlers(self, symbolList, explicitValidationSymbolList=[], queryLimit: int=None, refresh=False, verbose=None):
        verbose = shortc(verbose, self.verbose)

        symbolList += explicitValidationSymbolList
        ## purge unusable symbols
        symbolList[:] = [s for s in symbolList if (s.exchange, s.symbol) not in unusableSymbols]

        ## purge old data
        if refresh:
            if not self.explicitValidationSymbolList:
                self.googleInterestsHandlers.clear()
            else:
                ## preserve handlers tied to explicit validation list
                for k in self.googleInterestsHandlers.keys():
                    if k in self.explicitValidationSymbolList: continue
                    else: del self.googleInterestsHandlers[k]


        if gconfig.multicore and not self.maxGoogleInterestHandlers:
            for ticker, relativedata in tqdmLoopHandleWrapper(tqdmProcessMapHandlerWrapper(partial(multicore_getGoogleInterestsTickerTuples, queryLimit=queryLimit), symbolList, verbose, desc='Getting Google interests data'), verbose, desc='Creating Google interests handlers'):
                key = TickerKeyType(ticker.exchange, ticker.symbol)
                self.googleInterestsHandlers[key] = GoogleInterestsHandler(*key.getTuple(), relativedata)
                    
        else:
            for s in tqdmLoopHandleWrapper(symbolList, verbose, desc='Creating Google interests handlers'):
                key = TickerKeyType(s.exchange, s.symbol)
                self.googleInterestsHandlers[key] = GoogleInterestsHandler(*key.getTuple(), dbm.getGoogleInterests(s.exchange, s.symbol, queryLimit=queryLimit))


    def initializeWindow(self, windowIndex):
        self.normalized = False
        windowData = self.windows[windowIndex]
        self.initializeStockDataHandlers(windowData, refresh=True)
        self.initializeStockSplitsHandlers(windowData, refresh=True)
        self.initializeTechnicalIndicators()
        self.initializeGoogleInterestsHandlers(windowData, refresh=True)
        self.initializeStockDataInstances(refresh=True)
        self.setupSets(selectAll=True)
        self.initializedWindow = windowIndex
        gc.collect()

    def setupExplicitValidationSet(self):
        self.explicitValidationSet = list(self.explicitValidationStockDataInstances.values())
        if gconfig.testing.enabled:
            random.shuffle(self.explicitValidationSet)
            self.explicitValidationSet = self.explicitValidationSet[:self.setCount]
        random.shuffle(self.explicitValidationSet)

    def setupSets(self, setCount=None, setSplitTuple=None, minimumSetsPerSymbol=0, selectAll=False, verbose=None):
        verbose = shortc(verbose, self.verbose)

        if not setSplitTuple:
            setSplitTuple = shortc(self.setSplitTuple, (1/3,1/3))

        if self.useAllSets or selectAll:
            self.unselectedInstances = []
            self.selectedInstances = list(self.stockDataInstances.values())

            if gconfig.testing.enabled:
                random.shuffle(self.selectedInstances)
                self.selectedInstances = self.selectedInstances[:self.setCount]

            ## determine window size for iterating through all sets            
            psints, nsints = getInstancesByClass(self.selectedInstances)
            if verbose>=2: print('Class split ratio:', len(psints) / len(self.selectedInstances))
            if not selectAll:
                if len(psints) / len(self.selectedInstances) < gconfig.sets.minimumClassSplitRatio: raise ValueError('Positive to negative set ratio below minimum threshold')
                self.setsSlidingWindowPercentage = getAdjustedSlidingWindowPercentage(len(self.selectedInstances), setCount) 
                if verbose>=2: print('Adjusted sets window size from', setCount, 'to', int(len(self.selectedInstances)*self.setsSlidingWindowPercentage))

        else:
            self.unselectedInstances = list(self.stockDataInstances.values())
            self.selectedInstances = []

            if verbose>=2: print('Selecting', setCount, 'instances')

            ## cover minimums
            if minimumSetsPerSymbol > 0:
                self.unselectedInstances = []
                h: StockDataHandler
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
                            self.selectedInstances.append(self.stockDataInstances[(h.getTickerTuple(), d)])
                        for d in selectDates[sampleSize:]:
                            self.unselectedInstances.append(self.stockDataInstances[(h.getTickerTuple(), d)])
                if verbose>=2: 
                    print(len(self.selectedInstances), 'instances selected to cover minimums')
                    print(len(self.unselectedInstances), 'instances available for remaining selection')

            ## check balance
            psints, nsints = getInstancesByClass(self.selectedInstances)
            puints, nuints = getInstancesByClass(self.unselectedInstances)
            if verbose>=2: print('sel rem', len(self.selectedInstances), setCount, len(self.selectedInstances) < setCount)
            # select remaining
            if len(self.selectedInstances) < setCount:
                pusamplesize = int(min(len(puints), setCount * gconfig.sets.positiveSplitRatio - len(psints)) if setCount / 2 - len(psints) > 0 else len(puints))
                nusamplesize = int(min(len(nuints), setCount - len(self.selectedInstances)) if setCount - len(self.selectedInstances) > 0 else len(nuints))
                if verbose>=2: 
                    print('Positive selected instances', len(psints))
                    print('Negative selected instances', len(nsints))
                    print('Available positive instances', len(puints))
                    print('Available negative instances', len(nuints))
                    print('Positive sample size', pusamplesize)
                    print('Negative sample size', nusamplesize)

                self.selectedInstances.extend(random.sample(puints, pusamplesize))
                self.selectedInstances.extend(random.sample(nuints, nusamplesize))
            else:
                print('Warning: setCount too low for minimum sets per symbol')
            if verbose>=2:
                psints, nsints = getInstancesByClass(self.selectedInstances)
                print('All instances selected\nFinal balance:', len(psints), '/', len(nsints))

            if len(self.selectedInstances) < setCount: raise IndexError('Not enough sets available: %d vs %d' % (len(self.selectedInstances), setCount))
            ## instance selection done

        ## shuffle and distribute instances
        random.shuffle(self.selectedInstances)
        c1, c2 = getInstancesByClass(self.selectedInstances)
        trnStop = setSplitTuple[0]
        vldStop = setSplitTuple[1] + trnStop
        if verbose>=2: print('stops', trnStop, vldStop)
        ## adjust split indexes if split would result in instances being missed (e.g. trnStop = 500 but (math.floor) indexes result in 499)
        trsc1Index = math.floor(trnStop*len(c1))
        trsc2Index = math.floor(trnStop*len(c2))
        if trsc1Index + trsc2Index != trnStop * len(self.selectedInstances):
            trsc1Index += 1
        vsc1Index = math.floor(vldStop*len(c1))
        vsc2Index = math.floor(vldStop*len(c2))
        if vsc1Index + vsc2Index != vldStop * len(self.selectedInstances):
            vsc2Index += 1
        self.trainingSet = c1[:trsc1Index] + c2[:trsc2Index]
        self.validationSet = c1[trsc1Index:vsc1Index] + c2[trsc2Index:vsc2Index]
        self.testingSet = c1[vsc1Index:] + c2[vsc2Index:]

        random.shuffle(self.trainingSet)
        random.shuffle(self.validationSet)
        random.shuffle(self.testingSet)
        if verbose>=1: print('Sets split into', len(self.trainingSet), '/', len(self.validationSet), '/', len(self.testingSet))

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
    
    ## returns the slice of symbol list that corresponds to the given page (1 -> ~len(symbolList)/pageSize)
    def getSymbolListPage(self, page):
        if not self.usePaging: raise NotImplementedError()
        if page < 1 or (page-1)*self.pageSize > len(self.symbolList): raise ArgumentError(None, 'Invalid page number argument')
        return self.symbolList[math.floor((page-1)*self.pageSize):math.floor(page*self.pageSize)]
    
    ## returns how many pages the initial symbol list is divided into
    def getSymbolListPageCount(self):
        if not self.usePaging: raise NotImplementedError()
        return math.ceil(len(self.symbolList)/self.pageSize)

    def getInstanceRatio(self, ticker:TickerKeyType=None, instanceList:List[DataPointInstance]=None, instanceDict:Dict[TickerDateKeyType,DataPointInstance]=None):
        if not ticker and not instanceList and not instanceDict: raise ArgumentError('Missing something to check')

        instances:List[DataPointInstance]
        if ticker:
            if type(ticker) is TickerKeyType: ticker = ticker.getTuple()
            if ticker in self.stockDataHandlers.keys():
                unfilteredInstances = list(self.stockDataInstances.values())
            elif ticker in self.explicitValidationStockDataHandlers:
                unfilteredInstances = list(self.explicitValidationStockDataInstances.values())
            if unfilteredInstances:
                instances = filter(lambda x: x.stockDataHandler.getTickerTuple() == ticker, unfilteredInstances)
            else:
                raise ArgumentError('No data instances for ticker {}'.format(ticker))
        else:
            if instanceList:
                instances = instanceList
            else:
                instances = list(instanceDict.values())

        pclass, nclass = getInstancesByClass(instances)
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
        return ret

    def getKerasSets(self, 
                     classification=0, ## 1 = positive, 2 = negative
                     validationDataOnly=False, exchange=None, symbol=None, slice=None, omitValidation=False, verbose=1):
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

        staticSize, semiseriesSize, seriesSize = self.inputVectorFactory.getInputSize()
        def constrList_helper(set: List[DataPointInstance], isInput, showProgress=True):
            retList = []
            for i in tqdm.tqdm(set, desc='Building {} vector array'.format('input' if isInput else 'output'), leave=(verbose > 0.5)) if showProgress and isInput and verbose != 0 else set:
                retList.append(i.getInputVector() if isInput else i.getOutputVector())
            return retList

        def constrList(set: List, isInput: bool) -> numpy.array:
            return numpy.asarray(constrList_helper(set, isInput))

        def constrList_recurrent(dpiList: List[DataPointInstance]=[], vectorList: List=[], showProgress=True) -> List:
            iterateList = shortc(vectorList, dpiList)
            staticList = []
            semiseriesList = []
            seriesList = []
            for i in tqdm.tqdm(iterateList, desc='Building input vector array', leave=(verbose > 0.5)) if showProgress and verbose != 0 else iterateList:
                staticArr, semiseriesArr, seriesArr = i.getInputVector() if not vectorList else i
                staticList.append(staticArr)
                semiseriesList.append(numpy.reshape(semiseriesArr, (maxQuarters(self.precedingRange), semiseriesSize)))
                seriesList.append(numpy.reshape(seriesArr, (self.precedingRange, seriesSize)))

            return [
                numpy.array(staticList),
                *([numpy.array(semiseriesList)] if gconfig.feature.financials.enabled else []),
                numpy.array(seriesList)
            ]

        def constructDataSet(dpiList=[], vectorList=[]):
            if gconfig.network.recurrent:
                inp = constrList_recurrent(dpiList, vectorList)
            else:
                if vectorList: inp = vectorList
                else: inp = constrList(dpiList, True)
            oup = constrList(dpiList, False)
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

        ## only initialize and maintain so many Google Interests handlers at a time to save on memory
        ## data set construction must run vertically by ticker instead of horizontally by set type
        if self.maxGoogleInterestHandlers:
            if validationDataOnly:
                todoSetDict = {
                    SetType.VALIDATION: validationSet
                }
            else:
                todoSetDict = {
                    SetType.TRAINING: trainingSet,
                    SetType.TESTING: testingSet
                }
                if not omitValidation:
                    todoSetDict[SetType.VALIDATION] = validationSet
            
            ## gather tickers
            todoTickers: Set[TickerKeyType] = set()
            dpi: DataPointInstance
            for tds in todoSetDict.values():
                for dpi in tds:
                    todoTickers.add(dpi.stockDataHandler.getTickerKey())
            todoTickers = list(todoTickers)
            
            ## get input vectors
            inputVectorTuplesDict = { s: [] for s in todoSetDict.keys() }
            t: TickerKeyType
            for tickerSplitIndex in tqdm.tqdm(range(math.ceil(len(todoTickers)/self.maxGoogleInterestHandlers)), desc='Compiling raw input vectors'):
                tickers = todoTickers[tickerSplitIndex*self.maxGoogleInterestHandlers:(tickerSplitIndex+1)*self.maxGoogleInterestHandlers]
                self.initializeGoogleInterestsHandlers(tickers, queryLimit=self.queryLimit, refresh=True, leaveProgressBar=False)

                for stype,ticker,dpi in tqdm.tqdm([(s,t,d) for s in todoSetDict.keys() for t in tickers for d in todoSetDict[s]], desc='Generating vectors', leave=False):
                    if dpi.stockDataHandler.getTickerKey() == ticker:
                        inputVectorTuplesDict[stype].append(dpi.getInputVector())

            ## process input vectors to data sets
            if SetType.TRAINING in todoSetDict.keys():
                trainingDataLambda = lambda: constructDataSet(trainingSet, inputVectorTuplesDict[SetType.TRAINING])
            if SetType.VALIDATION in todoSetDict.keys():
                validationDataLambda = lambda: constructDataSet(validationSet, inputVectorTuplesDict[SetType.VALIDATION])
            if SetType.TESTING in todoSetDict.keys():
                testingDataLambda = lambda: constructDataSet(testingSet, inputVectorTuplesDict[SetType.TESTING])

        else:
            validationDataLambda = lambda: constructDataSet(validationSet)
            trainingDataLambda = lambda: constructDataSet(trainingSet)
            testingDataLambda = lambda: constructDataSet(testingSet)


        if omitValidation:  validationData = None
        else:               validationData = validationDataLambda()
        if validationDataOnly: return validationData
        trainingData = trainingDataLambda()
        testingData = testingDataLambda()

        if gconfig.testing.enabled and verbose > 0.5:
            print('Stock data handler build time', self.getprecstocktime)
            print('Stock indicator build time', self.getprecindctime)
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

    setcount = 50000
    tsplit = DataManager.determineAllSetsTickerSplit(
        setcount,
        # NeuralNetworkManager().get(1641959005),
        # assetTypes=['CS','CLA','CLB','CLC']
        # exchange=['BATS','NASDAQ','NEO','NYSE','NYSE ARCA','NYSE MKT','TSX']
        exchanges=dbm.getDistinctExchangesForHistoricalData(),
        precedingRange=60, followingRange=10, threshold=0.05
    )
    dbm.saveTickerSplit('split{}'.format(str(int(time.time()))), setcount, tsplit)
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
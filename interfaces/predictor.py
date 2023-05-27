import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, operator, numpy, time
import tensorflow as tf
from datetime import date, timedelta
from functools import reduce
from tensorflow.python.framework.errors_impl import InternalError
from typing import Tuple

from utils.other import determinePrecedingRangeType
from managers.databaseManager import DatabaseManager
from managers.vixManager import VIXManager
from managers.marketDayManager import MarketDayManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.dataManager import DataManager
from managers.networkAnalysisManager import NetworkAnalysisManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.stockDataHandler import StockDataHandler
from constants.enums import AccuracyType, InputVectorDataType, OperatorDict, SeriesType
from constants.exceptions import AnchorDateAheadOfLastDataDate, NoData, SufficientlyUpdatedDataNotAvailable
from utils.support import Singleton, asDate, asList, shortc, shortcdict
from globalConfig import config as gconfig

ivf: InputVectorFactory = InputVectorFactory()

POSITIVE_THRESHOLD = 0.5
JUST_BELOW_POSITIVE_THRESHOLD = 0.45
def thresholdRound(val):
    return 1 if val > POSITIVE_THRESHOLD else 0

class Predictor(Singleton):
    vixm: VIXManager = VIXManager()
    dbc: DatabaseManager = DatabaseManager()
    nnm: NeuralNetworkManager = NeuralNetworkManager()

    def __init__(self):
        self.resetTestTimes()
        self.exchanges = []
        self.symbols = []
        pass

    def _initialize(self, **kwargs
    # exchange=[], symbols=[]
    ) -> Tuple[NeuralNetworkInstance, list]:
        exchanges = asList(shortcdict(kwargs, 'exchange', []))
        symbols = asList(shortcdict(kwargs, 'symbol', []))

        nn = self.nnm.get(kwargs['networkid']) if 'networkid' in kwargs.keys() else kwargs['network']
        nn.load()

        needNewDataManager = False
        if len(self.symbols) == 0:
            for e in exchanges:
                if e not in self.exchanges:
                    needNewDataManager = True
                    break
        else:
            for s in symbols:
                if s not in self.symbols:
                    needNewDataManager = True
                    break
            
        if needNewDataManager or not hasattr(self, 'dm'):
            self.dm: DataManager = DataManager.forPredictor(nn, **kwargs)

        self.exchanges = exchanges
        self.symbols = symbols

        return nn

    @classmethod
    def resetTestTimes(self):
        ## prediction
        self.testing_getSymbolsTime = 0
        self.testing_getPrecedingReportsTime = 0
        self.testing_inputVectorBuildTime = 0
        self.testing_predictTime = 0
        
        ## weighting
        self.wt_testing_getSymbolsTime = 0
        self.wt_testing_getStockAccuracyTime = 0

    @classmethod
    def predict(cls, exchange, symbol, anchorDate=date.today().isoformat(), networkid=None, network=None, **kwargs):
        if network:
            networkid = network.id
        if 'anchorDates' in kwargs:
            anchorDate = None

        return Predictor.predictAll(networkid, anchorDate, exchange=[exchange], symbol=[symbol], **kwargs)

    ## returns stockData, precedingIndicators
    def __getPrecedingRangeData(self, network, exchange, symbol, anchorDate):
        sdh: StockDataHandler = self.dm.stockDataHandlers[(exchange, symbol)]
        d = MarketDayManager.getPreviousMarketDay(asDate(anchorDate))
        ind = None
        for index, item in enumerate(sdh.data):
            if item.date == d.isoformat():
                ind = index + 1
                break
        return sdh.getPrecedingSet(ind), sdh.getPrecedingIndicators(ind)

    def __buildPredictInputTuple(self, network, exchange, symbol, anchorDate=date.today().isoformat()):
        if gconfig.testing.predictor:
            startt = time.time()
        symbolinfo = self.dbc.getSymbols(exchange, symbol)[0]
        if gconfig.testing.predictor:
            self.testing_getSymbolsTime += time.time() - startt

        if gconfig.testing.predictor:
            startt = time.time()
        financialData = []
        if (exchange, symbol) in self.dm.financialDataHandlers.keys():
            financialData = self.dm.financialDataHandlers[(exchange, symbol)].getPrecedingReports(anchorDate, network.stats.precedingRange)
        if gconfig.testing.predictor:
            self.testing_getPrecedingReportsTime += time.time() - startt
        
        stockDataSet, precedingIndicators = self.__getPrecedingRangeData(network, exchange, symbol, anchorDate)

        inputVector = network.inputVectorFactory.build(
            stockDataSet=stockDataSet,
            vixData=self.vixm.data,
            financialDataSet=financialData,
            googleInterests=self.dm.googleInterestsHandlers[(exchange, symbol)].getPrecedingRange(anchorDate, network.stats.precedingRange),
            stockSplits=[],
            indicators=precedingIndicators,
            foundedDate=symbolinfo.founded,
            sector=symbolinfo.sector, 
            exchange=exchange,
            etfFlag=symbolinfo.asset_type == 'ETF'
        )
        if gconfig.testing.predictor:
            self.testing_inputVectorBuildTime += time.time() - startt
        
        return inputVector

    @classmethod
    def predictAll(cls, networkid, 
        anchorDate=None, #date.today().isoformat(),
        anchorDates=[],
        postPredictionWeighting=True,
        # exchange=None, exchange=[], excludeExchange=[]
        numberofWeightingsLimit=0,
        verbose=1,
        **kwargs
    ):
        self = cls()
        singleSymbol = 'symbol' in kwargs and len(kwargs['symbol']) == 1


        if anchorDate:
            anchorDates = [anchorDate]
        elif len(anchorDates) == 0:
            anchorDates = [date.today()]
        anchorDates = [asDate(dt) for dt in anchorDates]

        anchorDateArg = max(anchorDates)
        nn = self._initialize(networkid=networkid, anchorDate=anchorDateArg, postPredictionWeighting=postPredictionWeighting, 
                              skipAllDataInitialization='maxPageSize' in kwargs,
                              **kwargs)
        tickers = self.dm.symbolList
        if len(tickers) == 0:
            print('No tickers available for anchor date of', anchorDateArg)
            return

        if verbose == 1:
            if singleSymbol:
                print('Starting prediction{} for'.format('' if len(anchorDates) < 2 else 's'), kwargs['exchange'][0], ':', kwargs['symbol'][0])
            else:
                print('Starting predictions for', len(tickers), 'tickers') ## starting on', anchorDate)

        predictionCounter = 0
        predictionExceptionCounter = 0
        predictionList = []
        predictionInputVectors = {e: [] for e in InputVectorDataType} if gconfig.network.recurrent else []
        predictionTickers = []
        if gconfig.network.recurrent:
            staticsize, semiseriessize, seriessize = nn.inputVectorFactory.getInputSize()

        ## build input vectors for all tickers; iterating through pages of symbol list
        loopingTickers = True
        maxPage = self.dm.getSymbolListPageCount() if self.dm.usePaging else None
        pageLoopHandle = range(1, maxPage+1) if self.dm.usePaging else [0]
        for page in pageLoopHandle:
            loopHandle = tickers
            if self.dm.usePaging:
                self.dm.initializeAllDataForPage(page)
                loopHandle = self.dm.getSymbolListPage(page)
            if len(anchorDates) > 1:
                loopingTickers = False
                loopHandle = anchorDates
            if verbose > 0:
                loopHandle = tqdm.tqdm(loopHandle, desc='Building{}...'.format(' page {}/{}'.format(page, maxPage) if self.dm.usePaging else ''))
            
            for tkrORdt in loopHandle:
                if loopingTickers:
                    dt = anchorDates[0]
                    texchange = tkrORdt.exchange
                    tsymbol = tkrORdt.symbol
                else:
                    dt = tkrORdt
                    texchange = kwargs['exchange'][0]
                    tsymbol = kwargs['symbol'][0]
                try:
                    inptpl = self.__buildPredictInputTuple(nn, texchange, tsymbol, anchorDate=dt.isoformat())
                    if gconfig.network.recurrent:
                        predictionInputVectors[InputVectorDataType.STATIC].append(inptpl[0].reshape(-1, staticsize))
                        if gconfig.feature.financials.enabled:
                            predictionInputVectors[InputVectorDataType.SEMISERIES].append(inptpl[1].reshape(-1, nn.stats.precedingRange, semiseriessize))
                        predictionInputVectors[InputVectorDataType.SERIES].append(inptpl[2].reshape(-1, nn.stats.precedingRange, seriessize))
                    else:
                        predictionInputVectors.append(inptpl)
                
                    predictionTickers.append(tkrORdt)
                except (ValueError, tf.errors.InvalidArgumentError, SufficientlyUpdatedDataNotAvailable, KeyError, AnchorDateAheadOfLastDataDate, TypeError) as e:
                # except IndexError:
                    # print(e)
                    # raise e

                    predictionExceptionCounter += 1

                    pass

                if gconfig.testing.enabled and predictionCounter > 2:
                    break

        if gconfig.network.recurrent:
            predictionInputVectors = [
                predictionInputVectors[InputVectorDataType.STATIC],
                *([predictionInputVectors[InputVectorDataType.SEMISERIES]] if gconfig.feature.financials.enabled else []),
                predictionInputVectors[InputVectorDataType.SERIES]
            ]

        ## run batch predict for all vectors
        if verbose == 1: print('Predicting...')
        if gconfig.testing.predictor:
            startt = time.time()
        predictResults = nn.predict(predictionInputVectors, batchInput=True, raw=gconfig.predictor.ifBinaryUseRaw, verbose=verbose)
        if gconfig.testing.predictor:
            self.testing_predictTime += time.time() - startt

        ## (unpack and) massage prediction outputs
        if singleSymbol and len(anchorDates) < 2:
            p = predictResults[0][0]
            predictResults = thresholdRound(p) if gconfig.predictor.ifBinaryUseRaw else p
        else:
            lstlength = len(predictionTickers) if len(anchorDates) < 2 else len(anchorDates)
            loopHandle = tqdm.trange(lstlength, desc='Unpacking...') if verbose > 0 else range(lstlength)
            for ti in loopHandle:
                p = predictResults[ti][0] #.numpy()
                t = predictionTickers[ti]
                val = thresholdRound(p) if gconfig.predictor.ifBinaryUseRaw else p
                if singleSymbol:
                    predictionList.append((anchorDates[ti], val))
                elif val == 1:
                    predictionList.append((t.exchange, t.symbol, p))
            if singleSymbol: predictResults = predictionList

        if gconfig.testing.predictor:
            print('testing_getSymbolsTime', self.testing_getSymbolsTime, 'seconds')
            print('testing_getPrecedingReportsTime', self.testing_getPrecedingReportsTime, 'seconds')
            print('testing_inputVectorBuildTime', self.testing_inputVectorBuildTime, 'seconds')
            print('testing_predictTime', self.testing_predictTime, 'seconds')

        if len(anchorDates) < 2:
            if singleSymbol:
                if predictionExceptionCounter:
                    print('There was an exception for this ticker')
                else:
                    print(('{}redicted to'.format('P' if predictResults == 1 else 'Not p')) if gconfig.predictor.ifBinaryUseRaw else '{:.2f}% chance ticker will'.format(predictResults*100), 'exceed threshold from', dt.isoformat(), 'to', MarketDayManager.advance(dt, nn.stats.followingRange).isoformat())
            else:
                tickersMeetingThreshold = len(predictionList)
                ## perform additional weighting on the predict results accuracies
                if postPredictionWeighting:
                    weightedAccuracies = {}

                    key = AccuracyType.OVERALL
                    # if nn.stats.accuracyType == AccuracyType.POSITIVE:
                    #     key = AccuracyType.NEGATIVE
                    # elif nn.stats.accuracyType == AccuracyType.NEGATIVE:
                    #     key = AccuracyType.POSITIVE

                    networkFactor = getattr(nn.stats, key.statsName)
                    weightedAccuracyLambda = lambda v: reduce(operator.mul, list(v), 1) * 100
                    weightingsCount = 0
                    try:
                        tqdmhandle = tqdm.tqdm(sorted(predictionList, key=lambda x: x[2], reverse=True), desc='Weighting...')
                        for s in tqdmhandle:
                            exchange, symbol, prediction = s

                            if gconfig.testing.predictor:
                                startt = time.time()
                            symbolInfo = self.dbc.getSymbols(exchange=exchange, symbol=symbol)[0]
                            if gconfig.testing.predictor:
                                self.wt_testing_getSymbolsTime += time.time() - startt

                            sectorFactor = 1
                            if symbolInfo.sector:
                                pass

                            ## network analysis factors
                            # nanm = NetworkAnalysisManager(nn)
                            # symbolFactor = nanm.getStockAccuracy(exchange, symbol)
                            # precedingRangeFactor = nanm.getStockPrecedingRangeTypesAccuracy(determinePrecedingRangeType(self.__getPrecedingRangeData(nn, exchange, symbol, anchorDates[0])))


                            # weightedAccuracies[s] = (prediction, networkFactor, sectorFactor, symbolFactor, precedingRangeFactor)
                            weightedAccuracies[s] = (prediction, networkFactor, sectorFactor)
                            weightingsCount += 1
                            if numberofWeightingsLimit and weightingsCount >= numberofWeightingsLimit:
                                break

                            c = 0
                            postfixstr = ''
                            for k, v in sorted(weightedAccuracies.items(), key=lambda x: weightedAccuracyLambda(x[1]), reverse=True):
                                if c > 2: break
                                if c > 0:
                                    postfixstr += ' || '
                                c += 1
                                postfixstr += k[0] + ';' + k[1] + ': {:.3f}%'.format(float(weightedAccuracyLambda(v)))

                            tqdmhandle.set_postfix_str(postfixstr)


                    except (InternalError, KeyboardInterrupt):
                        pass

                    ## evaluate if tickers still meet threshold
                    tickersMeetingThreshold = 0
                    tickersJustBelowThreshold = 0
                    for v in weightedAccuracies.values():
                        reducedv = weightedAccuracyLambda(v)
                        if reducedv > POSITIVE_THRESHOLD:
                            tickersMeetingThreshold += 1
                        elif reducedv > JUST_BELOW_POSITIVE_THRESHOLD:
                            tickersJustBelowThreshold += 1

                    if verbose > 1:
                        print('wt_testing_getSymbolsTime', self.wt_testing_getSymbolsTime, 'seconds')
                        print('wt_testing_getStockAccuracyTime', self.wt_testing_getStockAccuracyTime, 'seconds::')

                    for k, v in sorted(weightedAccuracies.items(), key=lambda x: weightedAccuracyLambda(x[1])):
                        reducedv = weightedAccuracyLambda(v)
                        if (tickersMeetingThreshold > 0 and reducedv > 0.5) or (tickersMeetingThreshold == 0 and reducedv > JUST_BELOW_POSITIVE_THRESHOLD) or verbose > 1:
                            print(k, ':', reducedv, '%  <-', v)
                    print('Factors: predictions, network, sector, symbol, precrange')


                print(predictionExceptionCounter, '/', len(tickers), 'had exceptions')
                print(tickersMeetingThreshold, '/', len(tickers) - predictionExceptionCounter, 'predicted to exceed threshold from EOD', MarketDayManager.getPreviousMarketDay(dt.isoformat()), 'to', MarketDayManager.advance(MarketDayManager.getLastMarketDay(dt), nn.stats.followingRange).isoformat())
                if tickersMeetingThreshold == 0:
                    print(tickersJustBelowThreshold, '/', len(tickers) - predictionExceptionCounter, 'are just below the threshold')

        return predictResults if singleSymbol else weightedAccuracies

if __name__ == '__main__':
    # p: Predictor = Predictor()

    # fl, arg1, *argv = sys.argv
    # if arg1.lower() == 'predict':
    #     c.startAPICollection(argv[0].lower(), SeriesType[argv[1].upper()] if len(argv) > 1 else None)
    # elif arg1.lower() == 'all':
    #     c.collectVIX()


    # print(p.predict('nyse', 'gme', '2021-03-12', networkid='1617767788',))
    # print(Predictor.predict('NASDAQ', 'PROG', '2021-09-26', networkid='1633809914'))
    # p.predictAll('1623156322', '2021-05-30', exchange=gconfig.testing.exchange) ## 0.05
    # p.predictAll('1623009648', '2021-05-30', exchange='NYSE') ## 0.1
    # p.predictAll('1623013426', '2021-05-30', exchange='NYSE') ## 0.15
    # p.predictAll('1623016597', '2021-05-30', exchange='NYSE') ## 0.2
    # p.predictAll('1623018727', '2021-05-30', exchange='NYSE') ## 0.25
    # Predictor.predictAll('1633809914', '2021-12-11', exchanges=['NYSE', 'NASDAQ']) ## 0.05 - 10d
    # Predictor.predictAll('1631423638', '2021-11-20', exchanges=['NYSE', 'NASDAQ'], numberOfWeightingsLimit=200) ## 0.1 - 30d
    # p.predictAll('1631423638', exchanges=['NYSE', 'NASDAQ']) ## 0.1 - 30d
    Predictor.predictAll('1681021857', '2023-04-07', exchanges=['NYSE', 'NASDAQ'], numberofWeightingsLimit=500, assetTypes=['CS', 'CLA', 'CLB', 'CLC'], maxPageSize=500) ## 0.05 - 10d - recurrent
    # Predictor.predict('NYSE', 'GME', '2021-12-28', '1678667196')
    # Predictor.predict('NYSE', 'GME', networkid='1641959005', anchorDates=['2021-12-28', '2021-12-31']) ## 0.05 - 10d - recurrent


    # for x in range(365):
    #     dt = date.today() - timedelta(days=x+1)
    #     p.predictAll('1631423638', dt.isoformat(), exchanges=['NYSE', 'NASDAQ']) ## 0.1 - 30d

    # c.start(SeriesType.DAILY)
    # c.start()
    # c._collectFromAPI('polygon', [recdotdict({'symbol':'KRP'})], None)

    # nn, _ = p._initialize(networkid='1633809914', anchorDate='2021-10-29')
    # exchange='NASDAQ'
    # symbol='MRIN'
    # key = AccuracyType.OVERALL

    print('done')


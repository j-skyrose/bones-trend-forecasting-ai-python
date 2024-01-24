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
from constants.values import standardExchanges
from managers.databaseManager import DatabaseManager
from managers.marketDayManager import MarketDayManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.dataManager import DataManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.stockDataHandler import StockDataHandler
from constants.enums import AccuracyType, InputVectorDataType
from constants.exceptions import AnchorDateAheadOfLastDataDate, SufficientlyUpdatedDataNotAvailable
from utils.support import Singleton, asDate, asList, getIndex, shortc, shortcdict, tqdmLoopHandleWrapper
from globalConfig import config as gconfig

ivf: InputVectorFactory = InputVectorFactory()
nnm: NeuralNetworkManager = NeuralNetworkManager()
dbm: DatabaseManager = DatabaseManager()

POSITIVE_THRESHOLD = 0.5
JUST_BELOW_POSITIVE_THRESHOLD = 0.45
def thresholdRound(val):
    return 1 if val > POSITIVE_THRESHOLD else 0

class Predictor(Singleton):
    dm: DataManager = None
    exchanges = []
    symbols = []

    def __init__(self):
        self.resetTestTimes()

    def _initialize(self, **kwargs
    # exchange=[], symbols=[]
    ) -> Tuple[NeuralNetworkInstance, list]:
        exchanges = asList(shortcdict(kwargs, 'exchange', []))
        symbols = asList(shortcdict(kwargs, 'symbol', []))

        nn = nnm.get(kwargs['network'])
        nn.load()

        needNewDataManager = False
        if len(Predictor.symbols) == 0:
            for e in exchanges:
                if e not in Predictor.exchanges:
                    needNewDataManager = True
                    break
        else:
            for s in symbols:
                if s not in Predictor.symbols:
                    needNewDataManager = True
                    break
            
        if needNewDataManager or not Predictor.dm:
            Predictor.dm = DataManager.forPredictor(nn, **kwargs)

        Predictor.exchanges = exchanges
        Predictor.symbols = symbols

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
    def predict(cls, exchange, symbol, **kwargs):
        return cls.predictAll(exchange=asList(exchange), symbol=asList(symbol), **kwargs)

    def __getHandlerAndIndex(self, exchange, symbol, anchorDate):
        '''returns stockDataHandler, index of anchorDate'''
        sdh: StockDataHandler = Predictor.dm.stockDataHandlers[(exchange, symbol)]
        d = MarketDayManager.getPreviousMarketDay(asDate(anchorDate)).isoformat()
        index = getIndex(sdh.data, lambda x: x.period_date == d)
        if index is None:
            raise ValueError(f'{anchorDate} not found for {exchange}:{symbol} stock data')
        elif index not in sdh.getAvailableSelections():
            raise ValueError(f'{anchorDate} not a valid selection for {exchange}:{symbol} stock data')
        return sdh, index

    def __buildPredictInputTuple(self, exchange, symbol, anchorDate=date.today().isoformat()):
        if gconfig.testing.predictor: startt = time.time()
        inputVector = Predictor.dm.buildInputVector(*self.__getHandlerAndIndex(exchange, symbol, anchorDate))
        if gconfig.testing.predictor: self.testing_inputVectorBuildTime += time.time() - startt
        return inputVector

    @classmethod
    def predictAll(cls, 
        anchorDate=None, #date.today().isoformat(),
        postPredictionWeighting=True,
        # exchange=None, excludeExchange=[], network=None,
        numberofWeightingsLimit=0,
        notMeetingThresholdsPrintLimit=5,
        verbose=1,
        **kwargs
    ):
        if 'maxPageSize' not in kwargs:
            kwargs['maxPageSize'] = 500

        self = cls()
        singleSymbol = 'symbol' in kwargs and len(kwargs['symbol']) == 1

        if anchorDate:
            anchorDates = asList(anchorDate)
        elif len(anchorDates) == 0:
            anchorDates = [date.today()]
        anchorDates = [asDate(dt) for dt in anchorDates]

        anchorDateArg = max(anchorDates)
        nn = self._initialize(anchorDate=anchorDateArg, postPredictionWeighting=postPredictionWeighting, 
                              skipAllDataInitialization='maxPageSize' in kwargs, verbose=verbose,
                              **kwargs)
        tickers = cls.dm.symbolList
        if len(tickers) == 0:
            print('No tickers available for anchor date of', anchorDateArg)
            return

        if verbose == 1:
            if singleSymbol:
                print('Starting prediction{} for'.format('' if len(anchorDates) < 2 else 's'), kwargs['exchange'][0], ':', kwargs['symbol'][0])
            else:
                print('Starting predictions for', len(tickers), 'tickers') ## starting on', anchorDate)

        predictionCounter = 0
        predictionExceptions = []
        predictionList = []
        predictionInputVectors = {e: [] for e in InputVectorDataType} if gconfig.network.recurrent else []
        predictionTickers = []
        if gconfig.network.recurrent:
            staticsize, semiseriessize, seriessize = nn.inputVectorFactory.getInputSize()

        ## build input vectors for all tickers; iterating through pages of symbol list
        loopingTickers = True
        maxPage = cls.dm.getSymbolListPageCount() if cls.dm.usePaging else None
        pageLoopHandle = range(1, maxPage+1) if cls.dm.usePaging else [0]
        for page in pageLoopHandle:
            loopList = tickers
            if cls.dm.usePaging:
                cls.dm.initializeAllDataForPage(page)
                loopList = cls.dm.getSymbolListPage(page)
            if len(anchorDates) > 1:
                loopingTickers = False
                loopList = anchorDates
            
            for tkrORdt in tqdmLoopHandleWrapper(loopList, verbose=verbose, desc='Building{}...'.format(' page {}/{}'.format(page, maxPage) if cls.dm.usePaging else '')):
                if loopingTickers:
                    dt = anchorDates[0]
                    texchange = tkrORdt.exchange
                    tsymbol = tkrORdt.symbol
                else:
                    dt = tkrORdt
                    texchange = kwargs['exchange'][0]
                    tsymbol = kwargs['symbol'][0]
                try:
                    inptpl = self.__buildPredictInputTuple(texchange, tsymbol, anchorDate=dt.isoformat())
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
                    if verbose > 0: print(e.__class__, e)
                    # raise e

                    predictionExceptions.append(e)

                    pass

                if gconfig.testing.enabled and predictionCounter > 2:
                    break

        if gconfig.network.recurrent:
            predictionInputVectors = [
                predictionInputVectors[InputVectorDataType.STATIC],
                *([predictionInputVectors[InputVectorDataType.SEMISERIES]] if gconfig.feature.financials.enabled else []),
                predictionInputVectors[InputVectorDataType.SERIES]
            ]

        if len(predictionInputVectors) == 0 or len(predictionInputVectors[0]) == 0:
            print(predictionExceptions[0])
            if not singleSymbol:
                print(predictionExceptions[1])
                print(predictionExceptions[2])
            raise ValueError('No input vectors built')

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
                # elif val == 1:
                else:
                    predictionList.append((t.exchange, t.symbol, p))
            if singleSymbol: predictResults = predictionList

        if gconfig.testing.predictor:
            print('testing_getSymbolsTime', self.testing_getSymbolsTime, 'seconds')
            print('testing_getPrecedingReportsTime', self.testing_getPrecedingReportsTime, 'seconds')
            print('testing_inputVectorBuildTime', self.testing_inputVectorBuildTime, 'seconds')
            print('testing_predictTime', self.testing_predictTime, 'seconds')

        if len(anchorDates) < 2:
            if singleSymbol:
                if len(predictionExceptions) > 0:
                    print('There was an exception for this ticker')
                else:
                    print(('{}redicted to'.format('P' if predictResults == 1 else 'Not p')) if gconfig.predictor.ifBinaryUseRaw else '{:.2f}% chance ticker will'.format(predictResults*100), 'exceed threshold from EOD', MarketDayManager.getPreviousMarketDay(dt).isoformat(), 'to', MarketDayManager.advance(dt, nn.stats.followingRange).isoformat())
            else:
                tickersMeetingThreshold = []
                tickersJustBelowThreshold = []
                tickersNotMeetingThreshold = []

                ## perform additional weighting on the predict results accuracies
                if postPredictionWeighting:
                    key = AccuracyType.OVERALL
                    # if nn.stats.accuracyType == AccuracyType.POSITIVE:
                    #     key = AccuracyType.NEGATIVE
                    # elif nn.stats.accuracyType == AccuracyType.NEGATIVE:
                    #     key = AccuracyType.POSITIVE

                    networkFactor = getattr(nn.stats, key.statsName)
                    weightedAccuracyLambda = lambda v: reduce(operator.mul, list(v), 1)
                    weightingsCount = 0
                    try:
                        sortedPredictionList = sorted(predictionList, key=lambda x: x[2], reverse=True)
                        ## focus on higher value predictions first
                        for phase,phaseString in enumerate(['raw prediction meets threshold', 'raw prediction just under threshold', 'remainder']):
                            if phase == 1 and len(tickersMeetingThreshold) > 0: break
                            elif phase == 2 and len(tickersJustBelowThreshold) > 0: break

                            ## determine weighting factors and assign ticker to appropriate set
                            tqdmhandle = tqdmLoopHandleWrapper(sortedPredictionList, verbose=verbose, desc=f'Weighting {phaseString}')
                            for s in tqdmhandle:
                                exchange, symbol, prediction = s
                                ## raw prediction values below appropriate threshold will not rise above it with additional weighting, so skip until next phase
                                if phase == 0 and prediction <= POSITIVE_THRESHOLD: continue
                                elif phase == 1 and prediction <= JUST_BELOW_POSITIVE_THRESHOLD: continue

                                if gconfig.testing.predictor:
                                    startt = time.time()
                                symbolInfo = dbm.getSymbols(exchange=exchange, symbol=symbol)[0]
                                if gconfig.testing.predictor:
                                    self.wt_testing_getSymbolsTime += time.time() - startt

                                sectorFactor = 1
                                if symbolInfo.sector:
                                    pass

                                ## network analysis factors
                                # nanm = NetworkAnalysisManager(nn)
                                # symbolFactor = nanm.getStockAccuracy(exchange, symbol)
                                # precedingRangeFactor = nanm.getStockPrecedingRangeTypesAccuracy(determinePrecedingRangeType(self.__getPrecedingRangeData(nn, exchange, symbol, anchorDates[0])))


                                # val = (exchange, symbol, (prediction, networkFactor, sectorFactor, symbolFactor, precedingRangeFactor))
                                # val = (exchange, symbol, (prediction, networkFactor, sectorFactor))
                                val = (exchange, symbol, (prediction, networkFactor, sectorFactor))
                                weightedAcc = weightedAccuracyLambda(val[2])
                                if phase == 0 and weightedAcc > POSITIVE_THRESHOLD:
                                    tickersMeetingThreshold.append(val)
                                elif phase == 1 and weightedAcc > JUST_BELOW_POSITIVE_THRESHOLD:
                                    tickersJustBelowThreshold.append(val)
                                else:
                                    tickersNotMeetingThreshold.append(val)
                                weightingsCount += 1
                                if numberofWeightingsLimit and weightingsCount >= numberofWeightingsLimit:
                                    break

                                if verbose >= 1:
                                    c = 0
                                    postfixstr = ''
                                    for exchange, symbol, factorTuple in sorted(tickersMeetingThreshold + tickersJustBelowThreshold + tickersNotMeetingThreshold, key=lambda x: weightedAccuracyLambda(x[2]), reverse=True):
                                        if c > 2: break
                                        if c > 0:
                                            postfixstr += ' || '
                                        c += 1
                                        postfixstr += f'{exchange}:{symbol}; {float(weightedAccuracyLambda(factorTuple))*100:.3f}%'

                                    tqdmhandle.set_postfix_str(postfixstr)

                    except (InternalError, KeyboardInterrupt):
                        pass

                    ## sort each list of prediction tuples
                    tickersMeetingThreshold.sort(key=lambda x: weightedAccuracyLambda(x[2]))
                    tickersJustBelowThreshold.sort(key=lambda x: weightedAccuracyLambda(x[2]))
                    tickersNotMeetingThreshold.sort(key=lambda x: weightedAccuracyLambda(x[2]))

                    if verbose > 1:
                        print('wt_testing_getSymbolsTime', self.wt_testing_getSymbolsTime, 'seconds')
                        print('wt_testing_getStockAccuracyTime', self.wt_testing_getStockAccuracyTime, 'seconds::')


                else: ## no additional weighting of prediction outputs
                    for tpl in sorted(predictionList, key=lambda x: x[2]):
                        _,_,val = tpl
                        if val > POSITIVE_THRESHOLD:
                            tickersMeetingThreshold.append(tpl)
                        elif val > JUST_BELOW_POSITIVE_THRESHOLD:
                            tickersJustBelowThreshold.append(tpl)
                        else:
                            tickersNotMeetingThreshold.append(tpl)

                ## determine most important set that has tickers; for output
                noThresholdAdjacentTickers = False
                outputTickers = tickersNotMeetingThreshold
                if len(tickersMeetingThreshold) > 0:
                    outputTickers = tickersMeetingThreshold
                elif len(tickersJustBelowThreshold) > 0:
                    outputTickers = tickersJustBelowThreshold
                else:
                    noThresholdAdjacentTickers = True

                if verbose >= 1:
                    ## output tickers and their prediction (+ factors) from the highest value set
                    print()
                    printed = 0
                    for exchange, symbol, val in outputTickers:
                        if noThresholdAdjacentTickers and printed >= notMeetingThresholdsPrintLimit: break
                        printval = val
                        if postPredictionWeighting:
                            printval = weightedAccuracyLambda(val)
                        print(f"{exchange}:{symbol} : {printval * 100} % {f'<- {val}' if postPredictionWeighting else ''}")
                        printed += 1
                    if postPredictionWeighting: print('Factors: predictions, network, sector, symbol, precrange')

                    ## output summary of the predictions
                    print()
                    print(len(predictionExceptions), '/', len(tickers), 'had exceptions')
                    print(len(tickersMeetingThreshold), '/', len(predictionTickers), 'predicted to exceed threshold from EOD', MarketDayManager.getPreviousMarketDay(dt).isoformat(), 'to', MarketDayManager.advance(MarketDayManager.getLastMarketDay(dt), nn.stats.followingRange).isoformat())
                    if len(tickersMeetingThreshold) == 0:
                        print(len(tickersJustBelowThreshold), '/', len(predictionTickers), 'are just below the threshold')

        return predictResults if singleSymbol else (tickersMeetingThreshold, tickersJustBelowThreshold, tickersNotMeetingThreshold)

if __name__ == '__main__':
    # print(p.predict('nyse', 'gme', '2021-03-12', networkid='1617767788',))
    # print(Predictor.predict('NASDAQ', 'PROG', '2021-09-26', networkid='1633809914'))
    # p.predictAll('1623156322', '2021-05-30', exchange=gconfig.testing.exchange) ## 0.05
    # p.predictAll('1623009648', '2021-05-30', exchange='NYSE') ## 0.1
    # p.predictAll('1623013426', '2021-05-30', exchange='NYSE') ## 0.15
    # p.predictAll('1623016597', '2021-05-30', exchange='NYSE') ## 0.2
    # p.predictAll('1623018727', '2021-05-30', exchange='NYSE') ## 0.25
    # Predictor.predictAll('1633809914', '2021-12-11', exchange=['NYSE', 'NASDAQ']) ## 0.05 - 10d
    # Predictor.predictAll('1631423638', '2021-11-20', exchange=['NYSE', 'NASDAQ'], numberOfWeightingsLimit=200) ## 0.1 - 30d
    # p.predictAll('1631423638', exchange=['NYSE', 'NASDAQ']) ## 0.1 - 30d
    Predictor.predictAll('2023-01-27', 
                            network='1696139601',
                        #  exchange=standardExchanges, 
                        exchange=['BATS','NASDAQ','NYSE','NYSE ARCA','NYSE MKT'],
                         postPredictionWeighting=False,
                        #  numberofWeightingsLimit=500, 
                        #  assetTypes=['CS', 'CLA', 'CLB', 'CLC'], 
                         maxPageSize=50) ## 0.05 - 10d - recurrent
    # Predictor.predict('NYSE', 'PLTR', '2023-05-08', networkid='1684532612')
    # print(Predictor.predict('NASDAQ', 'AAPL', networkid='1684532612', 
    #                         anchorDates=[f'2023-04-{d}' for d in [(val if val > 9 else '0'+str(val)) for val in range(20,30)]])
    #                         # anchorDates=[f'2023-05-{d}' for d in [(val if val > 9 else '0'+str(val)) for val in range(8,21)]])
    #                         )
    # Predictor.predict('NYSE', 'GME', networkid='1641959005', anchorDates=['2021-12-28', '2021-12-31']) ## 0.05 - 10d - recurrent

    # for x in range(365):
    #     dt = date.today() - timedelta(days=x+1)
    #     p.predictAll('1631423638', dt.isoformat(), exchange=['NYSE', 'NASDAQ']) ## 0.1 - 30d


    print('done')


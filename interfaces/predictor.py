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

from utils.other import normalizeStockData
from interfaces.networkAnalyzer import Analyzer
from managers.databaseManager import DatabaseManager
from managers.vixManager import VIXManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.dataManager import DataManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from constants.enums import AccuracyType, LossAccuracy, OperatorDict, SeriesType
from constants.exceptions import AnchorDateAheadOfLastDataDate, NoData, SufficientlyUpdatedDataNotAvailable
from utils.support import Singleton, shortc
from globalConfig import config as gconfig

ivf: InputVectorFactory = InputVectorFactory()

class Predictor(Singleton):
    analyzer: Analyzer = None
    vixm: VIXManager = VIXManager()
    dbc: DatabaseManager = DatabaseManager()
    nnm: NeuralNetworkManager = NeuralNetworkManager()

    def __init__(self):
        self.resetTestTimes()
        self.exchanges = []
        self.symbols = []
        pass

    def _getNeuralNetwork(self, networkid, **kwargs) -> NeuralNetworkInstance:
        try:
            nn = self.nnm.get(networkid)
            nn.load()

            if 'exchange' in kwargs.keys() and kwargs['exchange']:
                kwargs['exchanges'] = [kwargs['exchange']]
            del kwargs['exchange']

            self.analyzer = Analyzer(nn, **kwargs)

            return nn
        except KeyError:
            print('Network ID not found')

    def _initialize(self, exchanges=[], symbols=[], **kwargs):
        nn = self.nnm.get(kwargs['networkid']) if 'networkid' in kwargs.keys() else kwargs['network']
        nn.load()

        needNewAnalyzer = False
        if len(self.symbols) == 0:
            for e in exchanges:
                if e not in self.exchanges:
                    needNewAnalyzer = True
                    break
        else:
            for s in symbols:
                if s not in self.symbols:
                    needNewAnalyzer = True
                    break
            
        if needNewAnalyzer or not self.analyzer:
            self.analyzer = Analyzer(nn, forPredictor=True, **kwargs)
            
        self.exchanges = exchanges
        self.symbols = symbols

        return nn, self.dbc.getLastUpdatedInfo(nn.stats.seriesType, kwargs['anchorDate'], dateModifier=OperatorDict.LESSTHANOREQUAL, **kwargs)

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

        return Predictor.predictAll(networkid, anchorDate, exchanges=[exchange], symbols=[symbol], **kwargs)

    def __buildPredictInputTuple(self, network, exchange, symbol, anchorDate=date.today().isoformat()):
        if gconfig.testing.predictor:
            startt = time.time()
        symbolinfo = self.dbc.getSymbols(exchange, symbol)[0]
        if gconfig.testing.predictor:
            self.testing_getSymbolsTime += time.time() - startt

        data = self.analyzer.dm.stockDataHandlers[(exchange, symbol)].data

        if gconfig.testing.predictor:
            startt = time.time()
        financialData = []
        if (exchange, symbol) in self.analyzer.dm.financialDataHandlers.keys():
            financialData = self.analyzer.dm.financialDataHandlers[(exchange, symbol)].getPrecedingReports(anchorDate, network.stats.precedingRange)
        if gconfig.testing.predictor:
            self.testing_getPrecedingReportsTime += time.time() - startt

        ## check if there is data for the desired anchor date (with some massaging if it was a weekend)
        anchorDate = date.fromisoformat(anchorDate)
        lastdd = date.fromisoformat(data[-1].date)
        ddiff = (anchorDate - lastdd).days
        offset = 0
        if anchorDate == lastdd:
            offset = 1
        elif ddiff < 0:
            offset = -ddiff
        elif ddiff > 1:
            # print('anchor', anchorDate, '\nlastdd', lastdd, ddiff)
            if anchorDate.weekday() in [5,6]:
                if ddiff > 2:
                    # raise Exception('Data is not recent enough for given anchor date', anchorDate.isoformat())
                    raise SufficientlyUpdatedDataNotAvailable(anchorDate.isoformat())
            elif anchorDate.weekday() == 0:
                offset = 3
            else:
                raise AnchorDateAheadOfLastDataDate()
        elif ddiff == 1:
            pass

        if gconfig.testing.predictor:
            startt = time.time()
        inputVector = network.inputVectorFactory.build(
            data[-(network.stats.precedingRange + offset):len(data) - offset], 
            self.vixm.data, financialData, None, symbolinfo.founded, None, symbolinfo.sector, exchange
        )
        if gconfig.testing.predictor:
            self.testing_inputVectorBuildTime += time.time() - startt
        
        return inputVector

    @classmethod
    def predictAll(cls, networkid, anchorDate=None, #date.today().isoformat(), 
        withWeighting=True,
        # exchange=None, exchanges=[], excludeExchanges=[]
        **kwargs
    ):
        self = cls()
        nn, tickers = self._initialize(networkid=networkid, anchorDate=shortc(anchorDate, date.today().isoformat()), needInstanceSetup=withWeighting, **kwargs)
        if len(tickers) == 0:
            print('No tickers available for anchor date of', anchorDate)
            return

        print('Starting predictions for', len(tickers), 'tickers') ## starting on', anchorDate)

        pc = 0
        pc_exceptions = 0
        pcl = []
        predictionInputVectors = []
        predictionTickers = []
        for t in tqdm.tqdm(tickers, desc='Building...'):
            dt = date.fromisoformat(anchorDate) if anchorDate else date.fromisoformat(t.date) + timedelta(days=1)
            try:
                predictionInputVectors.append(self.__buildPredictInputTuple(nn, t.exchange, t.symbol, anchorDate=dt.isoformat()))
                predictionTickers.append(t)
            except (ValueError, tf.errors.InvalidArgumentError, SufficientlyUpdatedDataNotAvailable, KeyError, AnchorDateAheadOfLastDataDate) as e:
            # except IndexError:
                # print(e)

                pc_exceptions += 1

                pass

            if gconfig.testing.enabled and pc > 2:
                break

        print('Predicting...')
        if gconfig.testing.predictor:
            startt = time.time()
        res = nn.predict(
            tf.experimental.numpy.vstack(predictionInputVectors), batchInput=True,
            raw=gconfig.predictor.ifBinaryUseRaw, verbose=1)
        if gconfig.testing.predictor:
            self.testing_predictTime += time.time() - startt
        
        for ti in tqdm.trange(len(predictionTickers), desc='Unpacking...'):
            p = res[ti][0]
            t = predictionTickers[ti]
            if (numpy.round(p) if gconfig.predictor.ifBinaryUseRaw else p) == 1:
                pcl.append((t.exchange, t.symbol, p))

        if gconfig.testing.predictor:
            print('testing_getSymbolsTime', self.testing_getSymbolsTime, 'seconds')
            print('testing_getPrecedingReportsTime', self.testing_getPrecedingReportsTime, 'seconds')
            print('testing_inputVectorBuildTime', self.testing_inputVectorBuildTime, 'seconds')
            print('testing_predictTime', self.testing_predictTime, 'seconds')

        ## weight the prediction accuracy
        weightedAccuracies = {}

        key = AccuracyType.OVERALL
        # if nn.stats.accuracyType == AccuracyType.POSITIVE:
        #     key = AccuracyType.NEGATIVE
        # elif nn.stats.accuracyType == AccuracyType.NEGATIVE:
        #     key = AccuracyType.POSITIVE

        networkFactor = getattr(nn.stats, key.statsName)

        try:
            for s in tqdm.tqdm(pcl, desc='Weighting...'):
                exchange, symbol, prediction = s
                
                if gconfig.testing.predictor:
                    startt = time.time()
                symbolInfo = self.dbc.getSymbols(exchange=exchange, symbol=symbol)[0]
                if gconfig.testing.predictor:
                    self.wt_testing_getSymbolsTime += time.time() - startt

                sectorFactor = 1
                if symbolInfo.sector:
                    pass
                
                
                if gconfig.testing.predictor:
                    startt = time.time()
                try:
                        symbolFactor = self.analyzer.getStockAccuracy(exchange, symbol, nn, key, LossAccuracy.ACCURACY)
                except NoData:
                    symbolFactor = -1
                    if gconfig.testing.predictor:
                        self.wt_testing_getStockAccuracyTime += time.time() - startt

                    weightedAccuracies[s] = (prediction, networkFactor, sectorFactor, symbolFactor)

        except (InternalError, KeyboardInterrupt):
            pass

        if gconfig.testing.predictor:
            print('wt_testing_getSymbolsTime', self.wt_testing_getSymbolsTime, 'seconds')
            print('wt_testing_getStockAccuracyTime', self.wt_testing_getStockAccuracyTime, 'seconds::')
            self.analyzer.printTestTimes()

        weightedAccuracyLambda = lambda v: reduce(operator.mul, list(v), 1) * 100
        for k, v in sorted(weightedAccuracies.items(), key=lambda x: weightedAccuracyLambda(x[1])):
            print(k, ':', weightedAccuracyLambda(v), '%  <-', v)
        print('Factors: predictions, network, sector, symbol')



        print(pc_exceptions, '/', len(tickers), 'had exceptions')
        print(pc, '/', len(tickers) - pc_exceptions, 'predicted to exceed threshold from anchor of', dt.isoformat())

        ## todo, show final date

        return self

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
    Predictor.predictAll('1633809914', '2021-12-11', exchanges=['NYSE', 'NASDAQ']) ## 0.05 - 10d
    # Predictor.predictAll('1631423638', '2021-11-20', exchanges=['NYSE', 'NASDAQ'], numberOfWeightingsLimit=200) ## 0.1 - 30d
    # p.predictAll('1631423638', exchanges=['NYSE', 'NASDAQ']) ## 0.1 - 30d

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
    # print('Weighted', p.analyzer.getStockAccuracy(exchange, symbol, nn, key, LossAccuracy.ACCURACY, timeWeighted=gconfig.predictor.timeWeightedStockAccuracy))
    # print('Unweighted', p.analyzer.getStockAccuracy(exchange, symbol, nn, key, LossAccuracy.ACCURACY, timeWeighted=gconfig.predictor.timeWeightedStockAccuracy))

    print('done')


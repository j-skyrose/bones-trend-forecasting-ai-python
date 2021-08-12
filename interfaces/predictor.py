import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, operator
import tensorflow as tf
from datetime import date, timedelta
from functools import reduce

from utils.other import normalizeStockData
from interfaces.analyzer import Analyzer
from managers.databaseManager import DatabaseManager
from managers.vixManager import VIXManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.dataManager import DataManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from constants.enums import AccuracyType, LossAccuracy, OperatorDict, SeriesType
from constants.exceptions import NoData, SufficientlyUpdatedDataNotAvailable
from globalConfig import config as gconfig

ivf: InputVectorFactory = InputVectorFactory()

class Predictor:
    analyzer: Analyzer = None
    vixm: VIXManager = VIXManager()
    dbc: DatabaseManager = DatabaseManager()
    nnm: NeuralNetworkManager = NeuralNetworkManager()

    def __init__(self):
        pass

    def _getNeuralNetwork(self, networkid) -> NeuralNetworkInstance:
        try:
            nn = self.nnm.get(networkid)
            self.analyzer = Analyzer(nn)
            return nn
        except KeyError:
            print('Network ID not found')


    def predict(self, exchange, symbol, anchorDate=date.today().isoformat(), networkid=None, network=None):
        nn = self._getNeuralNetwork(networkid) if networkid else network
        symbolinfo = self.dbc.getSymbols(exchange, symbol)[0]

        # data = self.dbc.getData(exchange, symbol, nn.stats.seriesType)
        data = self.analyzer.dm.stockDataManager.get(exchange, symbol).data
        
        ## check if there is data for the desired anchor date (with some massaging if it was a weekend)
        anchorDate = date.fromisoformat(anchorDate)
        lastdd = date.fromisoformat(data[-1].date)
        ddiff = (anchorDate - lastdd).days
        offset = 0
        if anchorDate == lastdd:
            offset = 1
        elif ddiff < 0:
            print('Predicting for historical date', anchorDate.isoformat())
            offset = -ddiff
        elif ddiff > 1:
            if anchorDate.weekday() in [5,6]:
                if ddiff > 2:
                    # raise Exception('Data is not recent enough for given anchor date', anchorDate.isoformat())
                    raise SufficientlyUpdatedDataNotAvailable(anchorDate.isoformat())
            elif anchorDate.weekday() == 0:
                offset = 3
            else:
                raise Exception('Anchor date ahead of last data date')
        elif ddiff == 1:
            pass

        # elif anchorDate.weekday() in [5,6] and ddiff > 2:
        #     raise Exception('Data is not recent enough for given anchor date', anchorDate.isoformat())
        
        # elif anchorDate.weekday() not in [5,6] and ddiff > 1:
        #     pass

        ## trim unnecessary data and normalize the rest
        # historicalData = normalizeStockData(data[-(nn.stats.precedingRange + offset):len(data) - offset], nn.stats.highMax, nn.stats.volumeMax)
        # historicalData = data[-(nn.stats.precedingRange + offset):len(data) - offset]
        # vixData = self.dbc.getVIXData()
        # for i in range(len(vixData)):
        #     if vixData[i].date == historicalData[-1].date:
        #         vixData = vixData[i+1-nn.stats.precedingRange:i+1]
        #         break

        # vixData = {r.date: r for r in vixData}
        # inputVector = nn.inputVectorFactory.build(historicalData, self.vixm, None, symbolinfo.founded, None, symbolinfo.sector, exchange)
        inputVector = nn.inputVectorFactory.build(
            data[-(nn.stats.precedingRange + offset):len(data) - offset], 
            self.vixm, None, symbolinfo.founded, None, symbolinfo.sector, exchange
        )

        return nn.predict(inputVector)

    def predictAll(self, networkid, anchorDate=date.today().isoformat(), exchange=None, exchanges=[], excludeExchanges=[]):
        nn = self._getNeuralNetwork(networkid)
        tickers = self.dbc.getLastUpdatedInfo(nn.stats.seriesType, anchorDate, dateModifier=OperatorDict.LESSTHANOREQUAL)
        if len(tickers) == 0:
            print('No tickers available for anchor date of', anchorDate)
            return

        print('Starting predictions for', len(tickers), 'tickers') ## starting on', anchorDate)

        pc = 0
        pcl = []
        for t in tqdm.tqdm(tickers, desc='Predicting...'):
            if exchange and t.exchange != exchange: continue
            elif len(exchanges) > 0 and t.exchange not in exchanges: continue
            elif len(excludeExchanges) > 0 and t.exchange in excludeExchanges: continue

            if gconfig.testing.enabled:
                if (t.exchange, t.symbol) not in self.analyzer.dm.stockDataManager.handlers.keys(): continue

            dt = date.fromisoformat(t.date) + timedelta(days=1)
            try:
                p = self.predict(t.exchange, t.symbol, anchorDate=dt.isoformat(), network=nn)
                if p == 1:
                    pc += 1
                    pcl.append((t.exchange, t.symbol))
            except (ValueError, tf.errors.InvalidArgumentError, SufficientlyUpdatedDataNotAvailable):
                pass

            if gconfig.testing.enabled and pc > 2:
                break

        ## weight the prediction accuracy
        weightedAccuracies = {}

        key = AccuracyType.OVERALL
        if nn.stats.accuracyType == AccuracyType.POSITIVE:
            key = AccuracyType.NEGATIVE
        elif nn.stats.accuracyType == AccuracyType.NEGATIVE:
            key = AccuracyType.POSITIVE

        networkFactor = getattr(nn.stats, key.statsName)

        for s in tqdm.tqdm(pcl, desc='Weighting...'):
            exchange = s[0]
            symbol = s[1]
            symbolInfo = self.dbc.getSymbols(exchange=exchange, symbol=symbol)[0]

            sectorFactor = 1
            if symbolInfo.sector:
                pass
            
            try:
                symbolFactor = self.analyzer.getStockAccuracy(exchange, symbol, nn)[key][LossAccuracy.ACCURACY]
            except NoData:
                symbolFactor = -1

            weightedAccuracies[s] = (networkFactor , sectorFactor , symbolFactor)


        for k, v in weightedAccuracies.items():
            print(k, ':', reduce(operator.mul, list(v), 1) * 100, '%  <-', v)


        # for p in pcl:
        #     print(p)



        print(pc, '/', len(tickers), 'predicted to exceed threshold from anchor of', dt.isoformat())
        ## todo, fix up output


if __name__ == '__main__':
    p: Predictor = Predictor()

    # fl, arg1, *argv = sys.argv
    # if arg1.lower() == 'predict':
    #     c.startAPICollection(argv[0].lower(), SeriesType[argv[1].upper()] if len(argv) > 1 else None)
    # elif arg1.lower() == 'all':
    #     c.collectVIX()


    # print(p.predict('nyse', 'gme', '2021-03-12', networkid='1617767788',))
    p.predictAll('1623156322', '2021-05-30', exchange=gconfig.testing.exchange) ## 0.05
    # p.predictAll('1623009648', '2021-05-30', exchange='NYSE') ## 0.1
    # p.predictAll('1623013426', '2021-05-30', exchange='NYSE') ## 0.15
    # p.predictAll('1623016597', '2021-05-30', exchange='NYSE') ## 0.2
    # p.predictAll('1623018727', '2021-05-30', exchange='NYSE') ## 0.25

    # c.start(SeriesType.DAILY)
    # c.start()
    # c._collectFromAPI('polygon', [recdotdict({'symbol':'KRP'})], None)
    print('done')


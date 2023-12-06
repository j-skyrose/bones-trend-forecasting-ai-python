import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time
from typing import List, Tuple

from globalConfig import config as gconfig
from constants.values import stockOffset
from constants.enums import IndicatorType, SeriesType
from managers._generatedDatabaseAnnotations.databaseRowObjects import SymbolsRow
from structures.normalizationDataHandler import NormalizationDataHandler
from utils.other import normalizeStockData, denormalizeStockData, getIndicatorPeriod
from utils.support import GetMemoryUsage, asISOFormat, asList, getItem, recdotdict, recdotobj, shortc
from utils.technicalIndicatorFormulae import generateADXs_AverageDirectionalIndex, generateATRs_AverageTrueRange, generateBollingerBands, generateCCIs_CommodityChannelIndex, generateDIs_DirectionalIndicator, generateEMAs_ExponentialMovingAverage, generateMACDs_MovingAverageConvergenceDivergence, generateRSIs_RelativeStrengthIndex, generateSuperTrends, generateVolumeBars
from utils.types import TickerKeyType

'''
maintains the time series data from the DB, in normalized and raw forms
also maintains possible selections, and the selected sets as single data points (ie index of the anchor date)
any set builds will need to reference these to get the actual full vectors

data should be in date ascending order, where each item is one row from DB table
'''
class StockDataHandler(GetMemoryUsage):

    def __init__(self, data=None, symbolData: SymbolsRow={}, seriesType: SeriesType=SeriesType.DAILY, normalizationData: NormalizationDataHandler=None, precedingRange=None, followingRange=None, normalize=False, offset=stockOffset,
        maxIndicatorPeriod=0
    ):
        self.symbolData = symbolData
        self.seriesType = seriesType
        
        self.indicators = {}
        self.maxIndicatorPeriod = maxIndicatorPeriod ## preceding days required for first calculation

        self.normalized = False
        self.shouldNormalize = normalize
        self.dataOffset = offset
        self.setData(data, normalizationData, precedingRange, followingRange)

    def getTickerTuple(self) -> Tuple[str,str]:
        return (self.symbolData.exchange, self.symbolData.symbol)

    def getTickerKey(self) -> TickerKeyType:
        return TickerKeyType(*self.getTickerTuple())

    def determineSelections(self, precedingRange=None, followingRange=None):
        precedingRange = shortc(precedingRange, self.precedingRange)
        lowerLimit = precedingRange + 1 + self.maxIndicatorPeriod
        followingRange = shortc(followingRange, self.followingRange)

        self.prunedIndexes = []
        self.selections = [x for x in range(len(self.data)) if lowerLimit <= x and x < len(self.data) - followingRange]
        return self.selections

    def normalize(self):
        if not self.normalized:
            if self.stockPriceNormalizationMax or self.stockVolumeNormalizationMax:
                self.data = normalizeStockData(self.data, self.stockPriceNormalizationMax, self.stockVolumeNormalizationMax, self.dataOffset)
                self.normalized = True
            else:
                raise RuntimeError('Data maxes not available for normalization')
    
    def denormalize(self):
        if self.normalized:
            if self.stockPriceNormalizationMax or self.stockVolumeNormalizationMax:
                self.data = denormalizeStockData(self.data, self.stockPriceNormalizationMax, self.stockVolumeNormalizationMax, self.dataOffset)
                self.normalized = False
            else:
                raise RuntimeError('Data maxes not available for denormalization')

    def setData(self, data, normalizationData: NormalizationDataHandler=None, precedingRange=None, followingRange=None):
        self.data: List = data
        if normalizationData:
            self.stockPriceNormalizationMax = normalizationData.getValue('high', orNone=True)
            self.stockVolumeNormalizationMax = normalizationData.getValue('volume', orNone=True)
        self.precedingRange = precedingRange
        self.followingRange = followingRange

        if self.shouldNormalize:
            self.normalize()
        if self.precedingRange is not None and self.followingRange is not None:
            self.determineSelections(self.precedingRange, self.followingRange)
        else:
            self.prunedIndexes = []
            self.selections = []

    def addPrunedIndex(self, indxArg):
        self.prunedIndexes.extend(asList(indxArg))

    def getAvailableSelections(self):
        return [s for s in self.selections if s not in self.prunedIndexes]

    def getPrecedingSet(self, index):
        return self.data[index-self.precedingRange:index]
    
    def getDay(self, dt):
        dt = asISOFormat(dt)
        return getItem(self.data, lambda x: x.period_date == dt)

    def setIndicatorData(self, indicator: IndicatorType, data):
        self.indicators[indicator] = data

    ## generates technical indicator values for each type, based on the stock data
    def generateTechnicalIndicators(
            self, indicators: List[IndicatorType], indicatorConfig=gconfig.defaultIndicatorFormulaConfig
        ):

        ## make sure to not override any individually set data, only those indicators passed
        for k in indicators:
            self.indicators[k] = []
        # self.indicators = {k: [] for k in keys}
        genTimes = {k: 0 for k in indicators}


        ## calculate for all given indicators
        for i in indicators:
            iperiod = getIndicatorPeriod(i, indicatorConfig)
            startt = time.time()
            if i.isEMA():
                self.indicators[i] = generateEMAs_ExponentialMovingAverage(self.data, iperiod, smoothing=indicatorConfig.modifiers[IndicatorType.EMA].smoothing)
            elif i == IndicatorType.RSI:
                self.indicators[i] = generateRSIs_RelativeStrengthIndex(self.data, iperiod)
            elif i == IndicatorType.CCI:
                self.indicators[i] = generateCCIs_CommodityChannelIndex(self.data, iperiod)
            elif i == IndicatorType.ATR:
                self.indicators[i] = generateATRs_AverageTrueRange(self.data, iperiod)
            elif i == IndicatorType.DIS:
                self.indicators[i] = (
                    generateDIs_DirectionalIndicator(self.data, iperiod),
                    generateDIs_DirectionalIndicator(self.data, iperiod, positive=False)
                )
                ## requires list(zip()) later, as these can be re-used to save calculation time for adx
            elif i == IndicatorType.ADX:
                adxkwargs = {}
                ## if possible, re-use existing calculated DIs
                if self.indicators[IndicatorType.DIS]:
                    if type(self.indicators[IndicatorType.DIS]) == tuple:
                        adxkwargs = {
                            'posDIs': self.indicators[IndicatorType.DIS][0],
                            'negDIs': self.indicators[IndicatorType.DIS][1]
                        }
                    else: ## is list, i.e. cached data used
                        adxkwargs = {
                            'posDIs': [d[0] for d in self.indicators[IndicatorType.DIS]],
                            'negDIs': [d[1] for d in self.indicators[IndicatorType.DIS]]
                        }

                self.indicators[i] = generateADXs_AverageDirectionalIndex(self.data, iperiod, **adxkwargs)
            elif i == IndicatorType.MACD:
                self.indicators[i] = generateMACDs_MovingAverageConvergenceDivergence(self.data)
            elif i == IndicatorType.BB:
                self.indicators[i] = generateBollingerBands(self.data, iperiod, multiplier=indicatorConfig.modifiers[IndicatorType.BB].multiplier)
            elif i == IndicatorType.ST:
                self.indicators[i] = generateSuperTrends(self.data, atrPeriod=iperiod, multiplier=indicatorConfig.modifiers[IndicatorType.ST].multiplier)
            elif i == IndicatorType.RGVB:
                self.indicators[i] = generateVolumeBars(self.data)
                
            genTimes[i] += time.time() - startt
        
        if IndicatorType.DIS in indicators:
            self.indicators[IndicatorType.DIS] = list(zip(*self.indicators[IndicatorType.DIS]))

        ## refresh possible selections as may be reduced due to indicators used
        self.determineSelections(self.precedingRange, self.followingRange)

        return genTimes

    ## reduce indicator dict to only the values corresponding to the days in the preceding set
    def getPrecedingIndicators(self, index):
        retIndcDict = recdotdict({})
        
        ## last index of each indicator list corresponds to last index stock data
        for k in self.indicators.keys():
            offset = len(self.data) - len(self.indicators[k])
            retIndcDict[k] = self.indicators[k][index-self.precedingRange-offset:index-offset]

        return retIndcDict

if __name__ == '__main__':
    sdh: StockDataHandler = StockDataHandler(recdotobj([{'close':x} for x in range(10000)]), precedingRange=5, followingRange=2, maxIndicatorPeriod=20)
    print(sdh._getMemorySize())
    print(sdh.generateTechnicalIndicators([IndicatorType.RSI]))
    print(sdh.getPrecedingIndicators(1))
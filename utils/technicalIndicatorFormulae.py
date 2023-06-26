import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, time, random
from typing import List, Tuple, Union

from globalConfig import config as gconfig
from utils.support import recdotobj, shortc
from constants.enums import CalculationMethod, DataRequiredType, IndicatorType, SuperTrendDirection
from constants.exceptions import InsufficientDataAvailable

## due to how values are calculated based on previous ones, updates to these require full re-calculation
unresumableGenerationIndicators = [IndicatorType.RSI, IndicatorType.DIS, IndicatorType.ADX, IndicatorType.ATR,
                                   ## ATR uses wilder smoothing by default, otherwise this could be resumable
                                   IndicatorType.ST
                                   ]

'''
Typical total/fresh generation TIME SPLITS
indicators_relativeStrengthIndex 0.38
indicators_commodityChannelIndex 0.86
indicators_averageTrueRange 0.67
indicators_directionalIndicators 2.16
indicators_averageDirectionalIndex 2.23
indicators_exponentialMovingAverage200 0.22
indicators_exponentialMovingAverage100 0.22
indicators_exponentialMovingAverage50 0.23
indicators_exponentialMovingAverage26 0.22
indicators_exponentialMovingAverage20 0.23
indicators_exponentialMovingAverage12 0.22
indicators_exponentialMovingAverage10 0.23
indicators_exponentialMovingAverage5 0.23
indicators_movingAverageConvergenceDivergence 0.47
indicators_bollingerBands 2.30
indicators_superTrend 1.32
'''

## for debugging generation of values, puts values in a matrix-like orientation/columns when printed
DEBUGGING = __name__ == '__main__'
class DebugMatrix:
    def __init__(self, headers=[], xdim=0, ydim=0, valuePrintLambda=lambda x: str(x)) -> None:
        self.headers = headers
        self.matrix = []
        if len(self.headers):
            self.matrix = [[''] for i in range(len(self.headers))]
        self.valuePrintLambda = valuePrintLambda

    def set(self, x, y, v):
        newColumnsRequired = x - len(self.matrix)
        newRowsRequired = y - len(self.matrix[0])
        if newColumnsRequired > 0:
            for c in range(newColumnsRequired):
                self.headers.append('')
                self.matrix.append(['' for r in range(len(self.matrix[0]))])
        if newRowsRequired > 0:
            for r in range(newRowsRequired):
                for c in range(len(self.matrix)):
                    self.matrix[c].append('')
        self.matrix[x-1][y-1] = v
        
    ## unload list into specified column
    def setToColumn(self, c, startingRow, vals):
        for indx in range(len(vals)):
            self.set(c, startingRow+indx, vals[indx])

    def getColByKey(self, k):
        for c in range(len(self.headers)):
            if k == self.headers[c]: return c+1

    def print(self, startingRow=1):
        maxColumnLength = max(*[len(c) for c in self.headers])+1
        print(*[str(c).ljust(maxColumnLength) for c in self.headers])

        for r in range(startingRow-1, len(self.matrix[0])):
            print(*[str(self.valuePrintLambda(self.matrix[c][r])).ljust(maxColumnLength) for c in range(len(self.matrix))])

if DEBUGGING:
    debugMatrix = DebugMatrix(
        ['TR','+DM1','-DM1','TR14','+DM14','-DM14','+DI14','-DI14','DX','ADX'],
        valuePrintLambda=lambda x: x if type(x) == str else '{:.2f}'.format(x)
    )

'''
general use/support
'''
def calculateMean(data): return sum(data) / len(data)
def calculateMeanDeviation(data, mean): return sum([abs(d - mean) for d in data]) / len(data)

## wilder smoothing, method one (e.g. ATR, ADX)
def _calculateNext_SmoothMethod1(previousValue, currentData, periods):
    # AKA: return currentData/periods + previousValue*(1-1/periods)
    return (previousValue*(periods-1) + currentData) / periods
## wilder smoothing, method two (e.g. +DM14 part of ADX)
def _calculateNext_SmoothMethod2(previousValue, currentData, periods):
    return previousValue - (previousValue/periods) + currentData
def _smooth(data, periods, func: Union[_calculateNext_SmoothMethod1, _calculateNext_SmoothMethod2], initialValue=None) -> List[float]:
    smoothed = [shortc(initialValue, sum(data[:periods]))]
    for i in range(periods, len(data)):
        smoothed.append(func(smoothed[-1], data[i], periods))
    return smoothed
def smooth_M1(data, periods, initialValue=None) -> List[float]:
    return _smooth(data, periods, _calculateNext_SmoothMethod1, initialValue)
def smooth_M2(data, periods) -> List[float]:
    return _smooth(data, periods, _calculateNext_SmoothMethod2)

## convert list of objects/dicts to a list of values extract from each list item; similar to REDUCE with some abstraction/customizability
def massageToRequiredDataList(data, required=DataRequiredType.ALL, customExtractor=None):
    if required == DataRequiredType.ALL: return data
    if required == DataRequiredType.CUSTOM:
        if not customExtractor: raise LookupError
        extractor = customExtractor
    else:
        extractor = lambda x: x.__getattr__(required.value.lower())

    return [extractor(x) for x in data]

'''
    Relative Strength Index
    type: momentum indicator
    range: [0,100]
        <30: oversold - bullish
        >70: overbought - bearish, overpriced
    formula:
        RSI = 100 - [100 / (1 + AverageGain / AverageLoss)]
    https://www.investopedia.com/terms/r/rsi.asp
'''
def generateRSIs_RelativeStrengthIndex(data, periods=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.RSI]) -> List[float]:
    DEBUG=False
    def _calculateRSI(g, l):
        if l == 0: return 100
        return 100 - (100 / (1 + g/l))

    if len(data) < periods: raise InsufficientDataAvailable

    ## calculate initial RSI
    avgGain = 0
    avgLoss = 0
    for indx,d in enumerate(data[1:periods+1]):
        delta = d.close - data[indx].close
        if delta > 0:
            avgGain += delta
        else:
            avgLoss += abs(delta)
    avgGain /= periods
    avgLoss /= periods
    rsi = [_calculateRSI(avgGain, avgLoss)]
    if DEBUG: 
        print('avgGain',avgGain)
        print('avgLoss',avgLoss)

    ## calculate RSI for the rest
    for indx,d in enumerate(data[periods+1:]):
        delta = d.close - data[indx+periods].close
        if DEBUG: print('delta',delta)
        avgGain = (avgGain*(periods-1) + (delta if delta > 0 else 0))/periods
        avgLoss = (avgLoss*(periods-1) + (0 if delta > 0 else abs(delta)))/periods
        if DEBUG: 
            print('avgGain',avgGain)
            print('avgLoss',avgLoss)
        rsi.append(_calculateRSI(avgGain, avgLoss))

    return rsi

def getRSIExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.RSI]):
    return datalength - periodlength

## test RSI
if __name__ == '__main__':
    data = recdotobj([
        {'close':44.34},
        {'close':44.09},
        {'close':44.15},
        {'close':43.61},
        {'close':44.33},
        {'close':44.83},
        {'close':45.1},
        {'close':45.42},
        {'close':45.84},
        {'close':46.08},
        {'close':45.89},
        {'close':46.03},
        {'close':45.61},
        {'close':46.28},
        {'close':46.28},
        {'close':46},
        {'close':46.03}
    ])
    rsis = generateRSIs_RelativeStrengthIndex(data)
    elrsi = getRSIExpectedLength(len(data))
    print('rsis',rsis)
    if rsis != [70.46413502109705, 66.24961855355505, 66.48094183471265]:
        raise ValueError


'''
    Commodity Channel Index
        less reliable than RSI? may lag
    type: momentum-based oscillator
    range: (-inf, inf)
    formula:
        CCI = (TypicalPrice - SMA) / (0.015 * MeanDeviation)
    https://www.investopedia.com/terms/c/commoditychannelindex.asp
'''
def generateCCIs_CommodityChannelIndex(data, periods=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.CCI]) -> List[float]:
    DEBUG=False
    def _calculateCCI(tp, sma, mdev): 
        if DEBUG: print('tp',tp,sma,mdev)
        if mdev == 0:
            return 0
            raise ZeroDivisionError
        return (tp - sma) / (0.015 * mdev)
    def _calculateTypicalPrice(d): return (d.high + d.low + d.close) / 3

    if len(data) < periods: raise InsufficientDataAvailable

    typicalPrices = [_calculateTypicalPrice(d) for d in data]
    if DEBUG: print('typicalPrices',typicalPrices)
    means = [calculateMean(typicalPrices[i-periods:i]) for i in range(periods, len(data)+1)]
    if DEBUG: print('means',means)
    meanDeviations = [calculateMeanDeviation(typicalPrices[i-periods:i], means[i-periods]) for i in range(periods, len(data)+1)]
    if DEBUG: print('meanDeviations',meanDeviations)

    return [_calculateCCI(typicalPrices[i+periods-1], means[i], meanDeviations[i]) for i in range(len(data)-periods+1)]

def getCCIExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.CCI]):
    return datalength - periodlength + 1

## test CCI
if __name__ == '__main__':
    data = recdotobj([
        {'high':24.2,'low':23.85,'close':23.89},
        {'high':24.07,'low':23.72,'close':23.95},
        {'high':24.04,'low':23.64,'close':23.67},
        {'high':23.87,'low':23.37,'close':23.78},
        {'high':23.67,'low':23.46,'close':23.5},
        {'high':23.59,'low':23.18,'close':23.32},
        {'high':23.8,'low':23.4,'close':23.75},
        {'high':23.8,'low':23.57,'close':23.79},
        {'high':24.3,'low':24.05,'close':24.14},
        {'high':24.15,'low':23.77,'close':23.81},
        {'high':24.05,'low':23.6,'close':23.78},
        {'high':24.06,'low':23.84,'close':23.86},
        {'high':23.88,'low':23.64,'close':23.7},
        {'high':25.14,'low':23.94,'close':24.96},
        {'high':25.20,'low':24.74,'close':24.88},
        {'high':25.07,'low':24.77,'close':24.96},
        {'high':25.22,'low':24.9,'close':25.18},
        {'high':25.37,'low':24.93,'close':25.07},
        {'high':25.36,'low':24.96,'close':25.27},
        {'high':25.26,'low':24.93,'close':25},
        {'high':24.82,'low':24.21,'close':24.46},
        {'high':24.44,'low':24.21,'close':24.28},
    ])
    ccis = generateCCIs_CommodityChannelIndex(data)
    elcci = getCCIExpectedLength(len(data))
    print('ccis',ccis)
    if ccis != [102.19852632840085, 30.770139381053642, 6.498977012877848]:
        raise ValueError



'''
    Average True Range
    type: volatility
    range: [0, inf)
    directional: no
    uses: stock screening, trade timing, position sizing
        value depends on stock price, makes it non-comparable between stocks with large price diff
    https://www.macroption.com/atr-calculation/#exponential-moving-average-ema-method
'''
def calculateTR(d0, d1=None) -> float:
    if d1 is None: return d0.high - d0.low
    return max(d1.high - d1.low, abs(d1.high - d0.close), abs(d1.low - d0.close))
def generateTRs_TrueRanges(data) -> List[float]:
    return [calculateTR(data[0])] + [calculateTR(data[i-1], data[i]) for i in range (1,len(data))]

def generateATRs_AverageTrueRange(data, periods=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ATR], method=CalculationMethod.WILDERSMOOTHING) -> List[float]:
    def _calculateATR(atr0, tr1): 
        if method == CalculationMethod.EMA:
            alphaf = 2 / (periods+1)
            return alphaf*tr1 + (1-alphaf)*atr0
        elif method == CalculationMethod.WILDERSMOOTHING: 
            return _calculateNext_SmoothMethod1(atr0, tr1, periods)

    if len(data) < periods: raise InsufficientDataAvailable

    trueRanges = generateTRs_TrueRanges(data)
    atrs = [calculateMean(trueRanges[:periods])]
    for i in range(1, len(data)-periods+1):
        if method == CalculationMethod.SMA:
            nextATR = calculateMean(trueRanges[i:i+periods])
        else:
            nextATR = _calculateATR(atrs[i-1], trueRanges[i+periods-1])
        atrs.append(nextATR)

    return atrs

def getATRExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ATR]):
    return datalength - periodlength + 1

## test ATR
if __name__ == '__main__':
    data = recdotobj([
        {'high':48.7,'low':47.79,'close':48.16},
        {'high':48.72,'low':48.14,'close':48.61},
        {'high':48.9,'low':48.39,'close':48.75},
        {'high':48.87,'low':48.37,'close':48.63},
        {'high':48.82,'low':48.24,'close':48.74},
        {'high':49.05,'low':48.64,'close':49.03},
        {'high':49.2,'low':48.94,'close':49.07},
        {'high':49.35,'low':48.86,'close':49.32},
        {'high':49.92,'low':49.5,'close':49.91},
        {'high':50.19,'low':49.87,'close':50.13},
        {'high':50.12,'low':49.2,'close':49.53},
        {'high':49.66,'low':48.9,'close':49.5},
        {'high':49.88,'low':49.43,'close':49.75},
        {'high':50.19,'low':49.73,'close':50.03},
        {'high':50.36,'low':49.26,'close':50.31},
        {'high':50.57,'low':50.09,'close':50.52},
        {'high':50.65,'low':50.3,'close':50.41},
    ])
    # atrs = generateATRs_AverageTrueRange(data, method=CalculationMethod.SMA)
    # print('atrs',atrs)
    # atrs = generateATRs_AverageTrueRange(data, method=CalculationMethod.EMA)
    # print('atrs',atrs)
    atrs = generateATRs_AverageTrueRange(data)
    elatr = getATRExpectedLength(len(data))
    print('atrs',atrs)
    if atrs != [0.5542857142857146, 0.5932653061224494, 0.5851749271137028, 0.5683767180341527]:
        raise ValueError


'''
    Directional Movement(s)
        component of +/-DI -> ADX
    range: (-inf, inf)
'''
def generateDMs_DirectionalMovement(data, positive=True) -> List[float]:
    def _calculateDM(d0, d1):
        pdiff = d1.high - d0.high
        ndiff = d0.low - d1.low
        if positive and pdiff > ndiff and pdiff > 0: return pdiff
        if not positive and ndiff > pdiff and ndiff > 0: return ndiff
        return 0

    return [_calculateDM(data[i-1], data[i]) for i in range(1,len(data))]

'''
    Directional Indicator
        +DI: positive directional indicator
        -DI: negative directional indicator
        components of ADX
    type: trend presence
    range: [0,inf)
    formula:
        posnegDirectionIndicator = (smoothedposnegDirectionMovement / smoothedTR) * 100
    https://www.investopedia.com/terms/p/positivedirectionalindicator.asp
'''
def generateDIs_DirectionalIndicator(data, periods=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ADX], positive=True) -> List[float]:
    DEBUG=False
    def _calculateDI(sdm, smtr):
        if smtr == 0: 
            return 0
            raise ZeroDivisionError
        return (sdm/smtr)*100
    def _calculateDM(d0, d1):
        pdiff = d1.high - d0.high
        ndiff = d0.low - d1.low
        if positive and pdiff > ndiff and pdiff > 0: return pdiff
        if not positive and ndiff > pdiff and ndiff > 0: return ndiff
        return 0

    if len(data) < periods: raise InsufficientDataAvailable

    trs = generateTRs_TrueRanges(data)
    smoothedtrs = smooth_M2(trs[1:], periods)
    if DEBUG: print('smoothedtrs',smoothedtrs, len(smoothedtrs))
    if DEBUGGING: debugMatrix.setToColumn(debugMatrix.getColByKey('TR'), 1, trs[1:])
    if DEBUGGING: debugMatrix.setToColumn(debugMatrix.getColByKey('TR14'), 14, smoothedtrs)

    dms = generateDMs_DirectionalMovement(data, positive)
    if DEBUG: print('dms',dms, len(dms))
    smootheddms = smooth_M2(dms, periods)
    if DEBUG: print('smootheddms',smootheddms, len(smootheddms))
    if DEBUGGING: debugMatrix.setToColumn(debugMatrix.getColByKey('{}DM1'.format('+' if positive else '-')), 1, dms)
    if DEBUGGING: debugMatrix.setToColumn(debugMatrix.getColByKey('{}DM14'.format('+' if positive else '-')), periods, smootheddms)


    dis = [_calculateDI(smootheddms[i], smoothedtrs[i]) for i in range(len(data)-periods)]
    if DEBUGGING: debugMatrix.setToColumn(debugMatrix.getColByKey('{}DI14'.format('+' if positive else '-')), periods, dis)

    return dis

def getDIExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ADX]):
    return datalength - periodlength

'''
    Directional Movement Index
        component of ADX
'''
def generateDXs_DirectionalMovementIndex(data=[], periods=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ADX], posDIs=[], negDIs=[]) -> List[float]:
    def _calculateDX(pdi, ndi):
        if pdi + ndi == 0: 
            return 0
            raise ZeroDivisionError
        return abs(pdi - ndi) / abs(pdi + ndi) * 100

    if len(data) < periods and (len(posDIs) < periods or len(negDIs) < periods): raise InsufficientDataAvailable

    pdis = posDIs if posDIs else generateDIs_DirectionalIndicator(data, periods)
    ndis = negDIs if negDIs else generateDIs_DirectionalIndicator(data, periods, positive=False)

    if len(pdis) < len(data)-periods-1: raise ValueError('Insufficient DI data for further calculation, try updating cached technical indicator data')

    dxs = [_calculateDX(pdis[i], ndis[i]) for i in range(len(data)-periods)]
    if DEBUGGING: debugMatrix.setToColumn(debugMatrix.getColByKey('DX'), periods, dxs)

    return dxs

def getDXExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ADX]):
    return datalength - periodlength

'''
    Average Directional Index
    type: trend strength
    range: [0, inf)
        >25: strong (trend)
        <20: weak
    https://www.investopedia.com/terms/a/adx.asp        
'''
def generateADXs_AverageDirectionalIndex(data=[], periods=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ADX], posDIs=[], negDIs=[]) -> List[float]:
    if len(data) < periods*2 and (len(posDIs) < periods*2 or len(negDIs) < periods*2): raise InsufficientDataAvailable

    dxs = generateDXs_DirectionalMovementIndex(data, periods, posDIs, negDIs)
    if len(dxs) < periods: raise IndexError
    adxs = smooth_M1(dxs, periods, initialValue=calculateMean(dxs[:periods]))
    if DEBUGGING: debugMatrix.setToColumn(debugMatrix.getColByKey('ADX'), periods*2-1, adxs)

    return adxs

def getADXExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ADX]):
    return datalength - periodlength*2 + 1

## test ADX
if __name__ == '__main__':
    data = recdotobj([
        {'high':44.53,'low':43.98,'close':44.52},

        {'high':44.93,'low':44.36,'close':44.65},
        {'high':45.39,'low':44.70,'close':45.22},
        {'high':45.70,'low':45.13,'close':45.45},
        {'high':45.63,'low':44.89,'close':45.49},
        {'high':45.52,'low':44.20,'close':44.24},
        {'high':44.71,'low':44.00,'close':44.62},
        {'high':45.15,'low':43.76,'close':45.15},
        {'high':45.65,'low':44.46,'close':44.54},
        {'high':45.87,'low':45.13,'close':45.66},
        {'high':45.99,'low':45.27,'close':45.95},
        {'high':46.35,'low':45.80,'close':46.33},
        {'high':46.61,'low':46.10,'close':46.31},
        {'high':46.47,'low':45.77,'close':45.94},

        {'high':46.30,'low':45.14,'close':45.60},
        {'high':45.98,'low':44.97,'close':45.70},
        {'high':46.68,'low':46.10,'close':46.56},
        {'high':46.59,'low':46.14,'close':46.36},
        {'high':46.88,'low':46.39,'close':46.83},
        {'high':46.81,'low':46.41,'close':46.72},
        {'high':46.74,'low':45.94,'close':46.65},
        {'high':47.08,'low':46.68,'close':46.97},
        {'high':46.84,'low':46.17,'close':46.56},
        {'high':45.81,'low':45.10,'close':45.29},
        {'high':45.13,'low':44.35,'close':44.94},
        {'high':44.96,'low':44.61,'close':44.62},

        {'high':45.01,'low':44.20,'close':44.70},
        {'high':45.67,'low':44.93,'close':45.27},
        {'high':45.71,'low':45.01,'close':45.44},
    ])

    # trs = generateTRs_TrueRanges(data)
    # pdms = generateDMs_DirectionalMovement(data)
    # spdms = smooth(pdms, atrPeriods)
    # ndms = generateDMs_DirectionalMovement(data, positive=False)
    # sndms = smooth(ndms, atrPeriods)
    # pdis = generateDIs_DirectionalIndicator(data)
    # ndis = generateDIs_DirectionalIndicator(data, positive=False)
    # dxs = generateDXs_DirectionalMovementIndex(data)


    # pdis = generateDIs_DirectionalIndicator(data)
    # print('pdis',pdis)
    # ndis = generateDIs_DirectionalIndicator(data, positive=False)
    # print('ndis',ndis)
    # dxs = generateDXs_DirectionalMovementIndex(data)
    # print('dxs',dxs)
    # adxs = generateADXs_AverageDirectionalIndex(data)
    # print('adxs',adxs)

    
    dxs = generateDXs_DirectionalMovementIndex(data)
    eldx = getDXExpectedLength(len(data))
    adxs = generateADXs_AverageDirectionalIndex(data)
    eladx = getADXExpectedLength(len(data))
    debugMatrix.print(startingRow=1)

    # if pdis != [26.488352027610002, 23.911089808879037, 30.356235533224208]:
    #     raise ValueError
    # if ndis != [18.032786885245926, 17.704151938170313, 16.50634692468376]:
    #     raise ValueError    


'''
    Exponential (weighted) Moving Average
        places more weight on more recent data
    type: moving average
    range: [0, inf)
    https://www.investopedia.com/terms/e/ema.asp
'''
def generateEMAs_ExponentialMovingAverage(data, periods=1, smoothing=gconfig.defaultIndicatorFormulaConfig.modifiers[IndicatorType.EMA].smoothing, usingLastEMA=None) -> List[float]:
    if not usingLastEMA and len(data) < periods: raise InsufficientDataAvailable

    data = massageToRequiredDataList(data, DataRequiredType.CLOSE)

    alphaf = smoothing / (periods+1)
    emas = [calculateMean(data[:periods])] if not usingLastEMA else [usingLastEMA]
    for i in range (1, len(data)-periods+1):
        emas.append(alphaf*data[i] + (1-alphaf)*emas[-1])
    if usingLastEMA: emas = emas[1:] ## trim the EMA passed as an arg
    return emas

def getEMAExpectedLength(datalength, periodlength=1):
    return datalength - periodlength + 1

'''
    Moving Average Convergence/Divergence (MACD)
    type: (trend-following) momentum indicator
    range: (-inf, inf)
    formula:
        MACD = EMA12 - EMA26
    https://www.investopedia.com/terms/m/macd.asp
'''
def generateMACDs_MovingAverageConvergenceDivergence(data) -> List[float]:
    if len(data) < 26: raise InsufficientDataAvailable

    ema12 = generateEMAs_ExponentialMovingAverage(data, periods=12)
    ema26 = generateEMAs_ExponentialMovingAverage(data, periods=26)

    macds = [ema12[i] - ema26[i] for i in range(len(data)-26)]
    return macds

def getMACDExpectedLength(datalength):
    return datalength-26

'''
    Volume Weighted Average Price (VWAP)
        suited mainly for intraday
    https://school.stockcharts.com/doku.php?id=technical_indicators:vwap_intraday
'''
def generateVWAPs_VolumeWeightedAveragePrice(data):
    pass

bbmassagetime = 0
bbstdtime = 0
bbmeantime = 0
bbappendtime = 0
'''
    Bollinger Bands
    type: momentum indicator
    range: [0, inf)
        lower, mid, upper bands
    https://school.stockcharts.com/doku.php?id=technical_indicators:bollinger_bands
'''
def generateBollingerBands(data, periods=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.BB], multiplier=gconfig.defaultIndicatorFormulaConfig.modifiers[IndicatorType.BB].multiplier) -> List[Tuple[float,float,float]]:
    if len(data) < periods: raise InsufficientDataAvailable

    global bbmassagetime, bbstdtime, bbmeantime, bbappendtime
    startt = time.time()
    data = massageToRequiredDataList(data, DataRequiredType.CLOSE)
    bbmassagetime += time.time() - startt

    bbs = []
    for i in range(periods, len(data)):
        idata = data[i-periods:i]
        startt = time.time()
        stdd = numpy.std(idata)
        bbstdtime += time.time() - startt

        startt = time.time()
        middleband = calculateMean(idata)
        lowerband = middleband - stdd * multiplier
        upperband = middleband + stdd * multiplier
        bbmeantime += time.time() - startt

        startt = time.time()
        bbs.append((lowerband, middleband, upperband))
        bbappendtime += time.time() - startt
    
    return bbs

def getBolligerBandsExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.BB]):
    return datalength - periodlength

## test bollinger bands
if __name__ == '__main__':
    data = recdotobj([
        {'high':44.53,'low':43.98,'close':44.52},

        {'high':44.93,'low':44.36,'close':44.65},
        {'high':45.39,'low':44.70,'close':45.22},
        {'high':45.70,'low':45.13,'close':45.45},
        {'high':45.63,'low':44.89,'close':45.49},
        {'high':45.52,'low':44.20,'close':44.24},
        {'high':44.71,'low':44.00,'close':44.62},
        {'high':45.15,'low':43.76,'close':45.15},
        {'high':45.65,'low':44.46,'close':44.54},
        {'high':45.87,'low':45.13,'close':45.66},
        {'high':45.99,'low':45.27,'close':45.95},
        {'high':46.35,'low':45.80,'close':46.33},
        {'high':46.61,'low':46.10,'close':46.31},
        {'high':46.47,'low':45.77,'close':45.94},

        {'high':46.30,'low':45.14,'close':45.60},
        {'high':45.98,'low':44.97,'close':45.70},
        {'high':46.68,'low':46.10,'close':46.56},
        {'high':46.59,'low':46.14,'close':46.36},
        {'high':49.88,'low':46.39,'close':49.83},
        {'high':49.81,'low':46.41,'close':49.72},
        {'high':49.74,'low':45.94,'close':49.65},
        {'high':49.08,'low':46.68,'close':49.97},
        {'high':49.84,'low':46.17,'close':49.56},
        {'high':49.81,'low':45.10,'close':49.29},
        {'high':45.13,'low':44.35,'close':44.94},
        {'high':44.96,'low':44.61,'close':44.62},

        {'high':45.01,'low':44.20,'close':44.70},
        {'high':45.67,'low':44.93,'close':45.27},
        {'high':45.71,'low':45.01,'close':45.44},
    ])
    data = recdotobj([{'high':random.randint(1,100),'low':random.randint(1,100),'close':random.randint(1,100)} for i in range(5000)])
    bbs = generateBollingerBands(data, 10)
    # print('bbs', bbs)

    print('bbmassagetime', bbmassagetime)
    print('bbstdtime', bbstdtime)
    print('bbmeantime', bbmeantime)
    print('bbappendtime', bbappendtime)


'''
    Super Trend
    type: trend following indicator
    range: [0, inf)
        ST value, SuperTrendDirection (UP/DOWN) enum
    https://medium.com/codex/step-by-step-implementation-of-the-supertrend-indicator-in-python-656aa678c111
'''
def generateSuperTrends(data, atrPeriod=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ST], multiplier=gconfig.defaultIndicatorFormulaConfig.modifiers[IndicatorType.ST].multiplier) -> List[Tuple[float,SuperTrendDirection]]:
    if len(data) < atrPeriod: raise InsufficientDataAvailable
    atrs = generateATRs_AverageTrueRange(data, atrPeriod)

    sts = []
    for i in range(atrPeriod-1, len(data)):
        d = data[i]
        upperband = ((d.high + d.low)/2) + multiplier * atrs[i-atrPeriod+1]
        lowerband = ((d.high + d.low)/2) - multiplier * atrs[i-atrPeriod+1]

        if i == atrPeriod-1: ## first
            finalUpperBand = upperband
            finalLowerBand = lowerband
            st = finalUpperBand if d.close < finalUpperBand else finalLowerBand
        else:
            finalUpperBand = upperband if upperband < previousFinalUpperBand or data[i-1].close > previousFinalUpperBand else previousFinalUpperBand
            finalLowerBand = lowerband if lowerband > previousFinalLowerBand or data[i-1].close < previousFinalLowerBand else previousFinalLowerBand
        
            st = finalUpperBand if (sts[-1][0] == previousFinalUpperBand and d.close <= finalUpperBand) or (sts[-1][0] == previousFinalLowerBand and d.close <= finalLowerBand) else finalLowerBand

        if d.close > st: dir = SuperTrendDirection.UP
        else: dir = SuperTrendDirection.DOWN
        sts.append((st, dir))

        previousFinalLowerBand = finalLowerBand
        previousFinalUpperBand = finalUpperBand

    return sts

def getSuperTrendExpectedLength(datalength, periodlength=gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ST]):
    return datalength - periodlength + 1

## test supertrend
if __name__ == '__main__':
    data = recdotobj([
        {'high':44.53,'low':43.98,'close':44.52},

        {'high':44.93,'low':44.36,'close':44.65},
        {'high':45.39,'low':44.70,'close':45.22},
        {'high':45.70,'low':45.13,'close':45.45},
        {'high':45.63,'low':44.89,'close':45.49},
        {'high':45.52,'low':44.20,'close':44.24},
        {'high':44.71,'low':44.00,'close':44.62},
        {'high':45.15,'low':43.76,'close':45.15},
        {'high':45.65,'low':44.46,'close':44.54},
        {'high':45.87,'low':45.13,'close':45.66},
        {'high':45.99,'low':45.27,'close':45.95},
        {'high':46.35,'low':45.80,'close':46.33},
        {'high':46.61,'low':46.10,'close':46.31},
        {'high':46.47,'low':45.77,'close':45.94},

        {'high':46.30,'low':45.14,'close':45.60},
        {'high':45.98,'low':44.97,'close':45.70},
        {'high':46.68,'low':46.10,'close':46.56},
        {'high':46.59,'low':46.14,'close':46.36},
        {'high':49.88,'low':46.39,'close':49.83},
        {'high':49.81,'low':46.41,'close':49.72},
        {'high':49.74,'low':45.94,'close':49.65},
        {'high':49.08,'low':46.68,'close':49.97},
        {'high':49.84,'low':46.17,'close':49.56},
        {'high':49.81,'low':45.10,'close':49.29},
        {'high':45.13,'low':44.35,'close':44.94},
        {'high':44.96,'low':44.61,'close':44.62},

        {'high':45.01,'low':44.20,'close':44.70},
        {'high':45.67,'low':44.93,'close':45.27},
        {'high':45.71,'low':45.01,'close':45.44},

        
        {'high':48.7,'low':47.79,'close':48.16},
        {'high':48.72,'low':48.14,'close':48.61},
        {'high':48.9,'low':48.39,'close':48.75},
        {'high':48.87,'low':48.37,'close':48.63},
        {'high':48.82,'low':48.24,'close':48.74},
        {'high':49.05,'low':48.64,'close':49.03},
        {'high':49.2,'low':48.94,'close':49.07},
        {'high':49.35,'low':48.86,'close':49.32},
        {'high':49.92,'low':49.5,'close':49.91},
        {'high':50.19,'low':49.87,'close':50.13},
        {'high':50.12,'low':49.2,'close':49.53},
        {'high':49.66,'low':48.9,'close':49.5},
        {'high':49.88,'low':49.43,'close':49.75},
        {'high':50.19,'low':49.73,'close':50.03},
        {'high':50.36,'low':49.26,'close':50.31},
        {'high':50.57,'low':50.09,'close':50.52},
        {'high':50.65,'low':50.3,'close':50.41},

        {'high':49.91,'low':47.20,'close':48.70},
        {'high':50.01,'low':47.20,'close':49.70},

        
        {'high':49.01,'low':45.20,'close':47.70},
        {'high':45.67,'low':44.93,'close':45.27},
        {'high':45.71,'low':45.01,'close':45.44},
        {'high':46.84,'low':46.17,'close':46.56},
        {'high':45.81,'low':45.10,'close':45.29},
        {'high':46.81,'low':46.41,'close':46.72},
        {'high':46.74,'low':45.94,'close':46.65},
        {'high':47.08,'low':46.68,'close':46.97},
        {'high':45.13,'low':44.35,'close':44.94},
        {'high':45.98,'low':44.97,'close':45.70},
        {'high':46.68,'low':46.10,'close':46.56},
        {'high':46.59,'low':46.14,'close':46.36},
        {'high':46.88,'low':46.39,'close':46.83},
        {'high':44.96,'low':44.61,'close':44.62},

    ])
    # data = recdotobj([
    #     {'open':88.09,'high':90.31,'low':88,'close':90.31},
    #     {'open':92.28,'high':94.33,'low':90.67,'close':93.81},
    #     {'open':94.74,'high':99.7,'low':93.65,'close':98.43},
    #     {'open':99.42,'high':99.76,'low':94.57,'close':96.27},
    #     {'open':96.36,'high':96.99,'low':94.74,'close':95.63},
    # ])    

    sts = generateSuperTrends(data, atrPeriod=2)
    print('sts', sts)

    from matplotlib import pyplot
    # pyplot.plot([d.close for d in data[1:]])
    # pyplot.plot([st[0] for st in sts])
    # pyplot.show()


    ## actual data
    from managers.databaseManager import DatabaseManager
    from constants.enums import SeriesType
    dbm = DatabaseManager()
    data = dbm.getStockData('NYSE ARCA', 'SPY', SeriesType.DAILY)

    atrPeriod = gconfig.defaultIndicatorFormulaConfig.periods[IndicatorType.ST]
    sts = generateSuperTrends(data, atrPeriod)
    
    pyplot.plot([d.close for d in data[atrPeriod-1:]])
    pyplot.plot([st[0] for st in sts])
    pyplot.show()



def getExpectedLengthForIndicator(indicator: IndicatorType, datalength, periodlength=None):
    kwargs = { 'datalength': datalength }
    if periodlength is not None: kwargs['periodlength'] = periodlength

    if indicator.isEMA():
        return getEMAExpectedLength(**kwargs)
    elif indicator == IndicatorType.RSI:
        return getRSIExpectedLength(**kwargs)
    elif indicator == IndicatorType.CCI:
        return getCCIExpectedLength(**kwargs)
    elif indicator == IndicatorType.ATR:
        return getATRExpectedLength(**kwargs)
    elif indicator == IndicatorType.DIS:
        return getDIExpectedLength(**kwargs)
    elif indicator == IndicatorType.ADX:
        return getADXExpectedLength(**kwargs)
    elif indicator == IndicatorType.MACD:
        return getMACDExpectedLength(**kwargs)
    elif indicator == IndicatorType.BB:
        return getBolligerBandsExpectedLength(**kwargs)
    elif indicator == IndicatorType.ST:
        return getSuperTrendExpectedLength(**kwargs)
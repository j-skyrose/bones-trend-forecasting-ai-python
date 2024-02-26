import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import re, optparse
from math import ceil
from typing import Dict, List, Union
from calendar import monthrange
from datetime import date

from globalConfig import config as gconfig
from constants.values import canadaExchanges, usExchanges
from constants.enums import AccuracyType, Api, ChangeType, InterestType, MarketRegion, OutputClass, PrecedingRangeType, IndicatorType, SQLHelpers, SeriesType, SetClassificationType
from utils.support import asList, shortc, shortcdict


def convertListToCSV(lst, excludeColumns=[]):
    header = list(lst[0].keys())
    for c in excludeColumns:
        header.remove(c)

    content = []
    for r in lst:
        line = []
        for k in header:
            try:
                if type(r[k]) == object:
                    print ('error:',r[k])
                    raise KeyError
                line.append(str(r[k]).replace(',',''))
            except KeyError:
                line.append('')
        content.append(','.join(line))
    header = ','.join(header)
    content = '\n'.join(content)
    return header + '\n' + content

def normalizeValue(value, max, offset=0):
    return (value / max) - offset

def denormalizeValue(value, max, offset=0):
    return (value + offset) * max

def normalizeStockData(data, priceMax=None, volumeMax=None, offset=0):
    for r in data:
        if priceMax:
            r.open = normalizeValue(r.open, priceMax, offset)
            r.high = normalizeValue(r.high, priceMax, offset)
            r.low = normalizeValue(r.low, priceMax, offset)
            r.close = normalizeValue(r.close, priceMax, offset)
        if volumeMax: r.volume = normalizeValue(r.volume, volumeMax, offset)
    return data

def denormalizeStockData(data, priceMax, volumeMax=None, offset=0):
    for r in data:
        if priceMax:
            r.open = denormalizeValue(r.open, priceMax, offset)
            r.high = denormalizeValue(r.high, priceMax, offset)
            r.low = denormalizeValue(r.low, priceMax, offset)
            r.close = denormalizeValue(r.close, priceMax, offset)
        if volumeMax: r.volume = denormalizeValue(r.volume, volumeMax, offset)
    return data

def normalizeFinancials(data, generalMax):
    for q in data:
        for v in q.nums:
            q.nums[v] = shortc(q.nums[v], 0) / generalMax
        pass
    return data

def maxQuarters(precedingDays):
    return ceil(precedingDays/90)
   
loggedonce = False

def getInstancesByClass(instances, classification: SetClassificationType=None) -> Union[List, Dict[SetClassificationType, List]]:
    classes = SetClassificationType.excludingAll()
    classBuckets = {c: [] for c in classes}
    classes = shortc(asList(classification), classes)
    for i in instances:
        try:
            for c in classes:
                if i.outputClass == c.outputClass:
                    classBuckets[c].append(i)
                    break
        except:
            print(f'Error while sorting {i}')
    return list(classBuckets.values()) if len(classes) > 1 else classBuckets[classes[0]]

def getOutputClass(data, index, followingRange, changeType, changeValue, normalizationMax=None, normalizationOffset=None):
    try:
        previousDayHigh = data[index - 1].high
        finalDayLow = data[index + followingRange].low
        if changeType == ChangeType.PERCENTAGE:
            change = (finalDayLow / previousDayHigh) - 1
        else:
            change = finalDayLow - previousDayHigh
    except ZeroDivisionError:
        change = 0
    if normalizationMax:
        change = denormalizeValue(change, normalizationMax, normalizationOffset)
    return OutputClass.POSITIVE if change >= changeValue else OutputClass.NEGATIVE

def determinePrecedingRangeType(data):
    open = data[0].open
    close = data[0].close
    high = 0
    low = sys.maxsize
    for d in data:
        if d.high > high:
            high = d.high
        if d.low < low:
            low = d.low

    if open > close:
        if high > open and low < close:
            return PrecedingRangeType.DECREASINGWITHBETTERHIGHANDWORSELOW
        if high > open:
            return PrecedingRangeType.DECREASINGWITHBETTERHIGH
        if low < close:
            return PrecedingRangeType.DECREASINGWITHWORSELOW
        return PrecedingRangeType.DECREASING
    else:
        if high > close and low < open:
            return PrecedingRangeType.INCREASINGWITHBETTERHIGHANDWORSELOW
        if high > close:
            return PrecedingRangeType.INCREASINGWITHBETTERHIGH
        if low < open:
            return PrecedingRangeType.INCREASINGWITHWORSELOW
        return PrecedingRangeType.INCREASING

def buildCommaSeparatedTickerPairString(tupleList: List):
    returnstr = ''
    for d in tupleList:
        returnstr += ',(\'' + d[0] + '\',\'' + d[1] + '\')'
    return returnstr

def getMarketRegion(exchange):
    exchange = asList(exchange)
    if all(e in canadaExchanges for e in exchange): return MarketRegion.CANADA
    elif all(e in usExchanges for e in exchange): return MarketRegion.US    
    else: raise ValueError(f'Exchange(s) {exchange} could not be mapped to any exchange lists')

def getIndicatorPeriod(i: IndicatorType, indicatorConfig=gconfig.defaultIndicatorFormulaConfig):
    if i.isEMA():
        period = i.emaPeriod
    elif i in [IndicatorType.MACD, IndicatorType.RGVB]:
        period = None
    else:
        period = indicatorConfig.periods[i] if i != IndicatorType.DIS else indicatorConfig.periods[IndicatorType.ADX]
        
    return period

## for use in determining whether there is enough (stock) data to cover all the back days required to calculate the widest indicator
def getMaxIndicatorPeriod(indicators: List[IndicatorType], indicatorConfig):
    return max(
        *[-sys.maxsize for x in range(2)], ## ensure there are enough args in-case there are less than 2 indicators
        *[i.emaPeriod for i in indicators if i.isEMA()], 
        *[indicatorConfig.periods[i]*(2 if i == IndicatorType.ADX else 1) for i in indicatorConfig.periods.keys() if i in indicators])


## for use in __main__ of non-interface classes
#   parses and adjusts command line args into proper python formats (e.g. boolean, enum, number)
def parseCommandLineOptions():
    parser = optparse.OptionParser()
    parser.add_option('-a', '--api',
        action='store', dest='api', default=None
    )
    parser.add_option('-t', '--type',
        action='store', dest='type', default=None
    )
    parser.add_option('-f', '--function',
        action='store', dest='function', default=None
    )

    options, args = parser.parse_args()

    def massageVariable(k: str, v: str):
        if v.lower() in ['true', 'false']:
            v = v.lower() == 'true'
        elif k.lower() == 'seriestype':
            v = SeriesType[v.upper()]
        elif k.lower() == 'interesttype':
            v = InterestType[v.upper()]
        elif k.lower() == 'api':
            v = Api[v.upper()]
        elif re.match(r'^[0-9]{2,4}-[0-9]{1,2}-[0-9]{1,2}$', v):
            year, month, day = v.split('-')
            if len(year) == 2: v = '20' + v
            v = date.fromisoformat(v)
        elif re.match(r'[0-9]+.[0-9]+', v):
            v = float(v)
        elif re.match(r'[0-9]+$', v):
            v = int(v)
        return v

    kwargs = {}
    for arg in args:
        key, val = arg.split('=')
        kwargs[key] = massageVariable(key, val)

    return options, kwargs

## add certain kwargs from the given config, for use in getting symbol list for dataManager init
def addAdditionalDefaultKWArgs(kwargs, config):
    kwargs['seriesType'] = shortcdict(kwargs, 'seriesType', SeriesType.DAILY)
    if config.feature.googleInterests.enabled:
        kwargs['googleTopicId'] = shortcdict(kwargs, 'googleTopicId', SQLHelpers.NOTNULL)
    if config.feature.companyAge.enabled and config.feature.companyAge.dataRequired:
        kwargs['founded'] = shortcdict(kwargs, 'founded', SQLHelpers.NOTNULL)
    if config.feature.sector.enabled and config.feature.sector.dataRequired:
        kwargs['sector'] = shortcdict(kwargs, 'sector', SQLHelpers.NOTNULL)
    
    return kwargs

def getCustomAccuracy(statsObj=None, positiveAccuracy=None, negativeAccuracy=None, classValueRatio=gconfig.trainer.customValidationClassValueRatio): 
    positiveAccuracy = shortc(positiveAccuracy, statsObj[AccuracyType.POSITIVE.name].current) 
    negativeAccuracy = shortc(negativeAccuracy, statsObj[AccuracyType.NEGATIVE.name].current)
    return (positiveAccuracy * classValueRatio) + (negativeAccuracy * (1 - classValueRatio))
    

if __name__ == '__main__':
    # ## nyse:mtb-
    # descfulldate = 'The company was founded August 1, 2016 in blah blah'.lower()
    # descyearonly = 'The company was founded in 1930 and is headquartered in Arden Hills, Minnesota.'.lower()
    # descmonthyear = ''.lower()
    # descslashdate = 'miln was created on 05/04/16 by mirae asset. the etf tracks an index composed of us-listed companies that '.lower()
    # companysplitdate = ' headquartered in singapore. maxeon solar technologies, ltd. operates independently of sunpower corporation as of august 26, 2020.'.lower()

    # # desc = descfulldate
    # desc = descyearonly
    # # desc = descmonthyear
    
    # test = "m&t bank corp. is a a bank holding company, which engages in the provision of retail and commercial banking, trust, wealth management and investment services, through its wholly owned subsidiaries, m&t bank and wilmington trust na. it operates through following segments: business banking, commercial banking, commercial real estate, discretionary portfolio, residential mortgage banking and retail banking. the business banking segment provides services to small businesses and professionals through the company's branch network, business banking centers and other delivery channels such as telephone banking, internet banking and automated teller machines. the commercial banking segment offers credit products and banking services for middle-market and large commercial customers. the commercial real estate segment includes credit and deposit services to its customers. the discretionary portfolio segment consists of investment and trading securities, residential mortgage loans and other assets, short-term and long-term borrowed funds, brokered certificates of deposit and interest rate swap agreements related thereto, and cayman islands branch deposits. the residential mortgage banking segment comprises of residential mortgage loans and sells substantially all of those loans in the secondary market to investors. the retail banking segment offers services to consumers through several delivery channels which include branch offices, automated teller machines, telephone banking, and internet banking. the company was founded in november 1969 and is headquartered in buffalo, ny".lower()
    # desc = test

    # # print(extractDateFromDesc(desc))


    # print(shortc('None', 'e'))

    pass

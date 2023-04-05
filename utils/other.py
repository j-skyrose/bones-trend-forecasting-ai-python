import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, re
from math import ceil
from typing import List
from calendar import monthrange
from datetime import date, datetime, timedelta

from globalConfig import config as gconfig
from structures.inputVectorStats import InputVectorStats
from utils.support import recdotdict, shortc, _isoformatd
from constants.values import stockOffset, canadaExchanges, usExchanges
from constants.enums import MarketType, OutputClass, PrecedingRangeType, IndicatorType



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

def normalizeStockData(data, highMax, volumeMax):
    for r in data:
        r.open = (r.open / highMax) - stockOffset
        r.high = (r.high / highMax) - stockOffset
        r.low = (r.low / highMax) - stockOffset
        r.close = (r.close / highMax) - stockOffset
        r.volume = (r.volume / volumeMax) - stockOffset
    return data

def denormalizeStockData(data, highMax, volumeMax):
    for r in data:
        r.open = (r.open +stockOffset)* highMax
        r.high = (r.high +stockOffset)* highMax
        r.low = (r.low +stockOffset)* highMax
        r.close = (r.close +stockOffset)* highMax
        r.volume = (r.volume +stockOffset)* volumeMax
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

def getInstancesByClass(instances):
    pclass = []
    nclass = []
    for i in instances:
        try:
            if i.outputClass == OutputClass.POSITIVE: pclass.append(i)
            else: nclass.append(i)
        except:
            print(i)
    return pclass, nclass

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

def getMarketType(exchange):
    if exchange in canadaExchanges: return MarketType.CANADA
    elif exchange in usExchanges: return MarketType.US    
    else: raise ValueError(f'Exchange {exchange} not found in exchange lists')

def getIndicatorPeriod(i: IndicatorType, indicatorConfig=gconfig.defaultIndicatorFormulaConfig):
    if i.isEMA():
        period = i.emaPeriod
    elif i == IndicatorType.MACD:
        period = None
    else:
        period = indicatorConfig.periods[i] if i != IndicatorType.DIS else indicatorConfig.periods[IndicatorType.ADX]
        
    return period

## for use in determining whether there is enough (stock) data to cover all the back days required to calculate the widest indicator
def getMaxIndicatorPeriod(indicators: List[IndicatorType], indicatorConfig):
    return max(
        *[i.emaPeriod for i in indicators if i.isEMA()], 
        *[indicatorConfig.periods[i]*(2 if i == IndicatorType.ADX else 1) for i in indicatorConfig.periods.keys() if i in indicators])


if __name__ == '__main__':
    # print(getMarketHolidays(2020))
    # print(getInputVectorStats().toString())



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


    print(getInputVectorStats().toString())

    pass


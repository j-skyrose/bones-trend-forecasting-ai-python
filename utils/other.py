from math import ceil
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, re

from calendar import monthrange
from datetime import date, datetime, timedelta
from structures.inputVectorStats import InputVectorStats
from utils.support import recdotdict, shortc, _isoformatd
from constants.values import interestColumn, stockOffset

from globalConfig import config


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

def normalizeFinancials(data, generalMax):
    for r  in data:
        pass
    return data

def maxQuarters(precedingDays):
    return ceil(precedingDays/30)
   
loggedonce = False
def _inputVector_old(dataSet, vixRef, googleInterests, listingDate, sector, getSplitStat=False):
    global loggedonce
    v_dayofweek = []
    v_dayofmonth = []
    v_monthofyear = []
    v_stock_open = []
    v_stock_high = []
    v_stock_low = []
    v_stock_close = []
    v_stock_volume = []
    v_vix_open = []
    v_vix_high = []
    v_vix_low = []
    v_vix_close = []
    v_googleinterest = []

    v_singleinstance = []
    ## single stats
    if config.feature.use.listingAge: v_singleinstance.append()
    if config.feature.use.sector: v_singleinstance.extend(getCategoricalVector(sector, lookupList=dbm.getSectors(), topBuffer=3))

    ## date stats
    for d in dataSet:
        dt = date.fromisoformat(d.date)
        try:
            v = vixRef.data[d.date]
        except:
            print(d.date, d.date in vixRef.data.keys())
            raise KeyError

        # if config.feature.use.dayOfWeek: v_dayofweek.extend(getCategoricalVector(dt.weekday(), 7))
        # if config.feature.use.dayOfMonth: v_dayofmonth.extend(getCategoricalVector(dt.day - 1, 31))
        # if config.feature.use.monthOfYear: v_monthofyear.extend(getCategoricalVector(dt.month - 1, 12))
        if config.feature.use.dayOfWeek: v_dayofweek.append(dt.weekday()/6 - 0.5)
        if config.feature.use.dayOfMonth: v_dayofmonth.append((dt.day - 1)/monthrange(dt.year, dt.month)[1] - 0.5)
        if config.feature.use.monthOfYear: v_monthofyear.append((dt.month - 1)/12 - 0.5)

        if config.feature.use.stock.open: v_stock_open.append(d.open)
        if config.feature.use.stock.high: v_stock_high.append(d.high)
        if config.feature.use.stock.low: v_stock_low.append(d.low)
        if config.feature.use.stock.close: v_stock_close.append(d.close)
        if config.feature.use.stock.volume: v_stock_volume.append(d.volume)
        if config.feature.use.vix.open: v_vix_open.append(v.open)
        if config.feature.use.vix.high: v_vix_high.append(v.high)
        if config.feature.use.vix.low: v_vix_low.append(v.low)
        if config.feature.use.vix.close: v_vix_close.append(v.close)
        if config.feature.use.googleInterests: v_googleinterest.append(googleInterests.at[dt, interestColumn])

    # print(loggedonce)
    if not loggedonce and not getSplitStat:
        loggedonce = True
        globals()['runningtotal'] = 0
        def speclogl(string, list):
            try: t = len(list)*len(list[0]) 
            except TypeError: t = len(list)
            except IndexError: t = 0
            globals()['runningtotal'] += t
            print(string, t, globals()['runningtotal'])

        print('Input vector split:')
        if config.feature.use.dayOfWeek: speclogl('v_dayofweek', v_dayofweek)
        if config.feature.use.dayOfMonth: speclogl('v_dayofmonth', v_dayofmonth)
        if config.feature.use.monthOfYear: speclogl('v_monthofyear', v_monthofyear)
        if config.feature.use.stock.open: speclogl('v_stock_open', v_stock_open)
        if config.feature.use.stock.high: speclogl('v_stock_high', v_stock_high)
        if config.feature.use.stock.low: speclogl('v_stock_low', v_stock_low)
        if config.feature.use.stock.close: speclogl('v_stock_close', v_stock_close)
        if config.feature.use.stock.volume: speclogl('v_stock_volume', v_stock_volume)
        if config.feature.use.vix.open: speclogl('v_vix_open', v_vix_open)
        if config.feature.use.vix.high: speclogl('v_vix_high', v_vix_high)
        if config.feature.use.vix.low: speclogl('v_vix_low', v_vix_low)
        if config.feature.use.vix.close: speclogl('v_vix_close', v_vix_close)
        if config.feature.use.googleInterests: speclogl('v_googleinterest', v_googleinterest)

    if getSplitStat:
        ivs = InputVectorStats()
        if config.feature.use.dayOfWeek: ivs.addStatFromList('v_dayofweek', v_dayofweek)
        if config.feature.use.dayOfMonth: ivs.addStatFromList('v_dayofmonth', v_dayofmonth)
        if config.feature.use.monthOfYear: ivs.addStatFromList('v_monthofyear', v_monthofyear)
        if config.feature.use.stock.open: ivs.addStatFromList('v_stock_open', v_stock_open)
        if config.feature.use.stock.high: ivs.addStatFromList('v_stock_high', v_stock_high)
        if config.feature.use.stock.low: ivs.addStatFromList('v_stock_low', v_stock_low)
        if config.feature.use.stock.close: ivs.addStatFromList('v_stock_close', v_stock_close)
        if config.feature.use.stock.volume: ivs.addStatFromList('v_stock_volume', v_stock_volume)
        if config.feature.use.vix.open: ivs.addStatFromList('v_vix_open', v_vix_open)
        if config.feature.use.vix.high: ivs.addStatFromList('v_vix_high', v_vix_high)
        if config.feature.use.vix.low: ivs.addStatFromList('v_vix_low', v_vix_low)
        if config.feature.use.vix.close: ivs.addStatFromList('v_vix_close', v_vix_close)
        if config.feature.use.googleInterests: ivs.addStatFromList('v_googleinterest', v_googleinterest)

        return ivs
    else:
        retarr = []
        if config.feature.use.dayOfWeek: retarr += v_dayofweek
        if config.feature.use.dayOfMonth: retarr += v_dayofmonth
        if config.feature.use.monthOfYear: retarr += v_monthofyear
        if config.feature.use.stock.open: retarr += v_stock_open
        if config.feature.use.stock.high: retarr += v_stock_high
        if config.feature.use.stock.low: retarr += v_stock_low
        if config.feature.use.stock.close: retarr += v_stock_close
        if config.feature.use.stock.volume: retarr += v_stock_volume
        if config.feature.use.vix.open: retarr += v_vix_open
        if config.feature.use.vix.high: retarr += v_vix_high
        if config.feature.use.vix.low: retarr += v_vix_low
        if config.feature.use.vix.close: retarr += v_vix_close
        if config.feature.use.googleInterests: retarr += v_googleinterest
        return numpy.array(
            retarr
            # v_dayofweek + v_dayofmonth + v_monthofyear +
            # v_stock_open + v_stock_high + v_stock_low + v_stock_close + v_stock_volume +
            # v_vix_open + v_vix_high + v_vix_low + v_vix_close +
            # v_googleinterest
        )




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


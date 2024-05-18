import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy
from calendar import monthrange
from datetime import date, timedelta

from managers.configManager import SavedStateManager
from managers.databaseManager import DatabaseManager
from structures.dailyDataHandler import DailyDataHandler
from structures.monthlyGIDataHandler import MonthlyGIDataHandler
from utils.support import asMonthKey, isSameMonth, recdotdict, tqdmLoopHandleWrapper
from constants.enums import InterestType, SQLHelpers, SeriesType

dbm: DatabaseManager = DatabaseManager()


def processRawGoogleInterests(exchange=None, symbol=None, verbose=1):
    '''pulls daily/weekly/monthly data from google_interests_d then calculates and inserts overall relative interest for each day that has stock data into google_interests_c table. Essentially rebuilds all data in google_interests_c table every execution as backfactor modification may be performed'''
    
    config = SavedStateManager()
    if config.get('google', 'lastprocessedrowid') == dbm.getMaxRowID():
        print('Already up-to-date')
        return
    
    if exchange and symbol:
        symbolList = [recdotdict({'exchange': exchange, 'symbol': symbol})]
    else:
        symbolList = dbm.getSymbols(exchange=exchange, topicId=SQLHelpers.NOTNULL)

    ddh: DailyDataHandler
    for s in tqdmLoopHandleWrapper(symbolList, verbose, desc='Processing symbols'):
        if verbose>=2: print(s.exchange, s.symbol)

        ## get daily
        dailydata = dbm.getGoogleInterests(s.exchange, s.symbol, itype=InterestType.DAILY, raw=True)
        if len(dailydata) == 0: continue
        ddh = DailyDataHandler(dailydata, dbm.getStockDataDaily(s.exchange, s.symbol))

        ## overall/monthly
        mdh = MonthlyGIDataHandler(dbm.getGoogleInterests(s.exchange, s.symbol, itype=InterestType.MONTHLY, raw=True), ddh)

        ## verify daily data has a match in monthly data set
        missingMonths = set()
        for m in ddh.getMonths():
            if not mdh.hasMonthKey(m):
                missingMonths.add(asMonthKey(m))
        missingMonths = sorted(list(missingMonths))

        ## if any months missing, need to calculate an average that can be used to project what the month value may be
        ## this projection is very rough, error is at least -50%
        if len(missingMonths) > 0:
            monthsums = {}
            runningvalues = []
            dategivaluetuples = sorted(ddh.getConsolidatedDict().items())

            ## ensure only full months are calculated first, as their sums will be needed to project missing daily values to possible incomplete months (should be first and last only)
            startindex = 0
            while date.fromisoformat(dategivaluetuples[startindex][0]).day != 1:
                startindex += 1
            endindex = len(dategivaluetuples)-1
            while (date.fromisoformat(dategivaluetuples[endindex][0]) + timedelta(days=1)).day != 1:
                endindex -= 1

            for tuplelist in [dategivaluetuples[startindex:endindex+1], dategivaluetuples[:startindex] + dategivaluetuples[endindex+1:]]: ## full months first, then potential partials ones
                curmonth = None
                for indx,(k,v) in enumerate(tuplelist):
                    if curmonth is None: curmonth = k
                    elif not isSameMonth(curmonth, k) or indx == len(tuplelist)-1:
                        if indx == len(tuplelist)-1: ## end of dailydata
                            runningvalues.append(v)

                        ## check if month is incomplete, approximate missing days (should only happen for latest month)
                        ddate = date.fromisoformat(curmonth)
                        expecteddays = monthrange(ddate.year, ddate.month)[1]
                        if len(runningvalues) != expecteddays:
                            missingdaycount = expecteddays - len(runningvalues)
                            avgval = (numpy.average(list(monthsums.values())) - sum(runningvalues)) / missingdaycount
                            ## removing average from each real value first seems to reduce the projected sum to a more realistic value
                            for rvindx in range(len(runningvalues)):
                                runningvalues[rvindx] -= avgval
                            for x in range(missingdaycount):
                                runningvalues.append(avgval)

                        ## rollover to next month
                        monthsums[asMonthKey(curmonth)] = sum(runningvalues)
                        curmonth = k
                        runningvalues = []
                    
                    runningvalues.append(v)

            
            ## fillout missing months
            m: date
            mk: date
            maxval = 0
            daydifflimit = 190 ## ~6 months
            # daydifflimit = 95 ## ~3 months
            for m in missingMonths:
                avgfactor = numpy.average([ mdh.getMonthValue(mk) / monthsums[mk] for mk in ddh.getMonths() if mk in mdh.data.keys() and monthsums[mk] > 0 and (m - mk).days < daydifflimit ])
                val = avgfactor * monthsums[m]
                if val > maxval: maxval = val
                mdh.setMonthValue(m, val)
            
            ## shift values if any of the projected month values are over the limit of 100
            if maxval > 100:
                backfactor = 100 / maxval
                for mk in mdh.data.keys():
                    mdh.setMonthValue(mk, mdh.getMonthValue(mk) * backfactor)

        ## calculate relative interest for each day based on daily, and monthly numbers
        for k,v in ddh.getConsolidatedDict().items():
            relativev = v * mdh.getMonthValue(k) / 100
            # for m in missingMonths:
            #     print(m, monthsums[m], mdh.getMonthValue(m))
            ## upsert
            dbm.insertCalculatedGoogleInterest(s.exchange, s.symbol, k, relativev)
            ## v, weeklyData, overallData: {1-100}
    
    if not exchange or symbol:
        ## save row count as snapshot for when data was processed and up to date
        maxrowid = dbm.getMaxRowID()
        config.set('google', 'lastprocessedrowid', maxrowid)
        print(f'Finished processing {maxrowid} raw data points')
        config.save()

    dbm.commit()

if __name__ == '__main__':
    # print(dbm.dbc.execute('SELECT MAX(rowid) FROM google_interests_d')[0]['MAX(rowid)'])
    # processRawGoogleInterests('NASDAQ','VTSI')
    processRawGoogleInterests()

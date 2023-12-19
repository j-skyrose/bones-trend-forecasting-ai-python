import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, traceback, math, requests, csv, codecs, copy, sqlite3
import time as timer
from random import random
from datetime import date, datetime, timedelta
from threading import Thread
from contextlib import closing
from types import NoneType
from typing import List

from managers.databaseManager import DatabaseManager
from managers.apiManager import APIManager
from managers.marketDayManager import MarketDayManager
from structures.api.google import Google
from structures.api.nasdaq import Nasdaq

from constants.exceptions import APILimitReached, APIError, APITimeout
from utils.other import parseCommandLineOptions
from utils.support import asDate, asDatetime, getIndex, recdotdict, shortcdict, tqdmLoopHandleWrapper
from constants.enums import APIState, EarningsCollectionAPI, FinancialReportType, FinancialStatementType, InterestType, OperatorDict, SQLHelpers, SeriesType, Direction, TimespanType
from constants.values import tseNoCommissionSymbols, minGoogleDate

dbm: DatabaseManager = DatabaseManager()

DEBUG = True

class Collector:
    def __init__(self, currentDate=date.today()):
        currentDatetime = asDatetime(currentDate)
        currentDate = asDate(currentDate)
        self.currentDatetime = currentDatetime
        self.currentDate = currentDate

        self.apiManager: APIManager = APIManager(self.currentDate)
        self.apiErrors = []

    def __updateSymbolsAPIField(self, api, exchange, symbol, val):
        dbm.dbc.execute('UPDATE symbols SET api_'+api+'=? WHERE exchange=? AND symbol=?',(val, exchange, symbol))

    def _loopCollectBySymbol(self, api, symbols, seriesType):
        updatedCount = 0
        apiErrorErrors = []
        try:
            for sp in symbols:
                try:
                    dbm.insertData(
                        sp.exchange, sp.symbol, seriesType, api, 
                        self.apiManager.query(api, sp.symbol, seriesType, exchange=sp.exchange)
                    )
                    self.__updateSymbolsAPIField(api, sp.exchange, sp.symbol, 1)
                    dbm.commit()
                    updatedCount += 1
                except APIError:
                    print('api error',sys.exc_info()[0])
                    print(traceback.format_exc())
                    self.apiErrors.append((sp.exchange, sp.symbol))
                    try:
                        self.__updateSymbolsAPIField(api, sp.exchange, sp.symbol, -1)
                    except:
                        apiErrorErrors.append((sp.exchange, sp.symbol))
                        print('API update error', sp.exchange, sp.symbol)

        except APILimitReached:
            print('api limit reached for',api)
            pass

        print('Updated', api, 'data for', updatedCount, 'symbols')
        print('Got', len(self.apiErrors), 'API errors')
        print(len(apiErrorErrors), '/', len(self.apiErrors), 'had errors while trying to update API field:', apiErrorErrors)

    def _loopCollectByDate(self, api, dryrun=False):
        batchByDate = {}
        startingPastDaysCount = self.apiManager.apis[api].priority * 365

        ## API cannot (403 error) retrieve same-day data, even if after market close, so need to adjust back for retrieval and DB last_updates
        backAdjustedCurrentDate = self.currentDate - timedelta(days=1)
        lastUpdatedPastDaysCount = math.floor( (backAdjustedCurrentDate - self.apiManager.apis[api].updatedOn).total_seconds() / (60 * 60 * 24) )
        if DEBUG: print('max days', startingPastDaysCount, 'last updated delta', lastUpdatedPastDaysCount)

        for c in range(min(startingPastDaysCount, lastUpdatedPastDaysCount)-1, -1, -1):
            try:
                d = (backAdjustedCurrentDate - timedelta(days=c)).isoformat()
                if not dryrun:
                    res = self.apiManager.query(api, qdate=d, verbose=1)
                    if len(res) > 0:
                        batchByDate[d] = res
                else: print(f'querying {api} for {d}')
            except APIError:
                print('api error',sys.exc_info()[0])
                print(traceback.format_exc())
                break
        if DEBUG: print('querying done, preparing data for db insertion')

        ## convert grouping by date to grouping by symbol
        batchBySymbol = {}
        for dt in tqdm.tqdm(batchByDate, desc='Converting date to symbol grouping'):
            for s in batchByDate[dt]:
                key = s['symbol'].replace('p','-')
                try:
                    batchBySymbol[key][dt] = s
                except KeyError:
                    batchBySymbol[key] = { dt: s }

        ## commit data only if symbols are in the given bucket
        counter = 0
        for s in tqdm.tqdm(batchBySymbol, desc='Inserting data'):
            exchangeQuery = dbm.getSymbols(symbol=s, api=api)
            if len(exchangeQuery) != 1:
                self.apiErrors.append(('-',s))
                continue

            dbm.insertData(exchangeQuery[0].exchange, s, SeriesType.DAILY, api, batchBySymbol[s], currentDate=backAdjustedCurrentDate)
            dbm.commit()
            counter += 1
        if dryrun: print(f'last updated set to {backAdjustedCurrentDate}')

        print('Updated', api, 'data for', counter, 'symbols')

    ## polygon only right now
    ## pre market is 4am-open, after market is close-8pm
    def __mixedSymbolDateTimespanCollect(self, api, symbols, timespan=TimespanType.MINUTE):
        ## polygon limit is 50000, each day is ~960 (~500 - max 1440)
        chunkSize = 34

        print('collecting for {c} symbols'.format(c=len(symbols)))
        for t in symbols:
            if t.timestamp:
                print(t)
                print('passing')
                pass
            ## no data, need to collect from current day back as far as there is data
            else:
                try:
                    ## use batch in case of any interupts
                    dbm.startBatch()
                    toDate = copy.deepcopy(self.currentDatetime)

                    anyData = False
                    multipler = 1
                    while True:
                        while True:
                            # print('multipler', multipler, int(chunkSize*multipler))
                            try: fromDate = toDate - timedelta(days=int(chunkSize*multipler))
                            except OverflowError: fromDate = datetime.min + timedelta(days=1)
                            try: 
                                data = self.apiManager.getAggregates(api, t.symbol, fromDate=fromDate.date().isoformat(), toDate=toDate.date().isoformat(), verbose=1)
                                ## aim for ~40k results
                                if len(data) > 0: multipler *= 40000 / len(data)
                                break
                            except OverflowError:
                                multipler /= 2
                        
                        if len(data) == 0: break
                        anyData = True

                        dbm.insertMinuteBatchData(t.exchange, t.symbol, data)

                        toDate = fromDate

                    if not anyData: dbm.insertMinuteBatchData(t.exchange, t.symbol, [recdotdict({
                        'unixTimePeriod': 2147385600,
                        'open': 0,
                        'high': 0,
                        'low': 0,
                        'close': 0,
                        'volumeWeightedAverage': 0,
                        'volume': 0,
                        'transactions': 0,
                        'artificial': True
                    })])
                    dbm.commitBatch()
                except Exception as e:
                    print(e)
                    dbm.rollbackBatch()
                    raise e
            # break # do one at a time

    def startAPICollection(self, api, seriesType: SeriesType=SeriesType.DAILY, dryrun=False, **kwargs):
        typeAPIs = ['alphavantage'] #self.apiManager.getAPIList(sort=True)
        nonTypeAPIs = ['polygon']

        try:
            if api in ['polygon']:
                if seriesType == SeriesType.MINUTE:
                    tickerlist = dbm.getLatestMinuteDataRows(api)

                    debugc = 0
                    for t in tickerlist[:]:
                        debugc += 1
                        # if debugc < 20: print(t, t.timestamp.date() if t.timestamp else None, datetime.now().date(), t.timestamp.date() >= datetime.now().date() if t.timestamp else False)
                        ## purge any up-to-date tickers or ones that would return partial data
                        if t.timestamp and ((t.timestamp.date() == MarketDayManager.getPreviousMarketDay(self.currentDate) or t.timestamp.date() == MarketDayManager.getLastMarketDay(self.currentDate) or t.timestamp.date() > self.currentDate) and self.currentDatetime.hour <= 19):
                            # print('removing {e}-{s}'.format(e=t.exchange, s=t.symbol))
                            tickerlist.remove(t)

                    self.__mixedSymbolDateTimespanCollect(api, tickerlist)
                else:
                    self._loopCollectByDate(api, dryrun=dryrun)
                
            else:
                ## gather symbols for this collection run
                lastUpdatedList = dbm.getLastUpdatedCollectorInfo(seriesType=seriesType, api=api, googleTopicID=Direction.DESCENDING).fetchall()
                if DEBUG: print('lastUpdatedList length',len(lastUpdatedList))

                if api == 'alphavantage':
                    symbols = []
                    for r in lastUpdatedList:
                        # ## cull all rows that have been updated today by the currently checked API (higher priority already culled in previous iteration)
                        # if r.api == api and date.fromisoformat(r.date) == date.today():
                        #     continue
                        # above is obsolete while all alphavantage stocks have been collected at least once for the given series type within the past 2 years
                        # polygon can handle all these stocks now, unless they are not available from the api, in which case only alphavantage can retrieve updated info
                        if date.fromisoformat(r.date) >= self.currentDate:
                            continue

                        ## only include if symbol is supported by API
                        try:
                            if r['api_'+api] == 1:
                                symbols.append(r)
                        except KeyError:
                            print('key error checking if symbol is supported by api', api)
                            raise APIError
                        # if len(symbols) == self.apiManager.apis[api]['remaining']: break

                    print('symbol list size', len(symbols))
                    self._loopCollectBySymbol(api, symbols, seriesType)

                elif api == 'neo':
                    for r in lastUpdatedList:
                        ## skip if updated today
                        if date.fromisoformat(r.date) >= self.currentDate:
                            continue
                        ## skip if symbol not supported by API
                        try: 
                            if r['api_'+api] != 1: continue
                        except KeyError: continue

                        self.__loopCollectDateRangebySymbol(api, r.symbol, date.fromisoformat(r.date))

        except (KeyboardInterrupt, APIError):
            print('keyboard interrupt')

        print('API Errors:',self.apiErrors)

    def __loopCollectDateRangebySymbol(self, api, symbol, sdate: date):
        if api == 'neo':
            chunkSize = 90
            results = []
            while sdate < self.currentDate:
                try:
                    results.append(self.apiManager.query(api, symbol, fromDate=sdate, toDate=sdate + timedelta(days=chunkSize), verbose=0.5))
                except APIError:
                    pass
                sdate += timedelta(days=chunkSize)

            ## merge all results into single dictionary
            resDict = {}
            for r in results:
                resDict = {**resDict, **r}

            dbm.insertData('NEO', symbol, SeriesType.DAILY, api, resDict, currentDate=currentDate)            

    def startAPICollection_exploratoryAlphavantageAPIUpdates(self, **kwargs):
        api = 'alphavantage'
        seriesType=SeriesType.DAILY
        tsePrioritySymbols = tseNoCommissionSymbols
    
        try:
            ## gather symbols for this collection run
            lastUpdatedList: List = dbm.getLastUpdatedCollectorInfo(seriesType=seriesType, api=api, apiSortDirection=Direction.ASCENDING, apiFilter=[APIState.UNKNOWN, APIState.WORKING], exchange=['TSX']).fetchall()
            if DEBUG: print('lastUpdatedList length',len(lastUpdatedList))

            priorityRows = []
            for idx, r in enumerate(lastUpdatedList):
                if r.exchange == 'TSX' and r.symbol in tsePrioritySymbols:
                    priorityRows.append(lastUpdatedList.pop(idx))
            apiRows = []
            for idx, r in enumerate(lastUpdatedList):
                if r.api_alphavantage == 0:
                    apiRows.append(lastUpdatedList.pop(idx))
            lastUpdatedList = priorityRows + apiRows + lastUpdatedList

            ## filter out any symbols already updated today
            symbols = []
            for r in lastUpdatedList:
                if date.fromisoformat(r.date) == date.today():
                    continue

                symbols.append(r)
                if len(symbols) == self.apiManager.apis[api]['remaining']: break
                # if len(symbols) > 500: break

            print('symbol list size', len(symbols))
            self._loopCollectBySymbol(api, symbols, seriesType)

        except (KeyboardInterrupt, APIError):
            print('keyboard interrupt')

        print('API Errors:',self.apiErrors)

    def collectVIX(self, **kwargs):
        # url = "https://ww2.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv"
        url = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"

        with closing(requests.get(url, stream=True)) as r:
            reader = csv.reader(codecs.iterdecode(r.iter_lines(), 'utf-8'), delimiter=',', quotechar='"')
            skipc = 0
            print('got vix data, inserting...', end='')
            for row in reader:
                if skipc < 2:
                    skipc += 1
                    continue
                dbm.insertVIXRow(row)
                # print('inserted', row)
            print('done')

        ## if on weekend or after close on Friday, the excel will not contain that Friday's data so it must be retrieved specifically
        if date.today().weekday() > 4 or (date.today() == 4 and timer.localtime()[3] >= 18):
            url = 'https://www.cboe.com/indices/data/?symbol=VIX&timeline=1M'
            
            resp = requests.get(url)
            if resp.ok:
                rjson = resp.json()
                friday = MarketDayManager.getLastMarketDay()
                topen = None
                tclose = None
                thigh = 0
                tlow = sys.maxsize
                for d in rjson['data']:
                    dt, open, high, low, close = d
                    if friday.isoformat() == dt[:10]:
                        if not topen: topen = open
                        if high > thigh: thigh = high
                        if low < tlow : tlow = low
                        tclose = close

                print(topen, thigh, tlow, tclose)

                dbm.insertVIXRow(point=(friday.isoformat(), topen, thigh, tlow, tclose, True))
                print('inserted Friday data')

            else:
                print('Unable to get Friday data')

    def collectAPIDump_symbolInfo(self, api, **kwargs):
        substmt = f'SELECT * FROM {dbm.getTableString("symbol_info_polygon_d")} dsi WHERE dsi.exchange = ssi.exchange AND dsi.symbol = ssi.symbol AND ' + api + ' IS NOT NULL'
        # stmt = 'SELECT exchange, symbol FROM symbols WHERE NOT EXISTS (' + substmt + ') AND api_' + api + ' = 1'

        ## still pulling NYSE:AAC even though row is present in dump table

        stmt = f'SELECT ssi.exchange, ssi.symbol FROM {dbm.getTableString("staging_symbol_info_d")} ssi JOIN symbols ON ssi.exchange = symbols.exchange AND ssi.symbol = symbols.symbol WHERE NOT EXISTS (' + substmt + ') AND polygon_sector NOT IN (\'e\',\'x\') AND api_' + api + ' = 1'
        tickers = dbm.dbc.execute(stmt).fetchall()

        # print(tickers[0].exchange, tickers[0].symbol)
        # return

        print(tickers)
        # return

        for t in tickers:
            try:
                details = self.apiManager.getTickerDetails(api, t.symbol)
                dbm.insertDump_symbolInfo(details, api)
            except APIError:
                if api == 'fmp' or api == 'alphavantage':
                    dbm.updateSymbolTempInfo(recdotdict({ 'sector': 'x' }), api, symbol=s.symbol)
                pass
            except APILimitReached:
                print(api+' limited reached')
                break

    def __collectAPITickerDetails(self, api, postprocessing=None):
        symbolRows = dbm.getSymbolsTempInfo(api)
        c=0
        for s in symbolRows:
            # c+=1
            # if c > 3: break
            try:
                details = self.apiManager.getTickerDetails(api, s.symbol)
                details = postprocessing(details) if postprocessing else details

                dbm.updateSymbolTempInfo(details, api, symbol=s.symbol)
            except APIError:
                if api == 'fmp' or api == 'alphavantage':
                    dbm.updateSymbolTempInfo(recdotdict({ 'sector': 'x' }), api, symbol=s.symbol)
                pass
            except APILimitReached:
                print(api+' limited reached')
                break

    def collectPolygonTickerDetails(self, **kwargs):
        def postprocessing(details):
            details['ipoDate'] = details.pop('listdate')
            return details
        return self.__collectAPITickerDetails('polygon', postprocessing)
        
    def collectFMPTickerDetails(self, **kwargs):
        return self.__collectAPITickerDetails('fmp')

    def collectAlphavantageTickerDetails(self, **kwargs):
        def postprocessing(details: dict):
            details['sector'] = details.pop('Sector')
            details['industry'] = details.pop('Industry')
            details['assetType'] = details.pop('AssetType')
            details['description'] = details.pop('Description')
            return details
        return self.__collectAPITickerDetails('alphavantage', postprocessing)          


    def collectPolygonFinancials(self, ftype: FinancialReportType, **kwargs):
        api = 'polygon'
        tickers = dbm.getSymbols_forFinancialStaging(api, ftype)
        print('collecting for',len(tickers),'tickers')
        for t in tickers:
            res = self.apiManager.getFinanicals(api, t.symbol, ftype)
            if len(res.results) == 0:
                dbm.insertFinancials_staging_empty(api, t.exchange, t.symbol, ftype)
            else:
                dbm.insertFinancials_staging(api, t.exchange, res.results)
            # break

    ## financials seem to be premium APIs
    def collectFMPFinancials(self, ftype: FinancialReportType, stype: FinancialStatementType, **kwargs):
        api = 'fmp'
        tickers = dbm.getSymbols_forFinancialStaging(api)

        return
        ## needs mod for specific periods
        for t in tickers:
            res = self.apiManager.getFinanicals(api, t.symbol, ftype, stype)
            if len(res.results) == 0:
                dbm.insertFinancials_staging_empty(api, t.exchange, t.symbol, ftype)
            else:
                dbm.insertFinancials_staging(api, t.exchange, res)
            break

    ## annual and quarterly come in same response
    def collectAlphavantageFinancials(self, stype: FinancialStatementType, **kwargs):
        api = 'alphavantage'
        tickers = dbm.getSymbols_forFinancialStaging(api)
        # tickers = [recdotdict({'exchange': 'NASDAQ', 'symbol': 'AAL'})]
        for t in tickers:
            try:
                res = self.apiManager.getFinanicals(api, t.symbol, None, stype)
                if len(res.quarterlyReports) == 0:
                    dbm.insertFinancials_staging_empty(api, t.exchange, t.symbol, FinancialReportType.QUARTER)
                else:
                    dbm.insertFinancials_staging(api, t.exchange, res.quarterlyReports, period=FinancialReportType.QUARTER.name, symbol=t.symbol)

                if len(res.annualReports) == 0:
                    dbm.insertFinancials_staging_empty(api, t.exchange, t.symbol, FinancialReportType.YEAR)
                else:
                    dbm.insertFinancials_staging(api, t.exchange, res.annualReports, period=FinancialReportType.YEAR.name, symbol=t.symbol)
            except APIError:
                dbm.insertFinancials_staging_empty(api, t.exchange, t.symbol, FinancialReportType.QUARTER)
                dbm.insertFinancials_staging_empty(api, t.exchange, t.symbol, FinancialReportType.YEAR)

            # break

    ## collect stock split dates/amounts and insert to DB
    def startSplitsCollection(self, api, **kwargs):
        if api != 'polygon': raise 'Splits retrieval not supported by non-polygon API at the moment'

        insertcount = 0

        frameLength = 200
        ## latest split date in DB
        startDate = date.fromisoformat(dbm.getLatestSplitDate(shortcdict(kwargs, 'exchange', None))) #- timedelta(days=1)

        while startDate < date.today():
            endDate = startDate + timedelta(days=frameLength)
            ## API can return future dated splits so should be careful to ensure last split is on or before run date
            if endDate > date.today(): endDate = date.today()
            res = self.apiManager.getStockSplits(api, date=startDate.isoformat(), endDate=endDate.isoformat(), dateOperator=OperatorDict.GREATERTHANOREQUAL, endDateOperator=OperatorDict.LESSTHAN)

            if len(res) > 999:
                frameLength /= 2
                print('too much data, reducing frame to {}'.format(frameLength))
            else:
                print('got {} splits'.format(len(res)))

                startDate += timedelta(days=frameLength)
                if len(res) < frameLength / 4: frameLength *= 2

                dbm.startBatch()
                # try:
                for s in reversed(res):
                    exchange = None
                    ## try to determine the exchange that symbol belong(ed/s) to
                    symbols = dbm.getSymbols(symbol=s.ticker, api=api)
                    if len(symbols) == 0:
                        symbols = dbm.getSymbols(symbol=s.ticker)
                    if len(symbols) == 1:
                        exchange = symbols[0].exchange

                    try: 
                        dbm.insertStockSplit(exchange, s.ticker, s.execution_date, s.split_from, s.split_to)
                        insertcount += 1
                    except sqlite3.IntegrityError:
                        print('IntegrityError', exchange, s.ticker, s.execution_date)
                        pass
                dbm.commitBatch()

        print('inserted {} splits'.format(insertcount))

    def startEarningsDateCollection(self, api: EarningsCollectionAPI=None, dryrun=False, verbose=1, **kwargs):
        collectorHandleKey = 'collector'
        currentCollectDateKey = 'startDate'
        previousCollectDateKey = 'previousDate'
        rawDataKey = 'rawData'
        backCollectionRawDataKey = 'bcRawData'
        parsedDataKey = 'parsedData'
        collectionConfig = recdotdict({})

        ## determine APIs which will be collecting
        if api:
            try: collectionConfig[api if type(api) is EarningsCollectionAPI else EarningsCollectionAPI[api.upper()]] = {}
            except KeyError: raise ValueError(f'Earnings date retrieval not supported by {api} API at the moment')
        else:
            # for a in [EarningsCollectionAPI.NASDAQ, EarningsCollectionAPI.YAHOO]: ## MARKETWATCH covered by these two
            for a in EarningsCollectionAPI:
                collectionConfig[a] = {}

        ## initialize API collector handles
        for api in collectionConfig.keys():
            if api == EarningsCollectionAPI.NASDAQ:
                collectionConfig[api][collectorHandleKey] = Nasdaq()
            elif api == EarningsCollectionAPI.MARKETWATCH:
                collectionConfig[api][collectorHandleKey] = MarketWatch()
            elif api == EarningsCollectionAPI.YAHOO:
                collectionConfig[api][collectorHandleKey] = Yahoo()

        ## initialize data keys
        for api in collectionConfig.keys():
            collectionConfig[api][rawDataKey] = {}
            collectionConfig[api][parsedDataKey] = []

        ## determine start date(s)
        minDate = self.currentDate
        for api in collectionConfig.keys():
            apiCurrentCollectDate = dbm.getLatestEarningsCollectionDate(api)
            if not apiCurrentCollectDate:
                ## manually determined minimum date based on historical data table
                apiCurrentCollectDate = date(1999, 11, 1) - timedelta(days=1)
            else:
                apiCurrentCollectDate = date.fromisoformat(apiCurrentCollectDate)
                ## also get previous collect date for back-collection
                previousCollectDates = dbm.getUniqueEarningsCollectionDates(api)
                indx = getIndex(previousCollectDates, apiCurrentCollectDate)
                previousCollectDate = previousCollectDates[indx-1] if indx else None

                if api == EarningsCollectionAPI.MARKETWATCH: ## adjust back to start of week as collection will only be done on Mondays (since full week returned)
                    apiCurrentCollectDate -= timedelta(days=apiCurrentCollectDate.weekday())
                    if indx: previousCollectDate -= timedelta(days=previousCollectDate.weekday())
            collectionConfig[api][currentCollectDateKey] = apiCurrentCollectDate
            collectionConfig[api][previousCollectDateKey] = previousCollectDate
            if apiCurrentCollectDate < minDate:
                minDate = apiCurrentCollectDate
        
        endDate = self.currentDate + timedelta(days=90)

        ## MarketWatch: 2015/7/13 gives 403 error, 7/14 does not
        # minDate = date(2023,9,30) - timedelta(days=2) ## debugging
        # endDate = date(2008,1,31)
        # endDate = self.currentDate + timedelta(days=1)
        # endDate = minDate + timedelta(days=11)

        ## determine dates and tickers for back-collection
        ## TODO
        
        ## collect for all days from last anchor date to ~3 months out, inclusive
        for cdate in tqdmLoopHandleWrapper([minDate + timedelta(days=d) for d in range((endDate - minDate).days + 1)], verbose=verbose, desc='Collecting data'):
            for api in collectionConfig.keys():
                if api == EarningsCollectionAPI.MARKETWATCH and cdate.weekday() != 0: continue ## MarketWatch returns all days until end of week
                if collectionConfig[api][currentCollectDateKey] > cdate: continue ## skip re-collection of data
                rawdata = collectionConfig[api][collectorHandleKey].getEarningsDates(cdate, week=True)
                collectionConfig[api][rawDataKey][cdate] = rawdata

        ## parse all data into keyword arg objects for later DB insertion
        parseLoopTuples = []
        for a in collectionConfig.keys():
            for k,v in collectionConfig[a][rawDataKey].items():
                parseLoopTuples.append((a,k,v))
        for api,cdate,data in tqdmLoopHandleWrapper(parseLoopTuples, verbose=verbose, desc='Parsing data and constructing args'):
            for d in data:
                datapointKWArgs = {
                    'inputDate': self.currentDate,
                    'earningsDate': cdate if api == EarningsCollectionAPI.NASDAQ else d['date']
                }
                if api != EarningsCollectionAPI.NASDAQ:
                    datapointKWArgs['exchange'] = getYahooExchangeForSymbol(shortcdict(d, 'ticker', shortcdict(d, 'symbol')), shortcdict(d, 'companyshortname', shortcdict(d, 'name')))

                for k,v in d.items():
                    ## ignore keys
                    if k in ['date']: continue

                    ## adjust key to DB column (in camel case)
                    key = k
                    if k == 'lastYearRptDt': key = 'lastYearReportDate'
                    elif k in ['surprise', 'epssurprisepct', 'surprise_percentage']: key = 'surprisePercentage'
                    elif k == 'noOfEsts': key = 'numberOfEstimates'
                    elif k == 'ticker': key = 'symbol'
                    elif k == 'companyshortname': key = 'name'
                    elif k == 'epsestimate': key = 'epsForecast'
                    elif k == 'epsactual': key = 'eps'
                    elif k == 'fiscal quarter': key = 'fiscalQuarterEnding'
                    elif k == 'eventname': key = 'eventName'
                    elif k == 'startdatetime': key = 'startDateTime'
                    elif k == 'startdatetimetype': key = 'startDateTimeType'
                    elif k == 'lastYearEPS': key = 'lastYearEps'

                    ## parse and adjust value
                    val = v
                    if k in ['lastYearEPS', 'marketCap', 'epsForecast', 'eps']:
                        val = v.replace('$','').replace(',','')
                        if '(' in val:
                            val = val.replace('(','').replace(')','')
                            val = float(val) * -1
                        elif val not in ['', 'N/A']:
                            val = float(val)
                    elif k == 'lastYearRptDt' and v != 'N/A':
                        val = datetime.strptime(v, "%m/%d/%Y").date()
                    elif k == 'fiscalQuarterEnding':
                        try:
                            val = datetime.strptime(v, '%b/%Y').date()
                        except ValueError as e: ## v is '/2000'-type
                            print('got value error for fiscalQuarterEnding', v, e)
                            if v.count('/') == 1:
                                vsplit = v.split('/')
                                if vsplit[0] == '':
                                    val = vsplit[1]
                            else:
                                val = v
                    elif k == 'fiscal quarter':
                        val = datetime.strptime(v, '%m/%d/%Y').date()
                    elif k == 'surprise_percentage' and v != 'N/A' and api == EarningsCollectionAPI.MARKETWATCH:
                        val = float(v.split('(')[1].split('%')[0].replace(',',''))

                    ## no need to have multiple types of empty/blank/N/A values, use null instead 
                    if type(val) == str and val.lower() in ['', 'n/a']:
                        val = None
                    
                    datapointKWArgs[key] = val
                
                ## market watch surprise sign can be incorrect if forecasted eps is negative (e.g. forecast: -0.49, actual: -0.53, surprise: +8.7%)
                if api == EarningsCollectionAPI.MARKETWATCH and type(datapointKWArgs['eps']) not in [str, NoneType] and type(datapointKWArgs['epsForecast']) not in [str, NoneType] and type(datapointKWArgs['surprisePercentage']) not in [str, NoneType]:
                    if (datapointKWArgs['eps'] < datapointKWArgs['epsForecast'] and datapointKWArgs['surprisePercentage'] > 0) or (datapointKWArgs['eps'] > datapointKWArgs['epsForecast'] and datapointKWArgs['surprisePercentage'] < 0):
                        datapointKWArgs['surprisePercentage'] *= -1

                collectionConfig[api][parsedDataKey].append(datapointKWArgs)

        ## insert data
        insertcount = 0
        uniquedates = set()
        insertLoopTuples = []
        for a in collectionConfig.keys():
            for d in collectionConfig[a][parsedDataKey]:
                insertLoopTuples.append((a,d))
        for api,dkwargs in tqdmLoopHandleWrapper(insertLoopTuples, verbose=verbose, desc='Inserting data'):
            try:
                if not dryrun: dbm.insertEarningsDateDump(api, **dkwargs)
                insertcount += 1
                uniquedates.add(dkwargs['earningsDate'])
            except sqlite3.IntegrityError:
                pass

        print(f'got data for {len(uniquedates)} days')
        print(f'inserted {insertcount} earnings dates')

    ## collect google interests and insert to DB
    ## measures up-to-date-ness by comparing latest GI and stock data dates, if not then it will collect data up til maxdate rather than til the latest stock data date
    def startGoogleInterestCollection(self, interestType:InterestType=InterestType.DAILY, direction:Direction=Direction.ASCENDING, collectStatsOnly=False, dryrun=False, **kwargs):
        gapi = Google()

        maxdate = copy.deepcopy(self.currentDate)
        ## up-to-date GI data is only available after 3 days
        if interestType == InterestType.DAILY:
            maxdate -= timedelta(days=4)
        else: ## WEEKLY or MONTHLY
            ## too close to beginning of month, need to go further back to get previous previous month
            if date.today().day < 4:
                maxdate -= timedelta(days=14)
            maxdate -= timedelta(days=maxdate.day)

        overlap_period = timedelta(days=15)
        daily_period = timedelta(weeks=34) ## anything much more will start returning weekly blocks
        weekly_period = timedelta(weeks=266) ## anything much more will start returning monthly blocks
        period = weekly_period if interestType == InterestType.WEEKLY else daily_period

        ## prioritizes based on how many '0's are in the period (i.e. daily search counts; popular tickers have more days where there are at least a handle of searches)
        useprioritythreshold = False
        priority_zeropercentagethreshold = 0.9
        def getZeroPercentage(gi, period=183): ## ~6 months
            zerocount = 0
            for g in gi[-period:]:
                if g['relative_interest'] == 0: zerocount += 1
            return zerocount/period

        ## stats stuff
        stats_uptodate = 0
        stats_notstarted = 0
        stats_partiallycollected = 0
        stats_nostockdata = 0
        successfulRequestCount = 0
        totalDataPointsCollected = 0
        def finish(): 
            if collectStatsOnly:
                total = stats_uptodate + stats_notstarted + stats_partiallycollected + stats_nostockdata
                print(f'{total} tickers checked')
                print(f'{stats_uptodate} are up-to-date(-ish)')
                print(f'{stats_partiallycollected} are partially collected')
                print(f'{stats_notstarted} are not started')
                print(f'{stats_nostockdata} have no stock data')
            else:
                print(f'{successfulRequestCount} requests made')
                print(f'{totalDataPointsCollected} data points collected')
        ##

        ## due to prioritization, collection loop repeats until all symbols are up-to-date
        symbollist = dbm.getSymbols(googleTopicId=SQLHelpers.NOTNULL)

        while len(symbollist):
            if not collectStatsOnly: print(f'Checking {len(symbollist)} symbols{f" with <={priority_zeropercentagethreshold*100}% zeroes" if useprioritythreshold else ""}')
            else: print(f'Collecting stats for {len(symbollist)} tickers')

            for s in symbollist[:]:
                tickergidString = f'{s.exchange:10s} {s.symbol:5s} {s.google_topic_id:15s}'

                sdata = dbm.getStockData(s.exchange, s.symbol, SeriesType.DAILY)
                if not sdata:
                    print(tickergidString, '- no stock data')
                    symbollist.remove(s)
                    stats_nostockdata += 1
                    continue

                ginterests = dbm.getGoogleInterests(s.exchange, s.symbol, itype=interestType, raw=True)

                ## determine start date for first collection period if applicable (startdate not getting set typically means symbol is up-to-date)
                startdate = None
                cur_direction = None
                upsertData = False
                stream = 0
                if interestType == InterestType.MONTHLY:
                    cur_direction = Direction.ASCENDING
                    upsertData = True
                    if ginterests:
                         if date.fromisoformat(ginterests[-1].date) < maxdate:
                            startdate = date.fromisoformat(ginterests[0].date)
                    else:
                        startdate = min(
                            maxdate - timedelta(weeks=278), ## offset >275? weeks to trigger monthly buckets
                            max(
                                minGoogleDate, 
                                date.fromisoformat(sdata[0].period_date) - timedelta(weeks=5) ## need to offset further to actually get month data for first stock data month
                            )
                        )
                else: ## DAILY or WEEKLY
                    if ginterests:
                        cur_direction = direction
                        if cur_direction == Direction.DESCENDING:
                            ## should only be a continuation of initial (stream 0) data collection
                            if sdata[0].period_date < ginterests[0].date:
                                startdate = date.fromisoformat(ginterests[0].date) - timedelta(days=1)
                        else: ## ascending
                            if dryrun: print(sdata[-1].period_date, ginterests[-1].date)
                            if sdata[-1].period_date > ginterests[-1].date:
                                ## check if latest stream can be updated instead of starting a new stream
                                maxStream = dbm.getMaxGoogleInterestStream(s.exchange, s.symbol, itype=interestType)
                                maxStreamData = dbm.getGoogleInterests(s.exchange, s.symbol, itype=interestType, stream=maxStream, raw=True)
                                maxStreamMinDate = date.fromisoformat(maxStreamData[0].date)
                                if maxStreamMinDate + period >= maxdate: ## period can cover all latest stream dates as well, so stream can be reused and updated
                                    startdate = maxStreamMinDate
                                    upsertData = True
                                    stream = maxStream
                                    print(f'Re-using stream {stream}')
                                else: ## need to start new stream
                                    ## should ensure there is at least one week block that overlaps between last stream and this new one, spanning the end of the last full month
                                    lastgidate = date.fromisoformat(ginterests[-1].date)
                                    startdate = lastgidate - timedelta(days=lastgidate.day) + timedelta(days=1) - overlap_period
                                    stream = maxStream + 1
                                    print(f'Starting (new) stream {stream}')
                    else:
                        cur_direction = Direction.DESCENDING
                        ## adjust so for stream 0 most recent daily period aligns with end of latest month (could? cause problems calculating relative_interest otherwise once more streams are involved and proper overlaps are required)
                        startdate = maxdate - timedelta(days=maxdate.day)
                        print('no ginterests')

                ## already up-to-date
                if not startdate or startdate < minGoogleDate or (cur_direction == Direction.ASCENDING and startdate > maxdate):
                    print(tickergidString, 'already up-to-date')
                    stats_uptodate += 1
                    symbollist.remove(s)
                    continue
                ## priority skip if not meeting threshold
                elif ginterests and useprioritythreshold and getZeroPercentage(ginterests) > priority_zeropercentagethreshold:
                    print(tickergidString, f'{priority_zeropercentagethreshold} priority threshold not met')
                    stats_partiallycollected += 1
                    continue
                ## not up-to-date
                else:
                    print(tickergidString)
                    if ginterests: 
                        print(cur_direction, '|  STK:', sdata[0].period_date, '->', sdata[-1].period_date, '|  GI:', ginterests[0].date, '->', ginterests[-1].date)
                        stats_partiallycollected += 1
                    else:
                        stats_notstarted += 1
                    if collectStatsOnly: continue
                
                ## is GI data up-to-date yet
                def fullyUpdated():
                    if cur_direction == Direction.DESCENDING:
                        return startdate < date.fromisoformat(sdata[0].period_date)
                    else:
                        return startdate > maxdate
                        # return startdate > date.fromisoformat(sdata[-1].period_date)

                ## insert interests data in chronological order into DB
                def insertGData(data:List):
                    nonlocal stream
                    nonlocal totalDataPointsCollected
                    if not data: return

                    data.sort(key=lambda a: a['startDate'])

                    for g in data:
                        if g['endDate']: ## weekly or monthly
                            for d in [(g['startDate'] + timedelta(days=d)) for d in range((g['endDate'] - g['startDate']).days + 1)]:
                                dbm.insertRawGoogleInterest(s.exchange, s.symbol, interestType, d, g['relative_interest'], upsert=upsertData)
                        else: ## daily
                            dbm.insertRawGoogleInterest(s.exchange, s.symbol, interestType, g['startDate'], g['relative_interest'], stream, upsert=upsertData)

                    totalDataPointsCollected += len(data)

                if interestType == InterestType.MONTHLY:
                    ## only one loop will run, so covers all data
                    period = timedelta(days=(maxdate - startdate).days)

                ## collect all interests historical data first
                gData = []
                apierrorbreak = False
                prioritybreak = False
                somedatagathered=False
                cur_period = period
                advanceStreamAndOverlap = False
                while not fullyUpdated() and not apierrorbreak:
                    directionmodifier = -1 if cur_direction == Direction.DESCENDING else 1
                    # ASCENDING: startdate -> endate;   i.e. begin with oldest time range and shift forwards
                    # DESCENDING: enddate <- startdate; i.e. begin with most recent time range and shift backwards
                    enddate = startdate + (cur_period * directionmodifier)
                    nextenddate = enddate + timedelta(days=1) + cur_period

                    if advanceStreamAndOverlap:
                        ## this is the last period, so need to increment the stream and ensure there is sufficient overlap with previous stream
                        ## insert current data into "previous" stream before incrementation
                        if dryrun:  print('inserting to stream', stream)
                        else:       insertGData(gData)
                        gData = []

                        startdate -= overlap_period
                        stream += 1

                    ## adjust enddate and/or final periods in this symbol's collection
                    if enddate > maxdate: enddate = maxdate
                    elif not advanceStreamAndOverlap and interestType == InterestType.DAILY and cur_direction == Direction.ASCENDING and nextenddate > maxdate: 
                        ## this will be the last full period, so need to make sure last full month is end of this stream and remainder is in the next so either method of keeping GI data up-to-date can be used (i.e. processing to relative values with or without corresponding monthly data for streams > 0)
                        enddate -= timedelta(days=enddate.day)
                        advanceStreamAndOverlap = True


                    ## Google does not have/allow data before 2004-01-01
                    if startdate < minGoogleDate: break
                    if enddate < minGoogleDate and startdate >= minGoogleDate:
                        enddate = minGoogleDate
                    elif cur_direction == Direction.DESCENDING and enddate.weekday() < 6: ## ??shift day to align with google interest week period (??i.e. mon-sun)
                        enddate += timedelta(days=abs(6-enddate.weekday()))

                    ## get GI data for current start/end date period via exponential backoff loop, to gracefully handle API timeouts
                    gResp = []
                    backoff = 60
                    while not gResp:
                        if dryrun:
                            print('requesting for', startdate, '->', enddate)
                            successfulRequestCount += 1
                            break
                        try:
                            gResp = gapi.getHistoricalInterests(s.google_topic_id, startdate, enddate)
                            if len(gResp) == 0:
                                if somedatagathered:
                                    break
                                else:
                                    raise APIError(400)
                            successfulRequestCount += 1
                            backoff = 60
                        except APITimeout:
                            insertGData(gData)
                            gData = []

                            if backoff >= 4 * 60:
                                print('Backoff exceeds limit, exiting')
                                finish()
                                return

                            print(f'Timeout, sleeping {backoff} seconds')
                            timer.sleep(backoff)
                            backoff *= 2
                        except APIError as e:
                            apierrorbreak = True
                            if e.args and e.args[0] == 400: ## g topic is no longer valid
                                print(f'Topic ID no longer valid for {s.exchange}:{s.symbol}.')
                                dbm.dbc.execute('UPDATE symbols SET google_topic_id=NULL WHERE google_topic_id=?', (s.google_topic_id,))
                            else:
                                print(f'API error for {s.exchange}:{s.symbol}. Some data gathered: {somedatagathered}')    
                            break

                    gData.extend(gResp)
                    ## priority skip if not meeting threshold
                    if not somedatagathered and useprioritythreshold and getZeroPercentage(gData) > priority_zeropercentagethreshold:
                        print('Priority threshold not met')
                        prioritybreak = True
                        break
                    somedatagathered = True
                    startdate = enddate + (timedelta(days=1) * directionmodifier)

                ## insert all collected GI data
                if dryrun:  print('inserting to stream', stream)
                else:       insertGData(gData)
                
                if not prioritybreak:
                    symbollist.remove(s)
                print()

            ## advance to next zero percentage threshold and re-run symbol loop
            priority_zeropercentagethreshold += 0.1
            if collectStatsOnly: break

        finish()

if __name__ == '__main__':
    opts, kwargs = parseCommandLineOptions()
    currentDate = shortcdict(kwargs, 'currentDate', date.today())
    c = Collector(currentDate)

    if opts.api:
        if opts.api == 'vix':
            c.collectVIX()
        elif opts.type == 'splits':
            c.startSplitsCollection(opts.api, **kwargs)
        elif opts.type == 'earningsdate':
            c.startEarningsDateCollection(opts.api, **kwargs)
        else:
            c.startAPICollection(opts.api, **kwargs)
    elif opts.function:
        getattr(c, opts.function)(**kwargs)
    else:
        # c.start(SeriesType.DAILY)
        # c.start()
        # c._collectFromAPI('polygon', [recdotdict({'symbol':'KRP'})], None)

        # c.startAPICollection('alphavantage', SeriesType.DAILY)

        try:
            # c.collectPolygonTickerDetails()
            # c.collectFMPTickerDetails()     ## reset around 4pm?
            # c.collectAlphavantageTickerDetails()
            # dbm.staging_condenseFounded()
            # dbm.staging_condenseSector()
            # dbm.symbols_pullStagedFounded()
            # dbm.symbols_pullStagedSector()
            c.startAPICollection('alphavantage', SeriesType.DAILY)
            # c.startAPICollection_exploratoryAlphavantageAPIUpdates()
            # c.startSplitsCollection('polygon')
            # c.startAPICollection('neo', SeriesType.DAILY)
            # c.startAPICollection('polygon', SeriesType.DAILY)
            # c.startGoogleInterestCollection(direction=Direction.DESCENDING)
            # c.startGoogleInterestCollection(direction=Direction.DESCENDING, collectStatsOnly=True)
            pass
        except KeyboardInterrupt:
            # dbm.staging_condenseFounded()
            # dbm.staging_condenseSector()
            # dbm.symbols_pullStagedFounded()
            # dbm.symbols_pullStagedSector()
            raise KeyboardInterrupt
        
        # with open(os.path.join(path, 'interfaces\\alphavantagexlist.txt'), 'r') as f:
        #     for symbol in f:
        #         # print('\"' + symbol[:-1] + '\"')
        #         dbm.updateSymbolTempInfo(recdotdict({ 'sector': 'x' }), 'alphavantage', symbol=symbol[:-1])


        #     dbm.staging_condenseFounded()
        #     dbm.staging_condenseSector()


        # c.collectPolygonFinancials(FinancialReportType.QUARTER)
        # c.collectFMPFinancials(FinancialReportType.QUARTER, FinancialStatementType.INCOME) ## premium api
        # c.collectAlphavantageFinancials(FinancialStatementType.INCOME)
        # c.collectAlphavantageFinancials(FinancialStatementType.BALANCE_SHEET)
        # c.collectAlphavantageFinancials(FinancialStatementType.CASH_FLOW)


    # c.collectAPIDump_symbolInfo('polygon')


    print('done')

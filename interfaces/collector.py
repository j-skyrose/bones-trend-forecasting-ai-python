import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, queue, atexit, traceback, math, requests, csv, codecs
import time as timer
from datetime import date, timedelta
from threading import Thread
from contextlib import closing

from managers.databaseManager import DatabaseManager
from managers.apiManager import APIManager

from constants.exceptions import APILimitReached, APIError
from utils.support import recdotdict
from constants.enums import FinancialReportType, FinancialStatementType, SeriesType
import json

dbm: DatabaseManager = DatabaseManager()

DEBUG = True

class Collector:
    def __init__(self):
        atexit.register(self.close)
        self.apiManager = APIManager()
        self.apiErrors = []

    def close(self):
        self.apiManager.saveConfig()
        print('collector shutting down')

    def __singleSymbolCollect(self, api, symbols, type):
        # for s in symbols:
        #     print(s.exchange, s.symbol)
        # return
        localDBM: DatabaseManager = DatabaseManager()
        counter = 0
        try:
            for sp in symbols:
                try:
                    # self.returnQueue.put((api, sp.exchange, sp.symbol, type, self.apiManager.query(api, sp.symbol, type)))
                    localDBM.insertData(sp.exchange, sp.symbol, type.name, api, self.apiManager.query(api, sp.symbol, type))
                    localDBM.commit()
                    counter += 1
                except APIError:
                    print('api error',sys.exc_info()[0])
                    print(traceback.format_exc())
                    self.apiErrors.append((sp.exchange, sp.symbol))
                    # try:
                    #     dbm.dbc.execute('UPDATE symbols SET api_?=-1 WHERE exchange=? AND symbol=?',(api, sp.exchange, sp.symbol))
                    # except:
                    #   sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread. The object was created in thread id 64284 and this is thread id 34320.
                    #     print('update api error',sys.exc_info()[0])
                    #     print(traceback.format_exc())

                # print ('mocking sp', sp)
                # self.returnQueue.put((api, sp.exchange, sp.symbol, recdotdict({
                #     '2020-01-01': {
                #         'open': "5.22",
                #         'high': "5.21",
                #         'low': "5.12",
                #         'close': "5.24",
                #         'volume': "4.22"
                #     },
                #     '2020-01-05': {
                #         'open': "5.22",
                #         'high': "5.21",
                #         'low': "5.12",
                #         'close': "5.24",
                #         'volume': "4.22"
                #     }
                # })))
        except APILimitReached:
            print('api limit reached for',api)
            pass

        print('Updated', api, 'data for', counter, '/', len(symbols), 'symbols')
        localDBM.close()

    def __singleDateBatchCollect(self, api):
        localDBM = DatabaseManager()
        batchByDate = {}
        startingPastDaysCount = self.apiManager.apis[api].priority * 365
        lastUpdatedPastDaysCount = math.floor( (date.today() - self.apiManager.apis[api].updatedOn).total_seconds() / (60 * 60 * 24) )
        if DEBUG: print('max days', startingPastDaysCount, 'last updated delta', lastUpdatedPastDaysCount)

        currentdate = date.today()
        if currentdate.weekday() < 5: print('WARNING: running too early on weekdays may result in incomplete data\nOpt to run after ~6pm')
        for c in range(min(startingPastDaysCount, lastUpdatedPastDaysCount)-1, -1, -1):
        # for c in range(1):
            try:
                d = (currentdate - timedelta(days=c)).isoformat()
                # res = self.apiManager.apis[api].api.query(d)
                res = self.apiManager.query(api, qdate=d)
                if len(res) > 0:
                    batchByDate[d] = res
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
        # bucketSymbols = [sp.symbol for sp in symbols]
        for s in tqdm.tqdm(batchBySymbol, desc='Inserting data'):
            # if s in bucketSymbols:
                exchangeQuery = localDBM.getSymbols(symbol=s, api=api)
                if len(exchangeQuery) != 1:
                    self.apiErrors.append(('-',s))
                    continue

                # break
                localDBM.insertData(exchangeQuery[0].exchange, s, SeriesType.DAILY.name, api, batchBySymbol[s])
                localDBM.commit()
                counter += 1
            # else:
            #     self.apiErrors.append(('n/a', s))

        print('Updated', api, 'data for', counter, 'symbols')
        localDBM.close()

    def _collectFromAPI(self, api, symbols=None, type=None):
        if type:
            print(api,'collector started',len(symbols))
            if api == 'alphavantage': self.__singleSymbolCollect(api, symbols, type)
        else:
            print(api,'collector started')
            if api == 'polygon': self.__singleDateBatchCollect(api)

        self.activeThreads -= 1
        print(api,'collector complete','\nThreads remaining',self.activeThreads)

    def startAPICollection(self, api, stype: SeriesType):
        typeAPIs = ['alphavantage'] #self.apiManager.getAPIList(sort=True)
        nonTypeAPIs = ['polygon']

        try:

            if api in nonTypeAPIs:
                self.__singleDateBatchCollect(api)
                
            else:
                ## gather symbols for this collection run
                lastUpdatedList = dbm.getLastUpdatedCollectorInfo(type=stype, api=api).fetchall()
                if DEBUG: print('lastUpdatedList length',len(lastUpdatedList))
                symbols = []
                for r in lastUpdatedList:
                    # ## cull all rows that have been updated today by the currently checked API (higher priority already culled in previous iteration)
                    # if r.api == api and date.fromisoformat(r.date) == date.today():
                    #     continue
                    # above is obsolete while all alphavantage stocks have been collected at least once for the given series type within the past 2 years
                    # polygon can handle all these stocks now, unless they are not available from the api, in which case only alphavantage can retrieve updated info
                    if date.fromisoformat(r.date) == date.today():
                        continue

                    ## only include if symbol is supported by API
                    try:
                        if r['api_'+api] == 1:
                            symbols.append(r)
                    except KeyError:
                        print('key error checking if symbol is supported by api', api)
                        raise APIError
                    if len(symbols) == self.apiManager.apis[api]['remaining']: break

                print('symbol list size', len(symbols))
                self.__singleSymbolCollect(api, symbols, stype)


        except (KeyboardInterrupt, APIError):
            print('keyboard interrupt')
            if api != 'polygon': self.close()

        print('API Errors:',self.apiErrors)


    def startold(self, type):
        self.interrupted = False
        try:
            typeAPIs = ['alphavantage'] #self.apiManager.getAPIList(sort=True)
            # nonTypeAPIs = ['polygon']
            nonTypeAPIs = []

            ## sort symbols into buckets for each API based on priority
            lastUpdatedList = dbm.getLastUpdatedCollectorInfo(type=type).fetchall()
            if DEBUG: print('lastUpdatedList length',len(lastUpdatedList))
            buckets = []
            for a in range(len(typeAPIs)):
                if DEBUG: print('looping', typeAPIs[a])
                bucket = []
                for r in lastUpdatedList:
                    ## cull all rows that have been updated today by the currently checked API (higher priority already culled in previous iteration)
                    if r.api == typeAPIs[a] and date.fromisoformat(r.date) == date.today():
                        lastUpdatedList.remove(r)
                        continue

                    ## only include if symbol is supported by API
                    try:
                        if r['api_'+typeAPIs[a]] == 1:
                            bucket.append(r)
                            lastUpdatedList.remove(r)
                    except KeyError:
                        pass
                    if len(bucket) == self.apiManager.apis[typeAPIs[a]]['remaining']: break
                buckets.append(bucket)

            print('bucket sizes',[len(x) for x in buckets])

            ## create threads for each API
            # self.returnQueue = queue.Queue()
            self.activeThreads = 0
            # for a in range(len(typeAPIs)):
            #     collector = Thread(target=self._collectFromAPI, args=(typeAPIs[a], buckets[a], type))
            #     collector.setDaemon(True)
            #     collector.start()
            #     self.activeThreads += 1

            # for a in range(len(nonTypeAPIs)):
            #     collector = Thread(target=self._collectFromAPI, args=(nonTypeAPIs[a],))
            #     collector.setDaemon(True)
            #     collector.start()
            #     self.activeThreads += 1

            # while self.activeThreads > 0:
            #     timer.sleep(1)

            
            for a in range(len(typeAPIs)):
                self._collectFromAPI(typeAPIs[a], buckets[a], type)

            for a in range(len(nonTypeAPIs)):
                self._collectFromAPI(nonTypeAPIs[a])

        except (KeyboardInterrupt, APIError):
            print('keyboard interrupt')
            self.interrupted = True
            self.close()
            # try:
            #     sys.exit(0)
            # except SystemExit:
            #     os._exit(0)

        print('API Errors:',self.apiErrors)

    def startold2(self, type):
        self.interrupted = False
        try:
            apis = ['alphavantage'] #self.apiManager.getAPIList(sort=True)
            # apis = ['polygon']

            ## sort symbols into buckets for each API based on priority
            lastUpdatedList = dbm.getLastUpdatedCollectorInfo(type=type).fetchall()
            if DEBUG: print('lastUpdatedList length',len(lastUpdatedList))
            buckets = []
            for a in range(len(apis)):
                if DEBUG: print('looping', apis[a])
                bucket = []
                for r in lastUpdatedList:
                    ## cull all rows that have been updated today by the currently checked API (higher priority already culled in previous iteration)
                    if r.api == apis[a] and date.fromisoformat(r.date) == date.today():
                        lastUpdatedList.remove(r)
                        continue

                    ## only include if symbol is supported by API
                    try:
                        if r['api_'+apis[a]] == 1:
                            bucket.append(r)
                            lastUpdatedList.remove(r)
                    except KeyError:
                        pass
                    if len(bucket) == self.apiManager.apis[apis[a]]['remaining']: break
                buckets.append(bucket)

            print('bucket sizes',[len(x) for x in buckets])

            ## create threads for each API
            # self.returnQueue = queue.Queue()
            self.activeThreads = 0
            for a in range(len(apis)):
                collector = Thread(target=self._collectFromAPI, args=(apis[a], buckets[a], type))
                collector.setDaemon(True)
                collector.start()
                self.activeThreads += 1

            ## insert collected data into the database
            # cond = True
            # counter=1
            # qempty=True
            # while cond:
            #     try:
            #         api, exchange, symbol, type, data = self.returnQueue.get(True, 3)
            #         dbm.insertData(exchange, symbol, type.name, api, data)
            #         self.returnQueue.task_done()
            #         counter += 1
            #         qempty=False
            #     except queue.Empty:
            #         qempty=True
            #         pass
            #     cond = self.activeThreads > 0 or not self.returnQueue.empty()
            #     ## sum(a['remaining'] for a in self.apiManager.apis.values()) > 0
            #
            #     if counter % 5 == 0 and not qempty: dbm.commit()
            #
            # # print('Updated data for', sum(len(x) for x in buckets), 'symbols')
            # print('Updated data for', counter-1, '/', sum(len(x) for x in buckets), 'symbols')

            while self.activeThreads > 0:
                timer.sleep(1)

        except (KeyboardInterrupt, APIError):
            print('keyboard interrupt')
            self.interrupted = True
            self.close()
            # try:
            #     sys.exit(0)
            # except SystemExit:
            #     os._exit(0)

        print('API Errors:',self.apiErrors)

    def collectVIX(self):
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

    def collectAPIDump_symbolInfo(self, api):
        substmt = 'SELECT * FROM dump_symbol_info WHERE dump_symbol_info.exchange = staging_symbol_info.exchange AND dump_symbol_info.symbol = staging_symbol_info.symbol AND ' + api + ' IS NOT NULL'
        # stmt = 'SELECT exchange, symbol FROM symbols WHERE NOT EXISTS (' + substmt + ') AND api_' + api + ' = 1'

        ## still pulling NYSE:AAC even though row is present in dump table

        stmt = 'SELECT staging_symbol_info.exchange, staging_symbol_info.symbol FROM staging_symbol_info JOIN symbols ON staging_symbol_info.exchange = symbols.exchange AND staging_symbol_info.symbol = symbols.symbol WHERE NOT EXISTS (' + substmt + ') AND polygon_sector NOT IN (\'e\',\'x\') AND api_' + api + ' = 1'
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

    def collectPolygonTickerDetails(self):
        def postprocessing(details):
            details['ipoDate'] = details.pop('listdate')
            return details
        return self.__collectAPITickerDetails('polygon', postprocessing)
        
    def collectFMPTickerDetails(self):
        return self.__collectAPITickerDetails('fmp')

    def collectAlphavantageTickerDetails(self):
        def postprocessing(details: dict):
            details['sector'] = details.pop('Sector')
            details['industry'] = details.pop('Industry')
            details['assetType'] = details.pop('AssetType')
            details['description'] = details.pop('Description')
            return details
        return self.__collectAPITickerDetails('alphavantage', postprocessing)          


    def collectPolygonFinancials(self, ftype: FinancialReportType):
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
    def collectFMPFinancials(self, ftype: FinancialReportType, stype: FinancialStatementType):
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
    def collectAlphavantageFinancials(self, stype: FinancialStatementType):
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

if __name__ == '__main__':

    print('starting')
    c = Collector()

    try:
        fl, arg1, *argv = sys.argv
    except ValueError:
        arg1 = ''
        pass
    if arg1.lower() == 'api':
        c.startAPICollection(argv[0].lower(), SeriesType[argv[1].upper()] if len(argv) > 1 else None)
    elif arg1.lower() == 'vix':
        c.collectVIX()
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

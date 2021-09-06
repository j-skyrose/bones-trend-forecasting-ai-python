import json
import os, sys
from typing import List
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import math, re, dill, operator, shutil
import sqlite3, atexit, numpy as np, xlrd
from datetime import date, timedelta, datetime
from tqdm import tqdm
from multiprocessing import current_process

from managers.dbCacheManager import DBCacheManager
from structures.api.googleTrends.request import GoogleAPI

from globalConfig import config as gconfig
from structures.neuralNetworkInstance import NeuralNetworkInstance
from constants.enums import FinancialReportType, OperatorDict, SeriesType, AccuracyType, SetType
from utils.support import processDBQuartersToDicts, processRawValueToInsertValue, recdot, recdotdict, Singleton, extractDateFromDesc, getMarketHolidays, recdotlist, shortc
from constants.values import testingSymbols, unusableSymbols, apiList

def addLastUpdatesRowsForAllSymbols(dbc):
    symbolPairs = dbc.execute("SELECT exchange, symbol FROM symbols").fetchall()
    print(len(symbolPairs),'symbols found')

    tot = 0
    for s in symbolPairs:
        exchange, symbol = s
        # print(s)

        for e in SeriesType:
            dbc.execute('INSERT OR IGNORE INTO last_updates(exchange, symbol, type, date) VALUES (?,?,?,?)', (exchange, symbol, e.function, '1970-01-01'))
            tot += dbc.rowcount
    print(tot, 'rows added')

## for ad hoc SQL execution ################################################################################################
# conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'raw/sp2Database.db'))
# dbc = conn.cursor()
# # importFromSymbolDumps(dbc)
# # dbc.execute("DELETE FROM symbols WHERE symbol like '%-%';")
# # dbc.execute("DELETE FROM symbols WHERE asset_type IS NOT NULL  ;")
# # dbc.execute("UPDATE symbols SET api_alphavantage=0 where asset_type IS NULL")
# addLastUpdatesRowsForAllSymbols(dbc)
#
# conn.commit()
# conn.close()
## end ad hoc SQL execution ################################################################################################

class DatabaseManager(Singleton):
    def init(self):
        atexit.register(self.close)
        self.connect = sqlite3.connect(os.path.join(path, 'data/sp2Database.db'), timeout=15)
        # self.connect.row_factory = sqlite3.Row
        self.connect.row_factory = self.__dict_factory
        self.dbc = self.connect.cursor()

        ## caching
        self.cacheManager = DBCacheManager()
        self.historicalDataCount = None

        ## one time retrieval saves
        self.exchanges = None
        self.assetTypes = None

    def close(self):
        ## save changes and close database connection
        self.commit()
        if current_process().name == 'MainProcess': print('Committed changes')
        self.connect.close()

    def commit(self):
        self.connect.commit()

    def __dict_factory(self, c, r):
        d = {}
        for idx, col in enumerate(c.description):
            d[col[0]] = r[idx]
        return recdotdict(d)


    def _getHistoricalDataCount(self):
        if not self.historicalDataCount:
            self.historicalDataCount = self.dbc.execute('SELECT count(1) FROM historical_data').fetchone()
        return self.historicalDataCount

    def _queryOrGetCache(self, query, qarg, validationObj, tag):
        print('qorc', query)
        cache = self.cacheManager.getCache(query, validationObj)
        if cache: 
            print('got cache')
            data = cache
        else: 
            print('no cache, executing')
            data = self.dbc.execute(query, qarg).fetchall()
            self.cacheManager.addInstance(tag, query, validationObj, data)
        return data

    def _convertVIXDataPoint(self, data):
        if '/' in str(data[0]):
            data[0] = datetime.strptime(data[0], "%m/%d/%Y").date().isoformat()
        else:
            year, month, day, *rem = xlrd.xldate_as_tuple(data[0], 0)
            data[0] = date(year, month, day).isoformat()
        for i in range (1, 5):
            data[i] = data[i] if data[i] != 'n/a' else 0
        return data


    ####################################################################################################################################################################
    ## gets ####################################################################################################################################################################

    def getLoadedQuarters(self):
        # stmt = 'SELECT DISTINCT fy, fp FROM dump_edgar_sub'
        # qrts = self.dbc.execute(stmt).fetchall()
        # return [q.fy.lower() + q.fp.lower() for q in qrts]
        # return []

        qrts = self.dbc.execute('SELECT period FROM dump_edgar_loaded WHERE type=\'quarter\'').fetchall()
        return [q.period for q in qrts]

    def getAliasesDictionary(self, api):
        ret = {}
        for r in self.dbc.execute('SELECT exchange, alias FROM exchange_aliases WHERE api=?', (api,)).fetchall():
            ret[r['alias']] = r['exchange']
            ret[r['exchange']] = r['exchange']
        return recdotdict(ret)

    ## add a new API option with data retrieval capabilities
    ## adds new column to symbols table for new API and can set for supported symbols
    def addAPI(self, api, exchange=None, symbolList=None, pairedList=None):
        stmt = 'ALTER TABLE symbols ADD COLUMN api_' + api + ' INTEGER NOT NULL DEFAULT 0'
        self.dbc.execute(stmt)

        if (exchange and symbolList) or pairedList:
            stmt = 'UPDATE symbols SET api_' + api + '=1 WHERE exchange=? AND symbol=?'
            tuples=[]
            if pairedList:
                if type(pairedList[0]) == object:
                    for r in pairedList:
                        tuples.append((r.exchange, r.symbol))
                else:
                    for r in pairedList:
                        tuples.append((r[0], r[1]))
            else:
                for s in symbolList:
                    tuples.append((exchange, s))

            self.dbc.executemany(stmt, tuples)

    ## get data from symbol_list table
    def getSymbols(self, exchange=None, symbol=None, assetType=None, api=None, googleTopicId=None, withDetailsMissing=False):
        stmt = 'SELECT * FROM symbols'
        args = []
        adds = []
        if exchange or symbol or assetType or api or withDetailsMissing:
            stmt += ' WHERE '
            if exchange:
                adds.append('exchange = ?')
                args.append(exchange)
            if symbol:
                adds.append('symbol = ?')
                args.append(symbol)
            if assetType:
                adds.append('asset_type = ?')
                args.append(assetType)
            if api:
                if type(api) is list:
                    apiAdds = []
                    for a in api:
                        apiAdds.append('api_'+a+' = 1')
                    adds.append('(' + ' OR '.join(apiAdds) + ')')
                else:
                    adds.append('api_'+api+' = 1')
            if googleTopicId:
                adds.append('google_topic_id = ?')
                args.append(googleTopicId if googleTopicId != -1 else None)
            if withDetailsMissing:
                adds.append('((sector IS NULL AND industry IS NULL) OR (sector = \'\' and industry = \'\'))')


            stmt += ' AND '.join(adds)

        # print('executing',stmt, args)
        return self.dbc.execute(stmt, tuple(args)).fetchall()

    ## assumes you are looking for rows that have details missing
    def getSymbolsTempInfo(self, api):
        stmt = 'SELECT * FROM staging_symbol_info ts JOIN symbols s ON ts.exchange=s.exchange AND ts.symbol=s.symbol'
        stmt += ' WHERE api_' +api+ '=1'

        ## new may 18
        stmt += ' AND ('+api+'_sector IS NULL OR ('+api+'_sector <> \'x\' AND ts.founded IS NULL and '+api+'_description IS NULL))'
        stmt += ' ORDER BY alphavantage_description, polygon_description, fmp_description'

        ## old may 18
        # stmt += ' AND ((' +api+ '_sector IS NULL AND ' +api+ '_industry IS NULL) OR (' +api+ '_sector = \'\' and ' +api+ '_industry = \'\')'
        # if api == 'polygon':
        #     stmt += ' OR polygon_ipo IS NULL'
        # stmt += ' OR ' + api + '_description IS NULL'
        # stmt += ')'

        return self.dbc.execute(stmt).fetchall()

    def getStagedSymbolRows(self):
        # return self.dbc.execute('SELECT * FROM staging_symbol_info WHERE exchange=?', ('NYSE',)).fetchall()
        return self.dbc.execute('SELECT * FROM staging_symbol_info').fetchall()

    ## get symbols of which financials retrieval has not already been attempted
    def getSymbols_forFinancialStaging(self, api, ftype: FinancialReportType=None):
        # stmt = 'SELECT s.exchange, s.symbol FROM symbols s LEFT JOIN staging_financials sf ON s.exchange = sf.exchange AND s.symbol = sf.symbol WHERE sf.exchange IS NULL AND sf.symbol IS NULL AND s.api_' + api + ' = 1'
        # if ftype:
        #     stmt += ' AND sf.period = \'' + ftype.name + '\''
        substmt = 'SELECT * FROM staging_financials WHERE exchange = symbols.exchange AND symbol = symbols.symbol AND ' + api + ' IS NOT NULL'
        if ftype: substmt += ' AND period = \'' + ftype.name + '\''
        stmt = 'SELECT exchange, symbol FROM symbols WHERE NOT EXISTS (' + substmt + ') AND api_' + api + ' = 1'
        return self.dbc.execute(stmt).fetchall()

    ## get raw data from last_updates
    def getLastUpdatedInfo(self, stype, dt=None, dateModifier=OperatorDict.EQUAL):
        stmt = 'SELECT * FROM last_updates WHERE type=? AND api IS NOT NULL'
        args = [stype.function.replace('TIME_SERIES_','')]
        if dt:
            stmt += ' AND date' + dateModifier.sqlsymbol + '? '
            args.append(dt)
        stmt += 'ORDER BY date ASC'
        return self.dbc.execute(stmt, tuple(args)).fetchall()

    ## used by collector to determine which stocks are more in need of new/updated data
    def getLastUpdatedCollectorInfo(self, exchange=None, symbol=None, type=None, api=None):
        stmt = 'SELECT s.*, u.api, u.date FROM last_updates u join symbols s on u.exchange=s.exchange and u.symbol=s.symbol'
        args = []
        adds = []
        if exchange or symbol or type:
            stmt += ' WHERE '
            adds.append('(' + ' OR '.join(['api_'+a+'=1' for a in apiList]) + ')')
            if exchange:
                adds.append('u.exchange = ?')
                args.append(exchange)
            if symbol:
                adds.append('u.symbol = ?')
                args.append(symbol)
            if type:
                adds.append('type = ?')
                args.append(type.function.replace('TIME_SERIES_',''))
            stmt += ' AND '.join(adds)

        stmt += ' ORDER BY ' + (('api_' + api + ' DESC, ') if api else '') + 'api_polygon ASC, date ASC'


        return self.dbc.execute(stmt, tuple(args))

    ## get network stats
    ## used by setManager when getting a saved data set
    def getSetInfo(self, id):
        stmt = 'SELECT changeThreshold, precedingRange, followingRange, highMax, volumeMax FROM networks WHERE id = ?'
        return self.dbc.execute(stmt, (id,)).fetchone()

    ## get all historical data for ticker and seriesType
    ## sorted date ascending
    def getStockData(self, exchange: str, symbol: str, type: SeriesType, fillGaps=False):
        stmt = 'SELECT * from historical_data WHERE exchange=? AND symbol=? AND type=? ORDER BY date'
        # return self._queryOrGetCache(stmt, (exchange, symbol, type.name), self._getHistoricalDataCount(), exchange+';'+symbol+';'+type.name)

        data = self.dbc.execute(stmt, (exchange.upper(), symbol.upper(), type.name)).fetchall()

        # if fillGaps:
        #     dateGaps = self.getDailyHistoricalGaps(exchange, symbol)
        #     gapCovers = []
        #     for g in dateGaps:
        #         ## find closest date without going over
        #         prevclose = None
        #         for d in data:
        #             if date.fromisoformat(d.date) > g: break
        #             prevclose = d.close
        #
        #         gapCovers.append(recdotdict({ 'date': g.isoformat(), 'open': prevclose, 'high': prevclose, 'low': prevclose, 'close': prevclose, 'volume': 0 }))
        #
        #
        #     data.extend(gapCovers)
        #     data.sort(key=lambda e: e.date)
        #     # for i in gapCovers: print(i)

        return data

    ## get saved data set for network
    def getDataSet(self, id, setid):
        stmt = 'SELECT * FROM data_sets WHERE network_id = ? AND network_set_id = ?'
        return self.dbc.execute(stmt, (id, setid)).fetchall()

    ## get all neural networks
    def getNetworks(self):
        stmt = 'SELECT n.*, ivf.factory, ivf.config FROM networks n JOIN input_vector_factories ivf on n.factoryId = ivf.id'
        return self.dbc.execute(stmt).fetchall()

    ## more of a helper function to fillHistoricalGaps
    def getDailyHistoricalGaps(self, exchange=None, symbol=None):
        ALL = not (exchange and symbol)
        DEBUG = False
        stmt = 'SELECT min(date) as start, max(date) as finish, exchange, symbol FROM historical_data WHERE type=? '
        tuple = (SeriesType.DAILY.name,)
        if not ALL:
            stmt += 'AND exchange=? AND symbol=? '
            tuple += (exchange, symbol)
        else:
            stmt += 'GROUP BY exchange, symbol'
        results = self.dbc.execute(stmt, tuple).fetchall()
        if DEBUG: print('result count', len(results))

        dateGaps = {} if ALL else []
        print('Determining DAILY historical gaps')
        for r in results if DEBUG else tqdm(results):
            data = self.dbc.execute('SELECT * from historical_data WHERE exchange=? AND symbol=? AND type=? ORDER BY date', (r.exchange, r.symbol, SeriesType.DAILY.name)).fetchall()
            startDate = date.fromisoformat(r.start)
            endDate = date.fromisoformat(r.finish)
            if DEBUG: print(startDate, ' -> ', endDate)

            dindex = 0
            cyear = 0
            holidays = []
            for d in range(int((endDate - startDate).total_seconds() / (60 * 60 * 24))):
                cdate = startDate + timedelta(days=d)
                if DEBUG: print('Checking', cdate)
                if cdate.weekday() > 4: # is Saturday (5) or Sunday (6)
                    if DEBUG: print('is weekend')
                    continue

                ## holiday checker
                if cyear != cdate.year:
                    holidays = getMarketHolidays(cdate.year)
                    cyear = cdate.year
                    if DEBUG: print('holidays for', cyear, holidays)
                if cdate in holidays:
                    if DEBUG: print('is holiday')
                    continue

                ## actual gap checker
                if cdate != date.fromisoformat(data[dindex].date):
                    if DEBUG: print('is gap')
                    if ALL:
                        try:
                            dateGaps[cdate].append((r.exchange, r.symbol))
                        except KeyError:
                            dateGaps[cdate] = [(r.exchange, r.symbol)]
                    else:
                        dateGaps.append(cdate)
                else:
                    dindex += 1

            #     if dindex > 30: break
            # break

        return dateGaps

    ## returns normalizationColumns, normalizationMaxes, symbolList
    def getNormalizationData(self, stype, normalizationInfo=None, exchanges=[], excludeExchanges=[], sectors=[], excludeSectors=[]):
        DEBUG = True
        normalizationColumns = ['high', 'volume']

        if normalizationInfo:
            normalizationMaxes = [normalizationInfo[x + 'Max'] for x in normalizationColumns]
        else:
            print('Getting symbols and averages')
            normalizationLists = []
            stmt = ('SELECT exchange, symbol' + ', avg({})' * len(normalizationColumns) + ' FROM historical_data WHERE type=? GROUP BY exchange, symbol').format(*normalizationColumns)
            if gconfig.testing.enabled: stmt += ' LIMIT ' + str(gconfig.testing.stockQueryLimit)

            data = self._queryOrGetCache(stmt, (stype.name,), self._getHistoricalDataCount(), 'getsandavg')

            for c in normalizationColumns:
                normalizationLists.append(
                    [x['avg(%s)' % c] for x in
                        [y for y in data if (y.exchange, y.symbol) not in testingSymbols + unusableSymbols]
                    ]
                )

            sdc = 2.5
            normalizationMaxes = []
            for i in range(len(normalizationColumns)):
                std = np.std(normalizationLists[i])
                avg = np.mean(normalizationLists[i])
                lowerlimit = max(0, avg - std * sdc)
                upperlimit = avg + std * sdc
                normalizationMaxes.append(upperlimit)

                if DEBUG:
                    print(normalizationColumns[i], '\nstd', std, '\navg', avg, '\nmax', max(normalizationLists[i]))
                    pinside = 0
                    for d in normalizationLists[i]:
                        if lowerlimit <= d and d <= upperlimit:
                            pinside += 1
                    if DEBUG: print(sdc, 'standard deviations of range will include', pinside / len(normalizationLists[i]), '% of symbols')


        ## get symbols data that meet normalization and other criteria        
        stmt = '''SELECT s.exchange, s.symbol, s.sector, s.industry, s.founded, s.asset_type, s.google_topic_id 
            FROM historical_data h JOIN symbols s'''
        stmt2 = ' ON h.exchange=s.exchange AND h.symbol=s.symbol '
        stmt3 = 'WHERE h.type=?'
        # stmt = 'SELECT * FROM historical_data h JOIN symbols s, staging_symbol_info st ON h.exchange=s.exchange AND h.symbol=s.symbol and h.exchange = st.exchange and h.symbol = st.symbol WHERE h.type=?'
        # stmt = 'SELECT h.exchange as exchange, h.symbol as symbol, s.asset_type as asset_type, s.google_topic_id as google_topic_id FROM historical_data h JOIN symbols s ON h.exchange=s.exchange AND h.symbol=s.symbol WHERE h.type=?'

        if gconfig.feature.financials.enabled and gconfig.feature.financials.dataRequired:
            stmt += ' , vwtb_edgar_quarters q'
            stmt2 += ' AND h.exchange = q.exchange AND h.symbol = q.symbol '
            stmt3 += ' AND h.exchange||h.symbol IN (SELECT DISTINCT q.exchange||q.symbol FROM vwtb_edgar_quarters q) AND REPLACE(h.date, \'-\', \'\') >= q.filed'

        if normalizationInfo or gconfig.testing.enabled:
            if gconfig.testing.enabled:
                exchanges.append(gconfig.testing.exchange)

            if exchanges:
                stmt3 += self._andXContainsListStatement('h.exchange', exchanges)
            elif excludeExchanges:
                stmt3 += self._andXContainsListStatement('h.exchange', excludeExchanges, notIn=True)

            if sectors:
                stmt3 += self._andXContainsListStatement('h.sector', sectors)
            elif excludeSectors:
                stmt3 += self._andXContainsListStatement('h.sector', excludeSectors, notIn=True)    
        else:
            if gconfig.feature.googleInterests.enabled: 
                stmt3 += 'AND s.google_topic_id IS NOT NULL'
            if gconfig.feature.companyAge.enabled and gconfig.feature.companyAge.dataRequired: 
                stmt3 += ' AND s.founded IS NOT NULL'
            if gconfig.feature.sector.enabled and gconfig.feature.sector.dataRequired:
                stmt3 += ' AND s.sector IS NOT NULL'


        tuple = (stype.name,)
        for i in range(len(normalizationColumns)):
            stmt3 += ' AND h.%s <= ? ' % normalizationColumns[i]
            tuple += (normalizationMaxes[i],)

        stmt = stmt + stmt2 + stmt3

        stmt += ' GROUP BY h.exchange, h.symbol'
        if gconfig.testing.enabled: stmt += ' LIMIT ' + str(gconfig.testing.stockQueryLimit)

        symbolList = self._queryOrGetCache(stmt, tuple, self._getHistoricalDataCount(), 'getnormsymbolist')
        # symbolList = self.dbc.execute(stmt, tuple).fetchall()

        if DEBUG and not normalizationInfo: print (len(symbolList), '/', len(normalizationLists[0]), 'are within thresholds')

        return normalizationColumns, normalizationMaxes, symbolList

    def _andXContainsListStatement(self, column, lst, notIn=False):
        return ' AND ' + column + (' not' if notIn else '') + ' in (\'' + '\',\''.join(lst) + '\')'

    ## generally one time use
    def getGoogleTopicIDsForSymbols(self):
        print('Getting topic IDs from Google')
        DEBUG = True
        gapi = GoogleAPI()
        stmt = 'UPDATE symbols SET google_topic_id=? WHERE exchange=? AND symbol=? '
        symbols = self.getSymbols(api=['alphavantage', 'polygon'], googleTopicId=-1)
        topicsFound = 0
        alreadyFound = 0
        for s in tqdm(symbols):
            if not s.google_topic_id:
                ex = s.exchange.replace(' ','')
                kw = ex + ':' + s.symbol
                topics = gapi.suggestions(kw)
                for t in topics:
                    if t['type'] == 'Topic' and t['title'] == kw:
                        self.dbc.execute(stmt, (t['mid'], s.exchange, s.symbol))
                        topicsFound += 1
            else:
                alreadyFound += 1
        if DEBUG: print(topicsFound, '/', len(symbols) - alreadyFound, 'topics found')

    def getFinancialData(self, exchange, symbol, raw=False):
        stmt = 'SELECT * FROM vwtb_edgar_financial_nums n JOIN vwtb_edgar_quarters q ON n.exchange = q.exchange AND n.symbol = q.symbol AND n.ddate = q.period WHERE n.exchange=? AND n.symbol=? ORDER BY q.period'
        res = self.dbc.execute(stmt, (exchange, symbol)).fetchall()

        return processDBQuartersToDicts(res) if not raw else res

    def getVIXData(self):
        stmt = 'SELECT * FROM cboe_volatility_index ORDER BY date'
        return self.dbc.execute(stmt).fetchall()

    def getVIXMax(self):
        stmt = 'SELECT max(high) FROM cboe_volatility_index'
        m = self.dbc.execute(stmt).fetchone()['max(high)']
        if m > 100:
            raise Exception('VIX has new max exceeding 100')
        return 100

    def getExchanges(self):
        if not self.exchanges:
            stmt = 'SELECT code FROM exchanges ORDER BY rowid'
            self.exchanges = self.dbc.execute(stmt).fetchall()
        return [r.code for r in self.exchanges]

    def getAssetTypes(self):
        if not self.assetTypes:
            stmt = 'SELECT type FROM asset_types ORDER BY rowid'
            self.assetTypes = self.dbc.execute(stmt).fetchall()
        return [r.type for r in self.assetTypes]

    def getListingDates(self, stype):
        stmt = 'SELECT exchange, symbol, min(date) FROM historical_data WHERE type=? GROUP BY exchange, symbol'
        tpl = (stype.name,)

        return self.dbc.execute(stmt, tpl).fetchall()

    def getSectors(self, asRowDict=False):
        stmt = 'SELECT * FROM sectors ORDER BY rowid'
        res = self.dbc.execute(stmt).fetchall()
        return res if asRowDict else [r['sector'] for r in res]


    ## end gets ####################################################################################################################################################################
    ####################################################################################################################################################################
    ## sets ####################################################################################################################################################################


    ## insert data in historical_data table and update the last_updates table with the API used and current date
    def insertData(self, exchange, symbol, typeName, api, data):
        ## reset caching
        self.historicalDataCount = None

        stmt = 'INSERT OR REPLACE INTO historical_data VALUES (?,?,?,?,?,?,?,?,?,?)'
        tuples = []
        for d in data:
            r = data[d]
            tuples.append((exchange, symbol, typeName, str(d), r.open, r.high, r.low, r.close, r.volume, 0))
        self.dbc.executemany(stmt, tuples)

        ## insert successful, log the updation date and api
        stmt = 'UPDATE last_updates SET date=?, api=? WHERE exchange=? AND symbol=? AND type=?'
        self.dbc.execute(stmt, (str(date.today()), api, exchange, symbol, typeName))
        # print('Data inserted and updated')

    ## save a data set used by a network
    def saveDataSet(self, id, trainingSet, validationSet, testingSet, setId=None):
        if not setId:
            stmt = 'SELECT max(network_set_id) as set_id FROM data_sets WHERE network_id = ?'
            setId = self.dbc.execute(stmt, (id,)).fetchall()[0]['set_id']
            if not setId: setId = 1
        
        # def _getSet(dset, stype):
        #     tpls = []
        #     for i in dset:
        #         h = i.handler
        #         # print('d', h.data[i.index], h.data[i.index].date)
        #         tpls.append((id, h.exchange, h.symbol, h.seriesType.name, h.data[i.index].date, setId, stype.name))
        #     return tpls

        ## save to data_sets
        # stmt = 'INSERT OR REPLACE INTO data_sets(network_id, exchange, symbol, series_type, date, network_set_id, set_type) VALUES (?,?,?,?,?,?,?)'
        # tpls = []
        # tpls.extend(_getSet(trainingSet, SetType.TRAINING))
        # tpls.extend(_getSet(validationSet, SetType.VALIDATION))
        # tpls.extend(_getSet(testingSet, SetType.TESTING))
        # print(tpls[0])

        # self.dbc.executemany(stmt, tpls)
        


        ## save data_sets and corresponding google_interests
        ds_stmt = 'INSERT OR REPLACE INTO data_sets(network_id, exchange, symbol, series_type, date, network_set_id, set_type) VALUES (?,?,?,?,?,?,?)'
        gi_stmt = 'INSERT OR REPALCE INTO google_interests(data_set_id, date, relative_interest) VALUES (?,?,?)'
        
        def _saveSet(dset, stype):
            for i in tqdm(dset, desc='Saving ' + stype.name + ' set and interests'):
                ## save to data_sets
                h = i.handler
                self.dbc.execute(ds_stmt, (id, h.symbolData.exchange, h.symbolData.symbol, h.seriesType.name, h.data[i.index].date, setId, stype.name))
                
                ## save to google_interests
                if gconfig.feature.googleInterests.enabled:
                    ds_id = self.dbc.lastrowid
                    tpls = []
                    for dt in [d.date for d in h.getPrecedingSet(i.index)]:
                        tpls.append((ds_id, dt, i.getGoogleInterestAt(dt)))
                    self.dbc.executemany(gi_stmt, tpls)
            
        # for t in SetType
        _saveSet(trainingSet, SetType.TRAINING)
        _saveSet(validationSet, SetType.VALIDATION)
        _saveSet(testingSet, SetType.TESTING)

    ## insert or update network table data
    def pushNeuralNetwork(self, nn: NeuralNetworkInstance):
        if nn.defaultInputVectorFactory:
            with open(os.path.join(path, 'managers/inputVectorFactory.py'), 'rb') as f:
                factoryblob = f.read()
            configdill = dill.dumps(nn.inputVectorFactory.config)

            ## check if factory/config combination is already present
            tpl = (factoryblob, configdill)
            res = self.dbc.execute('SELECT * FROM input_vector_factories WHERE factory=? AND config=?', tpl).fetchall()
            if len(res) > 0:
                factoryId = res[0].id
            else:
                stmt = 'INSERT OR IGNORE INTO input_vector_factories(factory, config) VALUES (?,?)'
                self.dbc.execute(stmt, tpl)
                factoryId = self.dbc.lastrowid
        else:
            factoryId = nn.stats.factoryId
        
        stmt = 'INSERT OR REPLACE INTO networks(id, factoryId, accuracyType, overallAccuracy, negativeAccuracy, positiveAccuracy, changeThreshold, precedingRange, followingRange, seriesType, highMax, volumeMax, epochs) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)'
        tpl = (nn.id,
            factoryId,
            nn.stats.accuracyType.name,
            # stats.accuracyType.name if type(stats.accuracyType) is not str else stats.accuracyType,
            nn.stats.overallAccuracy,
            nn.stats.negativeAccuracy,
            nn.stats.positiveAccuracy,
            nn.stats.changeThreshold,
            nn.stats.precedingRange,
            nn.stats.followingRange,
            nn.stats.seriesType.name,
            # stats.seriesType.name if type(stats.seriesType) is not str else stats.seriesType,
            nn.stats.highMax,
            nn.stats.volumeMax,
            nn.stats.epochs
        )
        self.dbc.execute(stmt, tpl)


    def insertVIXRow(self, row):
        stmt = 'INSERT OR REPLACE INTO cboe_volatility_index(date, open, high, low, close) VALUES (?,?,?,?,?)'
        self.dbc.execute(stmt, (*self._convertVIXDataPoint(row),))


    ## for updating symbol details like sector, industry, founded
    ## updateDetails is expected to be a dict with keys corresponding to the column names
    def updateSymbolTempInfo(self, updateDetails, infoPrefix, exchange=None, symbol=None):
        stmt = 'UPDATE staging_symbol_info SET '
        args = []


        stmt += infoPrefix + '_sector=?, '
        args.append(updateDetails['sector'] if 'sector' in updateDetails.keys() and updateDetails['sector'] != '' and updateDetails['sector'] != None else 'e')

        if 'industry' in updateDetails.keys():
            stmt += infoPrefix + '_industry=?, '
            args.append(updateDetails['industry'])
        if 'ipoDate' in updateDetails.keys():
            stmt += infoPrefix + '_ipo=?, '
            args.append(shortc(updateDetails['ipoDate'], 'e'))
        if 'isEtf' in updateDetails.keys():
            stmt += infoPrefix + '_isetf=?, '
            args.append(updateDetails['isEtf'])
        if 'assetType' in updateDetails.keys():
            stmt += infoPrefix + '_assettype=?, '
            args.append(updateDetails['assetType']) 
        if 'description' in updateDetails.keys():
            stmt += infoPrefix + '_description=?, '
            # args.append(extractDateFromDesc(updateDetails['description']))
            args.append(shortc(updateDetails['description'], 'e'))


        stmt = stmt[:-2] + ' WHERE '

        adds = []
        if exchange or symbol:
            if exchange:
                adds.append('exchange = ?')
                args.append(exchange)
            if symbol:
                adds.append('symbol = ?')
                args.append(symbol)
            stmt += ' AND '.join(adds)

        self.dbc.execute(stmt, tuple(args))

    def insertFinancials_staging_empty(self, api, exchange, symbol, ftype: FinancialReportType):
        stmt = 'INSERT INTO staging_financials(' + api + ', exchange, symbol, period, calendarDate) VALUES (?,?,?,?,?) ON CONFLICT(exchange, symbol, period, calendarDate) DO UPDATE SET ' + api + ' = 0'
        self.dbc.execute(stmt, (0, exchange, symbol, ftype.name, '1970-01-01'))

    def insertFinancials_staging_old(self, api, exchange, data: List[dict], period=None, symbol=None):
        symbolcol = 'symbol'
        periodcol = 'period'
        datecol = 'calendarDate'
        ## confirm columns are present in staging table; construct statement
        pkcolumnnames = ['exchange', symbolcol, periodcol, datecol]

        for d in data:
            # stmt = 'INSERT INTO staging_financials(exchange,'
            # tpl = [exchange]
            # stmt = 'INSERT INTO staging_financials(exchange,' + api + ','

            # tpl = [exchange, True]
            columnnames = [r[0] for r in self.dbc.execute('SELECT * FROM staging_financials').description]

            insertstmt_columnnames = []
            insertstmt_pkcolumnnames = ['exchange']
            tpl = []
            pktpl = [exchange]

            for k,v in d.items():
                if k == 'ticker': coln = symbolcol
                elif k == 'fiscalDateEnding': coln = datecol
                elif k in pkcolumnnames: coln = k
                else: coln = api + '_' + k

                if coln in pkcolumnnames:
                    insertstmt_pkcolumnnames.append(coln)
                    if coln == periodcol:
                        pktpl.append(FinancialReportType.getNameFor(v))
                    else:
                        pktpl.append(v)
                else:
                    insertstmt_columnnames.append(coln)
                    tpl.append(v)

                # if k == periodcol:
                #     tpl.append(FinancialReportType.getNameFor(v))
                # else:
                #     tpl.append(v)
                # coln = k if k in pkcolumnnames else api + '_' + k
                # coln = 'symbol' if coln == 'ticker' else coln
                
                ## confirm columns are present in staging table
                if coln not in columnnames:
                    self.dbc.execute('ALTER TABLE staging_financials ADD COLUMN ' + coln + ' TEXT')
                ## construct statement
                # stmt += coln + ','


            if period:
                insertstmt_pkcolumnnames.append(periodcol)
                pktpl.append(period)
            if symbol:
                insertstmt_pkcolumnnames.append(symbolcol)
                pktpl.append(symbol)
                

            # stmt = stmt[:-1] + ') VALUES (' + ','.join(['?' for x in tpl]) + ')'
            final_insertstmt_pkcolumnnames = [api] + insertstmt_pkcolumnnames
            final_pktpl = [True] + pktpl
            final_overall_tpl = tpl + final_pktpl

            columnsstr = ','.join(insertstmt_columnnames) + ',' + ','.join(final_insertstmt_pkcolumnnames)
            stmt = 'INSERT INTO staging_financials(' + columnsstr + ') VALUES (' + ','.join(['?' for x in final_overall_tpl]) + ')'
            stmt += ' ON CONFLICT(' + ','.join(insertstmt_pkcolumnnames) + ') DO UPDATE SET ' + api + ' = 1, ' + ','.join([ k + ' = ' + (str(v) if type(v) == int else ('\'' + v + '\'')) for k,v in zip(insertstmt_columnnames, tpl) ])

            # try:
            self.dbc.execute(stmt, tuple(final_overall_tpl))
            # except sqlite3.IntegrityError:
            #     pass

        # self.dbc.executemany(stmt, tpls)

    def insertFinancials_staging(self, api, exchange, data: List[dict], period=None, symbol=None):
        pkObj = {
            'exchange': exchange,
            'symbol': symbol,
            'period': period,
            'calendarDate': None
        }
        columnNameRemapping = {
            'ticker': 'symbol',
            'fiscalDateEnding': 'calendarDate'
        }
        pkcolumnValueRemapping = {
            'period': lambda v: FinancialReportType.getNameFor(v)
        }
        self.__insertAPIDumpData('staging_financials', pkObj, data, api, columnNameRemapping, pkcolumnValueRemapping)

    def insertDump_symbolInfo(self, data, api):
        aliasDict = self.getAliasesDictionary(api)
        pkObj = {
            'exchange': None,
            'symbol': None
        }
        columnNameRemapping = {

        }
        pkcolumnValueRemapping = {
            'exchange': lambda e: aliasDict[e]
        }
        self.__insertAPIDumpData('dump_symbol_info', pkObj, data, api, columnNameRemapping, pkcolumnValueRemapping)
       
    ## dump table should have the following columns: PRIMARY_KEY(s), API(s)
    def __insertAPIDumpData(self, table, pkObj: dict, data, api, columnNameRemapping={}, pkcolumnValueRemapping={}):
        columnNames = [r[0] for r in self.dbc.execute('SELECT * FROM ' + table).description]

        if type(data) is not List:
            data = [data]

        for d in data:
            ## put pk columns and their values if given
            insertstmt_pkcolumnNames = [k for k in pkObj.keys() if pkObj[k] is not None]
            pktpl = [v for v in pkObj.values() if v is not None]
            insertstmt_columnNames = []
            tpl = []

            for k,v in d.items():
                if k in columnNameRemapping.keys():
                    coln = columnNameRemapping[k]
                elif k in pkObj.keys():
                    coln = k
                else:
                    coln = api + '_' + k

                if coln in pkObj.keys():
                    insertstmt_pkcolumnNames.append(coln)
                    if coln in pkcolumnValueRemapping.keys():
                        pktpl.append(pkcolumnValueRemapping[coln](v))
                    else:
                        pktpl.append(v)
                else:
                    insertstmt_columnNames.append(coln)
                    if type(v) is not list:
                        if type(v) is str:
                            tpl.append(v.replace('\'', '\'\''))
                        else:
                            tpl.append(v)
                    else:
                        tpl.append(json.dumps(v))

                ## confirm columns are present in staging table
                if coln not in columnNames:
                    self.dbc.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + coln + ' TEXT')
               

            final_insertstmt_pkcolumnnames = [api] + insertstmt_pkcolumnNames
            final_pktpl = [True] + pktpl
            final_overall_tpl = tpl + final_pktpl

            
            columnsstr = ','.join(insertstmt_columnNames) + ',' + ','.join(final_insertstmt_pkcolumnnames)
            stmt = 'INSERT INTO ' + table + '(' + columnsstr + ') VALUES (' + ','.join(['?' for x in final_overall_tpl]) + ')'
            stmt += ' ON CONFLICT(' + ','.join(insertstmt_pkcolumnNames) + ') DO UPDATE SET ' + api + ' = 1, ' + ','.join([ k + ' = ' + processRawValueToInsertValue(v) for k,v in zip(insertstmt_columnNames, tpl) ])

            try:
                self.dbc.execute(stmt, tuple(final_overall_tpl))
            except sqlite3.OperationalError:
                print(stmt)
                raise sqlite3.OperationalError

    def insertEDGARFinancialDump(self, period, sub: list, tag: list, num: list, pre=None, ptype='quarter'):
        if len(sub) == 0:
            return

        sub_stmt = 'INSERT INTO dump_edgar_sub VALUES (?,?,' + ','.join(['?' for x in sub[0].keys()]) + ')'
        tag_stmt = 'INSERT INTO dump_edgar_tag VALUES (' + ','.join(['?' for x in tag[0].keys()]) + ')'
        num_stmt = 'INSERT INTO dump_edgar_num VALUES (' + ','.join(['?' for x in range(len(num[0].keys())+1)]) + ')'
        if pre:
            pre_stmt = 'INSERT INTO dump_edgar_pre VALUES (' + ','.join(['?' for x in pre[0].keys()]) + ')'
            pass


        self.commit()
        print('Inserting data...')
        try:
            self.dbc.execute('BEGIN')

            notfound = 0
            for s in tqdm(sub, desc='Submissions'):
                try:
                    ticker = self.dbc.execute('SELECT * FROM dump_symbol_info WHERE polygon_cik IN (?,?)', (s.cik, s.cik.rjust(10, '0'))).fetchall()[0]
                except IndexError as e:
                    notfound += 1
                    ticker = recdotdict({ 'exchange': None, 'symbol': None })
                self.dbc.execute(sub_stmt, tuple([ticker.exchange, ticker.symbol] + list(s.values())))

            # self.dbc.executemany(tag_stmt, [tuple(t.values()) for t in tag])
            for t in tqdm(tag, desc='Tags'):
                try:
                    self.dbc.execute(tag_stmt, tuple(t.values()))
                except sqlite3.IntegrityError:
                    # print(t)
                    # print(self.dbc.execute('SELECT * FROM dump_edgar_tag WHERE tag=? AND version=?', (t.tag, t.version)).fetchall())
                    # raise e
                    pass

            # self.dbc.executemany(num_stmt, [tuple(n.values()) for n in num])
            duplicatekey_diffnums = []
            for n in tqdm(num, desc='Numbers'):
                try:
                    self.dbc.execute(num_stmt, tuple(list(n.values()) + [False]))
                except sqlite3.IntegrityError:
                    # if n.adsh == lastadsh:
                    #     print(n)
                    #     print(self.dbc.execute('SELECT * FROM dump_edgar_num WHERE adsh=? AND tag=? AND version=? AND ddate=? AND qtrs=?', (n.adsh, n.tag, n.version, n.ddate, n.qtrs)).fetchall())

                    #     raise e
                    # else:
                    # existingkey_row = self.dbc.execute('SELECT * FROM dump_edgar_num WHERE adsh=? AND tag=? AND version=? AND coreg=? AND ddate=? AND qtrs=? AND uom=?', (n.adsh, n.tag, n.version, n.coreg, n.ddate, n.qtrs, n.uom)).fetchall()[0]
                    # if existingkey_row.value != n.value:
                    #     duplicatekey_diffnums.append(n)
                    self.dbc.execute(num_stmt, tuple(list(n.values()) + [True]))
                    
                
            if pre: self.dbc.executemany(pre_stmt, [tuple(p.values()) for p in pre])

            print(len(sub)-notfound, '/', len(sub), 'cik found in tickers')
            # raise 'test'
            # if len(duplicatekey_diffnums) > 0:
            #     print('Duplicate nums')
            #     for n in duplicatekey_diffnums:
            #         print(n)

            self.dbc.execute('INSERT INTO dump_edgar_loaded VALUES (?,?)', (ptype, period))

            self.dbc.execute('COMMIT')
            
                
        except Exception as e:
            print('Transaction error', e)
            self.dbc.execute('ROLLBACK')
            raise e

    ## end sets ####################################################################################################################################################################
    ####################################################################################################################################################################
    ## deletes ####################################################################################################################################################################
       
    def deleteNetworks(self, exclude=[], dryRun=True):
        networkIds = [str(x.id) for x in self.getNetworks()]
        exclude = [str(x) for x in exclude] if type(exclude) is list else [str(exclude)]
        for x in exclude:
            networkIds.remove(str(x))

        for root, dirs, files in os.walk(os.path.join(path, 'data\\network_saves')):
            for dir in dirs:
                if dir == 'assets' or dir == 'variables': continue
                ## cleanup any orphaned network saves too
                if dir in networkIds:
                    print('Deleting network', dir)
                    if not dryRun: shutil.rmtree(os.path.join(root, dir))
                elif dir not in networkIds and dir not in exclude:
                    print('Deleting orphaned network', dir)
                    if not dryRun: shutil.rmtree(os.path.join(root, dir))
        
        stmt = 'DELETE FROM networks'
        if exclude:
            stmt += ' WHERE id IN ('
            stmt += ','.join(networkIds)
            stmt += ')'

        if not dryRun: self.dbc.execute(stmt)
        else: print('Executing SQL', stmt)
        
        ## todo cleanup data_sets table, ON DELETE CASCADE not working?
            

    def deleteNeuralNetwork(self, id):
        # stmt = 'DELETE FROM google_interests WHERE network_id = ?'
        # self.dbc.execute(stmt, (id,))

        # stmt = 'DELETE FROM data_sets WHERE network_id = ?'
        # self.dbc.execute(stmt, (id,))

        ## SQL cascade should handle deletion
        stmt = 'DELETE FROM networks WHERE id = ?'
        self.dbc.execute(stmt, (id,))



    ## end deletes ####################################################################################################################################################################
    ####################################################################################################################################################################
    ## migrations ####################################################################################################################################################################
    

    def _condenseFoundedTuples(self):
        symlist = self.getStagedSymbolRows()
        tpls = []
        for s in symlist:
            # if s.founded: continue

            DEBUG = False
            desclist = []
            for a in apiList:
                d = s[a+'_description']
                if d: desclist.append(d)
            
            if DEBUG: print(desclist)
            if len(desclist) > 0:
                flist = []
                for d in desclist:
                    td = extractDateFromDesc(d)
                    # if len(td) < 20:
                    # if td and len(td) < 20 and re.search(r'd+', td):
                    if td:
                        flist.append(td)
                
                
                if DEBUG: print(flist)
                if len(flist) > 0:
                    samef = True
                    tf = flist[0]
                    for f in flist:
                        if f != tf: samef = False

                    if not samef:
                        print('Mismatch found', flist, s.exchange, s.symbol)
                    else:
                        # print('Writing founded', tf, s.exchange, s.symbol)
                        # if s.founded and s.founded != tf: print('fixing date', s.founded, '->', tf, '  ', s.exchange, s.symbol)
                        # self.dbc.execute('UPDATE staging_symbol_info SET founded=? WHERE exchange=? AND symbol=?', (tf, s.exchange, s.symbol))
                        tpls.append((tf, s.exchange, s.symbol))
                else:
                    # print('Unable to determine a date', s.exchange, s.symbol)
                    pass
        

        return tpls

    def _condenseSectorTuples(self):
        stmt = 'SELECT * FROM staging_symbol_info WHERE fmp_sector IS NOT NULL AND polygon_sector IS NOT NULL AND alphavantage_sector IS NOT NULL AND migrated=0'
        symbolList = self.dbc.execute(stmt).fetchall()
        sectorList = self.getSectors()

        print('Checking', len(symbolList), 'symbols in staging')
        print(sectorList)

        tpls = []
        mismatchc = 0
        for s in symbolList:
            valids = []
            for a in apiList:
                sct = s[a+'_sector']
                if sct == '': continue
                if sct in sectorList:
                    valids.append(sct)

            if len(valids) == 0: continue
            elif len(valids) == 1 or (len(valids) == 2 and valids[0] == valids[1]) or (len(valids) == 3 and valids[0] == valids[1] and valids[0] == valids[2]):
                tpls.append((valids[0], s.exchange, s.symbol))
            else:
                # print('Mismatch:', s.exchange, s.symbol, valids)
                mismatchc += 1

        print(mismatchc, 'mismatches')
        print('Migrating', len(tpls))

        return tpls


    def staging_condenseIPO(self):
        apilist = ['polygon', 'fmp']
        symlist = self.getStagedSymbolRows()
        for s in symlist:
            if s.ipo: continue

            DEBUG = False
            ipolist = []
            for a in apilist:
                i = s[a+'_ipo']
                if i and i != 'e' and i != 'x': ipolist.append(i)
            
            ipolist.sort()

            if DEBUG: print(ipolist)
            if len(ipolist) > 0:
                samei = True
                ti = ipolist[0]
                for i in ipolist:
                    if i != ti: samei = False

                if not samei:
                    data = self.getStockData(s.exchange, s.symbol, SeriesType.DAILY)

                    if len(data) > 0:
                        print('Mismatch found', ipolist, s.exchange, s.symbol)
                        earliestdate = date.fromisoformat(data[0].date)
                        ipodates = [date.fromisoformat(d) for d in ipolist]

                        resultdate = None
                        if earliestdate < ipodates[0]:
                            resultdate = earliestdate
                            print('Writing ipo using data', resultdate, s.exchange, s.symbol)
                        else:
                            for ic in range(len(ipodates)):
                                i = ipodates[ic]

                                if i <= earliestdate:
                                    if ic == 0:
                                        resultdate = i
                                    else:
                                        try:
                                            if (date.today() - i).years > 19:
                                                print('ipo too old to determine', i.isoformat())
                                                resultdate = None
                                                break
                                        except AttributeError:
                                            pass

                            if resultdate:
                                print('Writing ipo using overview', resultdate, s.exchange, s.symbol)
                                pass
                            else:
                                print('Unable to determine correct ipo date')
                    else:
                        # print('No historical data to check')
                        pass

                else:
                    # print('Writing ipo', ti, s.exchange, s.symbol)
                    # self.dbc.execute('UPDATE staging_symbol_info SET ipo=? WHERE exchange=? AND symbol=?', (ti, s.exchange, s.symbol))
                    pass
            else:
                ## no ipo
                pass

    def staging_condenseFounded(self):
        tpls = self._condenseFoundedTuples()

        self.dbc.executemany('UPDATE staging_symbol_info SET founded=? WHERE exchange=? AND symbol=?', tpls)

    def staging_condenseSector(self):
        tpls = self._condenseSectorTuples()
        self.dbc.executemany('UPDATE staging_symbol_info SET sector=? WHERE exchange=? AND symbol=?', tpls)


    def symbols_pullStagedSector(self):
        tpls = self._condenseSectorTuples()

        print('Moving', len(tpls), 'sector items')

        ## transfer info
        self.dbc.executemany('UPDATE symbols SET sector=? WHERE exchange=? AND symbol=?', tpls)
        # self.dbc.executemany('UPDATE staging_symbol_info SET migrated=1 WHERE migrated <> ? AND exchange=? and symbol=?', tpls)

    def symbols_pullStagedFounded(self):
        tpls = self._condenseFoundedTuples()

        print('Moving', len(tpls), 'founded items')

        ## transfer info
        self.dbc.executemany('UPDATE symbols SET founded=? WHERE exchange=? AND symbol=?', tpls)
        # self.dbc.executemany('UPDATE staging_symbol_info SET migrated=1 WHERE migrated <> ? AND exchange=? and symbol=?', tpls)        


    ## end migrations ####################################################################################################################################################################
    ####################################################################################################################################################################
    ## limited use utility ####################################################################################################################################################################

    ## generally only used after VIX update dumps
    ## fill any data gaps with artificial data using last real trading day
    def fillVIXHistoricalGaps(self, dryrun=False):
        DEBUG = True
        ## get date range
        stmt = 'SELECT min(date) as start, max(date) as finish FROM cboe_volatility_index'
        res = self.dbc.execute(stmt).fetchone()
        startDate = date.fromisoformat(res.start)
        endDate = date.fromisoformat(res.finish)
        if DEBUG: print(startDate, ' -> ', endDate)

        ## get vix data
        stmt = 'SELECT date, close FROM cboe_volatility_index ORDER BY date'
        data = self.dbc.execute(stmt).fetchall()

        ## fill gaps
        stmt = 'INSERT OR IGNORE INTO cboe_volatility_index VALUES (?,?,?,?,?,?)'
        prevclose = 0
        dindex = 0
        cyear = 0
        holidays = []
        DEBUG = False
        gapsFilled = 0
        for d in range(int((endDate - startDate).total_seconds() / (60 * 60 * 24))):
            cdate = startDate + timedelta(days=d)
            if DEBUG: print('Checking', cdate)
            if cdate.weekday() > 4: # is Saturday (5) or Sunday (6)
                if DEBUG: print('is weekend')
                continue

            ## holiday checker
            if cyear != cdate.year:
                holidays = getMarketHolidays(cdate.year)
                cyear = cdate.year
                if DEBUG: print('holidays for', cyear, holidays)
            if cdate in holidays:
                if DEBUG: print('is holiday')
                continue

            ## actual gap checker
            if cdate != date.fromisoformat(data[dindex].date):
                # print(cdate.weekday(), cdate in holidays)
                if not dryrun: 
                    self.dbc.execute(stmt, (str(cdate), prevclose, prevclose, prevclose, prevclose, True))
                else: 
                    print(str(cdate), prevclose)
                gapsFilled += 1
                # if debugcount > 20: break
                pass
            else:
                prevclose = data[dindex].close
                dindex += 1
        
        print(gapsFilled, 'gaps filled')

    ## generally only used after large data acquisitions/dumps
    ## fill any data gaps (generally daily) with artificial data using last real trading day
    def fillHistoricalGaps(self, exchange=None, symbol=None, type=SeriesType.DAILY, dryrun=False):
        ## reset caching
        self.historicalDataCount = None

        ALL = not (exchange and symbol)
        stmt = 'INSERT OR REPLACE INTO historical_data VALUES (?,?,?,?,?,?,?,?,?,?)'
        tuples = []
        gaps = []
        if type == SeriesType.DAILY:
            gaps = self.getDailyHistoricalGaps(exchange, symbol)

        print('Filling historical gaps for', type)
        for g in tqdm(gaps):
        # for g in trange(gaps):
            # for t in gaps[g] if ALL else [(exchange, symbol)]:
            for t in tqdm(gaps[g], desc=str(g), leave=False) if ALL else [(exchange, symbol)]:
                ## find closest date without going over
                prevclose = None
                for d in self.getStockData(t[0], t[1], type):
                    if date.fromisoformat(d.date) > g: break
                    prevclose = d.close
                tuples.append((t[0], t[1], type.name, str(g), prevclose, prevclose, prevclose, prevclose, 0, True))

        print('Writing gap fillers to database')
        if not dryrun: 
            self.dbc.executemany(stmt, tuples)
        else:
            for t in tuples:
                print(t)


    ## one time use
    def loadVIXArchive(self, filepath):
        ## load data from xls
        xlsheet = xlrd.open_workbook(filepath).sheet_by_name('OHLC')

        # read header values into the list    
        keys = [xlsheet.cell(1, col_index).value for col_index in range(xlsheet.ncols)]

        drows = []
        for row_index in range(2, xlsheet.nrows):
            # d = {keys[col_index]: xlsheet.cell(row_index, col_index).value 
            #     for col_index in range(xlsheet.ncols)}
            # year, month, day, *rem = xlrd.xldate_as_tuple(d['Date'], 0)
            # d['Date'] = date(year, month, day).isoformat()
            # for k in d:
            #     if k == 'Date': continue
            #     d[k] = d[k] if d[k] != 'n/a' else 0
            self.insertVIXRow([xlsheet.cell(row_index, col_index).value for col_index in range(xlsheet.ncols)])


    def checkAvailabilitySplit(self, seriesType, precedingRange, followingRange, threshold):
        totalcount = 0
        matchcountE = 0
        matchcountS = 0
        matchSpread = {x: 0 for x in range(101)}
        tickers = self.dbc.execute('SELECT DISTINCT exchange, symbol FROM historical_data').fetchall()
        for t in tqdm(tickers):
            data = self.dbc.execute('SELECT * FROM historical_data WHERE exchange=? AND symbol=? AND type=?', (t.exchange, t.symbol, seriesType.name)).fetchall()
            if len(data) < precedingRange + followingRange + 1:
                continue
            data = data[precedingRange-1:]

            for d in range(1, len(data) - followingRange):
                try:
                    inc = 1 - (data[d + followingRange].low / data[d-1].high)
                    if inc < 0:
                        inc = 0
                    else:
                        inc = math.floor(inc*100)
                    matchSpread[inc] += 1
                except ZeroDivisionError:
                    pass
                # ## enddate exceed
                # try:
                #     if 1 - (data[d + followingRange].low / data[d-1].high) > threshold:
                #         matchcountE += 1
                # except ZeroDivisionError:
                #     pass
                # ## sometime exceed
                # for ds in range(1, followingRange):
                #     try:
                #         if 1 - (data[d+ds].high / data[d-1].high) > threshold:
                #             matchcountS += 1
                #             break
                #     except ZeroDivisionError:
                #         pass

                totalcount += 1

        print(totalcount, 'possibilities')
        # print(matchcountE, 'exceeding threshold of', threshold, 'by day', followingRange)
        # print(matchcountS, 'exceeding threshold of', threshold, 'sometime within the following', followingRange, 'days')
        for k in range(len(matchSpread)-1, 0, -1):
            matchSpread[k-1] += matchSpread[k]
        for k in matchSpread:
            print(matchSpread[k], 'exceeding threshold of', k/100, 'representing', round(matchSpread[k] / totalcount * 100, 4), '% of possibilites')

    def pushDefaultInputVectorFactory(self):
        with open(os.path.join(path, 'managers/inputVectorFactory.py'), 'rb') as f:
            blob = f.read()
        cnf = dill.dumps(gconfig)

        stmt = 'INSERT OR REPLACE INTO input_vector_factories VALUES (?,?,?)'
        self.dbc.execute(stmt, (1, blob, cnf))
        print(d.dbc.lastrowid)     

    # def printTableColumns(self, tablename):
    #      columnnames = [r[0] for r in self.dbc.execute('SELECT * FROM ' + tablename).description]
    #      for c in columnnames:
    #          print(c)

    ## end limited use utility ####################################################################################################################################################################
    ####################################################################################################################################################################
    




def printSectorColumnInfos(d: DatabaseManager):
    ## compare sectors from temp table
    stmt = 'SELECT DISTINCT {}_sector FROM staging_symbol_info ORDER BY 1'
    # ds_fmp = [d['fmp_sector'] for d in d.dbc.execute(stmt.format('fmp')).fetchall()]
    # ds_polygon = [d['polygon_sector'] for d in d.dbc.execute(stmt.format('polygon')).fetchall()]
    # ds_alphavantage = [d['alphavantage_sector'] for d in d.dbc.execute(stmt.format('alphavantage')).fetchall()]
    # dss = [ds_fmp, ds_polygon, ds_alphavantage]
    dss = []
    for a in apiList:
        dss.append([d[a + '_sector'] for d in d.dbc.execute(stmt.format(a)).fetchall()])


    for l in dss:
        try:
            l.remove(None)
        except ValueError:
            pass
        try:
            l.remove('')
        except ValueError:
            pass

    ## get counts
    stmt = 'SELECT count(*) as count FROM staging_symbol_info WHERE {}_sector=?'
    counts = []
    for ac in range(len(apiList)):
        dcl = []
        for dc in dss[ac]:
            dcl.append(d.dbc.execute(stmt.format(apiList[ac]), (dc,)).fetchone()['count'])
        counts.append(dcl)


    ## print real pretty
    fmpc = 0
    polygonc = 0
    alphavantagec = 0
    ac = [fmpc, polygonc, alphavantagec]
    rowstr = '{: <8} {: <30} {: <8} {: <30} {: <8} {: <30}'
    print(rowstr.format('count', 'fmp', 'count', 'polygon', 'count', 'alphavantage'))
    while True:
        primary = [0]
        try:
            if dss[0][ac[0]] == dss[1][ac[1]]:
                primary.append(1)
            elif dss[0][ac[0]] > dss[1][ac[1]]:
                primary = [1]

            if dss[primary[0]][ac[primary[0]]] == dss[2][ac[2]]:
                primary.append(2)
            elif dss[primary[0]][ac[primary[0]]] > dss[2][ac[2]]:
                primary = [2]
        except IndexError:
            break


        print(rowstr.format(
            counts[0][ac[0]] if 0 in primary else 0,
            dss[0][ac[0]] if 0 in primary else '',
            counts[1][ac[1]] if 1 in primary else 0,
            dss[1][ac[1]] if 1 in primary else '',
            counts[2][ac[2]] if 2 in primary else 0,
            dss[2][ac[2]] if 2 in primary else '',
        ))

        for i in primary:
            ac[i] += 1

    print(rowstr.format(len(dss[0]), '', len(dss[1]), '', len(dss[2]), ''))

if __name__ == '__main__':
    d: DatabaseManager = DatabaseManager()
    # res = d.getDailyHistoricalGaps()
    # res = d.getDailyHistoricalGaps('BATS','AVDR')
    # for r in res:
    #     try:
    #         print(r, len(res[r]), res[r])
    #     except:
    #         print(res)
    #         break

    # print(d.getDailyHistoricalGaps('BATS','ACES'))
    # data = d.getStockData('BATS', 'AVDR', SeriesType.DAILY, True)
    # for d in data: print(d)

    # d.fillHistoricalGaps(exchange='BATS', symbol='ACES', type=SeriesType.DAILY)
    # d.fillHistoricalGaps(type=SeriesType.DAILY)

    # addLastUpdatesRowsForAllSymbols(d.dbc)
    # d.addAPI('polygon')
    # print(d.getSymbols(api='alphavantage').fetchone()['api_alphavantage'])

    # d.getNormalizationData(SeriesType.DAILY)
    # d.getGoogleTopicIDsForSymbols()

    # d.pushNeuralNetwork('1615006455', recdotdict({
    #     'changeThreshold': 0.1, 
    #     'precedingRange': 52, 
    #     'followingRange': 4, 
    #     'highMax': 125.86740668907949, 
    #     'volumeMax': 4300572.902793559, 
    #     'accuracyType': AccuracyType.OVERALL, 
    #     'overallAccuracy': 0.9926470518112183, 
    #     'negativeAccuracy': 1.0, 
    #     'positiveAccuracy': 0.0, 
    #     'epochs': 5}))


    # d.loadVIXArchive(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw/vixarchive.xls'))

    # print(d.getDailyHistoricalGaps('NYSE', 'AA'))
    # print(getMarketHolidays(2012))
    # d.fillHistoricalGaps(type=SeriesType.DAILY)
    # d.fillVIXHistoricalGaps()
    # d.fillHistoricalGaps(type=SeriesType.DAILY, dryrun=True)
    # d.fillVIXHistoricalGaps(dryrun=True)

    ## get insert statements for vix table refresh
    # data = d.dbc.execute('SELECT * FROM cboe_volatility_index')
    # for i in data:
    #     print('INSERT INTO cboe_volatility_index(date, open, high, low, close) values (\"'+str(i.date)+'\",'+str(i.open)+','+str(i.high)+','+str(i.low)+','+str(i.close)+');')

    # print(d.getAssetTypes())
    # d.checkAvailabilitySplit(SeriesType.DAILY, 200, 20, 0.2)


    ## migrate sector/industry data and symbols to temp table
    # si = d.getSymbols()
    # for s in si:
    #     d.dbc.execute(
    #         'INSERT OR REPLACE INTO staging_symbol_info(exchange, symbol, pg_sector, pg_industry) VALUES (?,?,?,?)',
    #         (s.exchange, s.symbol, 
    #             s.sector if s.sector else None, 
    #             s.industry if s.industry else None
    #         )
    #     )
    # d.addAPI('fmp')


    # printSectorColumnInfos(d)

    # d.staging_condenseFounded()
    # d.staging_condenseIPO()
    # d.staging_condenseSector()

    # d.symbols_pullStagedSector()
    # d.symbols_pullStagedFounded()

    # d.pushDefaultInputVectorFactory()

    # d.deleteNetworks(exclude=[1622952945])
    # d.deleteNetworks(dryRun=False)

    # print(d.getSymbols_forFinancialStaging('alphavantage'))
    
    
    

    # print(d.printTableColumns('staging_financials'))
    

    # ## staging financials stuff
    # rows = d.dbc.execute('SELECT * FROM staging_financials WHERE polygon = 1 AND alphavantage = 1 AND period = \'QUARTER\'').fetchall()
    
    # ## print example row with column names
    # # for k,v in rows[0].items():
    # #     print(k, v)

    # ## print specific row
    # for r in rows:
    #     # if r.symbol == 'AAL' and r.calendarDate == '2018-09-30':
    #     if r.symbol !='ACHC' and r.polygon_investments != r.polygon_investmentsCurrent:
    #         for k,v in r.items():
    #             print(k,v)

    # ## check intergrity of staging_financials
    # pairs = [
    #     ('alphavantage_operatingIncome', 'polygon_operatingIncome'),
    #     ('alphavantage_interestExpense', 'polygon_interestExpense'),
    #     ('alphavantage_incomeBeforeTax', 'polygon_earningsBeforeTax'),
    #     ('alphavantage_incomeTaxExpense', 'polygon_incomeTaxExpense'),

    #     ('alphavantage_nonInterestIncome', 'polygon_revenues'),

    #     # ('alphavantage_netIncomeFromContinuingOperations', 'fmp'),
    #     ('alphavantage_netIncome', 'fmp'),
    #     ('fmp', 'polygon_consolidatedIncome'),
    #     ('fmp', 'polygon_netIncome'),
    #     ('fmp', 'polygon_netIncomeCommonStock'),
    #     ('fmp', 'polygon_netIncomeCommonStockUSD'),

        
    #     ('alphavantage_ebit', 'fmp'),
    #     ('fmp', 'polygon_earningBeforeInterestTaxes'),
    #     # ('fmp', 'polygon_earningsBeforeInterestTaxesDepreciationAmortization'),
    #     # ('fmp', 'polygon_earningsBeforeInterestTaxesDepreciationAmortizationUSD'),
    #     ('fmp', 'polygon_earningBeforeInterestTaxesUSD')
    # ]

    # c=0
    # for r in rows:
    #     print(r.exchange, r.symbol, r.period, r.calendarDate)
    #     for c1,c2 in pairs:
    #         print(c1,c2)
    #         print(r[c1], r[c2])
    #     print()
    #     c += 1
    #     if c > 6: break


    print(d.getFinancialData('BATS','CBOE'))


    pass

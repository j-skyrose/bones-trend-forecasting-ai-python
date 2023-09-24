import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import math, re, dill, operator, shutil, json, time, pickle
from typing import Dict, List, Union
import sqlite3, atexit, numpy as np, xlrd
from datetime import date, timedelta, datetime
from tqdm import tqdm
from multiprocessing import current_process
from decimal import Decimal
from enum import Enum

from managers.dbCacheManager import DBCacheManager
from structures.api.googleTrends.request import GoogleAPI

from globalConfig import config as gconfig
from managers.configManager import StaticConfigManager
from managers.marketDayManager import MarketDayManager
from constants.enums import APIState, AccuracyAnalysisTypes, CorrBool, EarningsCollectionAPI, FinancialReportType, IndicatorType, InterestType, NormalizationGroupings, OperatorDict, OutputClass, PrecedingRangeType, SQLHelpers, SQLInsertHelpers, SeriesType, AccuracyType, SetType, Direction
from structures.normalizationColumnObj import NormalizationColumnObj
from structures.normalizationDataHandler import NormalizationDataHandler
from structures.sqlArgumentObj import SQLArgumentObj
from utils.support import asDate, asISOFormat, asList, convertToCamelCase, convertToSnakeCase, flatten, generateCommaSeparatedQuestionMarkString, recdotdict_factory, processDBQuartersToDicts, processRawValueToInsertValue, recdotdict, Singleton, extractDateFromDesc, recdotlist, recdotobj, shortc, shortcdict, tqdmLoopHandleWrapper, unixToDatetime
from utils.other import buildCommaSeparatedTickerPairString, generateSQLAdditionalStatementAndArguments, parseCommandLineOptions
from constants.values import unusableSymbols, apiList, standardExchanges

configManager: StaticConfigManager = StaticConfigManager()

def _getDBHandles(dbpath, row_factory=recdotdict_factory):
    dbconnect = sqlite3.connect(dbpath, timeout=15)
    dbconnect.row_factory = row_factory
    return dbconnect, dbconnect.cursor()

def _attachDB(dbc: sqlite3.Cursor, dbpath, alias):
    dbc.execute(f'ATTACH ? AS {alias}', (dbpath,))

## auto-generate a file full of annotation objects for the rows of each table in the database: _generatedDatabaseAnnotations/databaseRowObjects.py
def _generateDatabaseAnnotationObjectsFile(propertiesDatabasePath=None, computedDatabasePath=None, dumpDatabasePath=None):
    connect, dbc = _getDBHandles(shortc(propertiesDatabasePath, configManager.get('propertiesdatabase', required=True)))
    computedDBAlias = 'computeddbalias'
    _attachDB(dbc, shortc(computedDatabasePath, configManager.get('computeddatabase', required=True)), computedDBAlias)
    dumpDBAlias = 'dumpdb'
    _attachDB(dbc, shortc(dumpDatabasePath, configManager.get('dumpdatabase', required=True)), dumpDBAlias)

    def __generateArgTypeString(cname, t):
        if t in ['TEXT', 'STRING']: return ': str'
        elif t in ['', 'NUMERIC', 'INTEGER'] and cname in ['artificial', 'migrated', 'fmp_isetf', 'duplicate', 'wksi', 'prevrpt', 'detail', 'custom', 'abstract', 'tradeable', 'crypto_tradeable']: return ': bool'
        elif t in ['REAL', 'BIGDOUBLE', 'NUMERIC']: return ': float'
        elif t in ['NUM', 'NUMBER', 'INTEGER', 'INT', 'BIGINT']: return ': int'
        elif t in ['BYTE', 'BLOB']: return ': bytes'
        elif t in ['DATETIME']: return ': datetime'
        return ''

    filestring = 'from datetime import datetime\n\n'
    for dbalias, tables in [(dbalias, [r.tbl_name for r in dbc.execute(f'SELECT * FROM {dbalias}.sqlite_master WHERE type=?', ('table',)).fetchall()]) for dbalias in ['main', computedDBAlias, dumpDBAlias]]:
        for t in tables:
            columns = dbc.execute(f'PRAGMA {dbalias}.table_info({t})').fetchall()


            commaSeparatedSnakeCaseColumnNames = ', '.join([f"'{c['name']}'" for c in columns])
            commaSeparatedCamelCaseColumnNames = ', '.join([f"'{convertToCamelCase(c['name'])}'" for c in columns])

            initargsList = []
            initfuncString = ''
            for c in columns:
                cname = convertToCamelCase(c.name)
                initargsList.append(f"{cname}Value{__generateArgTypeString(c['name'], c['type'])}")
                initfuncString += f'\t\tself.{cname} = {cname}Value\n'

            filestring += f'## TABLE: {t} ######################################\n'
            filestring += f'{convertToCamelCase(t)}SnakeCaseTableColumns = [{commaSeparatedSnakeCaseColumnNames}]\n'
            filestring += f'{convertToCamelCase(t)}CamelCaseTableColumns = [{commaSeparatedCamelCaseColumnNames}]\n'
            filestring += f'class {convertToCamelCase(t, firstCapital=True)}Row():\n'
            filestring += f"\tdef __init__(self, {', '.join(initargsList)}):\n"
            filestring += initfuncString
            filestring += '\n'

    with open(os.path.join(path, 'managers', '_generatedDatabaseAnnotations', 'databaseRowObjects.py'), 'w') as f:
        f.write(filestring)

    connect.close()

## generate before import to ensure things are up-to-date for the current execution
_generateDatabaseAnnotationObjectsFile()
from managers._generatedDatabaseAnnotations.databaseRowObjects import AccuracyLastUpdatesRow, CboeVolatilityIndexRow, HistoricalDataRow, StagingSymbolInfoDRow, StockSplitsPolygonDRow, VectorSimilaritiesCRow, NetworkAccuraciesRow, NetworksRow, SymbolsRow, symbolsSnakeCaseTableColumns, historicalDataSnakeCaseTableColumns, earningsDatesNasdaqDCamelCaseTableColumns, earningsDatesMarketwatchDCamelCaseTableColumns, earningsDatesYahooDCamelCaseTableColumns, symbolStatisticsYahooDCamelCaseTableColumns, shortInterestFinraDCamelCaseTableColumns

class DatabaseManager(Singleton):

    def init(self, propertiesDatabasePath=None, computedDatabasePath=None, dumpDatabasePath=None):
        atexit.register(self.close)
        self.connect, self.dbc = _getDBHandles(shortc(propertiesDatabasePath, configManager.get('propertiesdatabase', required=True)))

        self.computedDBAlias = 'computeddbalias'
        _attachDB(self.dbc, shortc(computedDatabasePath, configManager.get('computeddatabase', required=True)), self.computedDBAlias)
        self.dumpDBAlias = 'dumpdbalias'
        _attachDB(self.dbc, shortc(dumpDatabasePath, configManager.get('dumpdatabase', required=True)), self.dumpDBAlias)

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

    ## for SQL transactions
    def startBatch(self): 
        self.commit()
        self.dbc.execute('BEGIN')
    def commitBatch(self): self.dbc.execute('COMMIT')
    def rollbackBatch(self): self.dbc.execute('ROLLBACK')

    def _resetCachedHistoricalDataCount(self):
        self.historicalDataCount = None

    def _getHistoricalDataCount(self):
        if not self.historicalDataCount:
            self.historicalDataCount = self.getMaxRowID('historical_data')
        return self.historicalDataCount

    def _queryOrGetCache(self, query, qarg, validationObj, tag):
        print('qorc', query)
        cache = self.cacheManager.get(query, validationObj)
        if cache: 
            print('got cache')
            data = cache
        else: 
            print('no cache, executing')
            data = self.dbc.execute(query, qarg).fetchall()
            self.cacheManager.add(tag, query, validationObj, data)
        return data

    def _convertVIXDataPoint(self, data: List):
        if '/' in str(data[0]):
            data[0] = datetime.strptime(data[0], "%m/%d/%Y").date().isoformat()
        else:
            year, month, day, *rem = xlrd.xldate_as_tuple(data[0], 0)
            data[0] = date(year, month, day).isoformat()
        for i in range (1, 5):
            data[i] = data[i] if data[i] != 'n/a' else 0
        data.append(False) ## artificial
        return data

    def __purgeUnusableTickers(self, data, raw=False, **kwargs):
        if raw: return data
        return [d for d in data if (d.exchange, d.symbol) not in unusableSymbols]
    
    def _getDBAliasForTable(self, tablename: str):
        if tablename.endswith('_d'): return self.dumpDBAlias
        elif tablename.endswith('_c'): return self.computedDBAlias
        return 'main'

    ####################################################################################################################################################################
    ## gets ####################################################################################################################################################################

    def getTableString(self, table) -> str:
        return f'{self._getDBAliasForTable(table)}.{table}'
    
    def getMaxRowID(self, table='google_interests_d') -> int:
        return self.dbc.execute(f'SELECT MAX(rowid) FROM {self.getTableString(table)}').fetchone()['MAX(rowid)']



    def getLoadedQuarters(self):
        qrts = self.dbc.execute(f'SELECT period FROM {self.getTableString("financial_stmts_loaded_periods_d")} WHERE type=\'quarter\'').fetchall()
        return [q.period for q in qrts]

    def getAliasesDictionary(self, api=None):
        ret = {}
        for r in self.dbc.execute(f'SELECT exchange, alias FROM exchange_aliases {"WHERE api=?" if api else ""}', (api,) if api else []).fetchall():
            ret[r['alias']] = r['exchange']
            ret[r['exchange']] = r['exchange']
        return recdotdict(ret)

    ## get data from symbols table
    def getSymbols(self,
                   ## symbols table
                   exchange=None, symbol=None, name=None, assetType=None, api=None, googleTopicId=None, sector=None, industry=None, founded=None,
                   ## historical data table
                   seriesType: SeriesType=None, periodDate=None, open=None, high=None, low=None, close=None, volume=None, artificial=None,
                   ## other
                   requireEarningsDates=None, normalizationData=None, rawStmt=False, **_) -> List[SymbolsRow]:
        kwargs = {}
        for k,v in locals().items():
            k = convertToSnakeCase(k)
            if (k in symbolsSnakeCaseTableColumns + historicalDataSnakeCaseTableColumns or k == 'api') and v is not None:
                kwargs[k] = v

        stmt = 'SELECT * FROM symbols s '
        adds = []
        args = []
        includingHistorical = False
        ## check if any arguments are for the historical data table
        onlyHistoricalDataSnakeCaseTableColumns = list(set(historicalDataSnakeCaseTableColumns) - set(symbolsSnakeCaseTableColumns))
        if any(c in onlyHistoricalDataSnakeCaseTableColumns for c in kwargs.keys()) or (normalizationData and len(normalizationData.get(NormalizationGroupings.HISTORICAL, orNone=True)) > 0):
            includingHistorical = True
            stmt += ' JOIN historical_data h ON s.exchange=h.exchange AND s.symbol=h.symbol '

        ## add all column-keyword args to the query
        for argKey, argVal in kwargs.items():
            if argKey == 'api':
                if type(argVal) is list:
                    apiAdds = []
                    for a in argVal:
                        apiAdds.append(f's.api_{a} = 1')
                    adds.append(f'( {" OR ".join(apiAdds)} )')
                else:
                    adds.append(f's.api_{api} = 1')
            else:
                col = 's'
                if argKey in onlyHistoricalDataSnakeCaseTableColumns:
                    col = 'h'
                col += f'.{argKey}'

                if type(argVal) == SQLHelpers:
                    adds.append(f' {col} is {argVal.value} ')
                elif type(argVal) == SQLArgumentObj:
                    argVal: SQLArgumentObj
                    adds.append(f' ? {argVal.modifier.sqlsymbol} {col} ')
                    args.append(argVal.value)
                else:
                    if issubclass(argVal.__class__, Enum): argVal = argVal.name
                    vlist = asList(argVal)
                    adds.append(f' {col} in ({",".join(["?" for x in range(len(vlist))])}) ')
                    args.extend(vlist)

        ## add normalization args to query
        if normalizationData:
            nc: NormalizationColumnObj
            for nc in normalizationData:
                if nc.normalizationGrouping in [NormalizationGroupings.HISTORICAL, NormalizationGroupings.STOCK]:
                    adds.append(f' ? {OperatorDict.LESSTHANOREQUAL.sqlsymbol} h.{nc.columnName} ')
                    args.append(nc.value)

        if requireEarningsDates:
            adds.append(f's.exchange||s.symbol IN (SELECT DISTINCT exchange||symbol FROM {self.getTableString("earnings_dates_c")})')

        ## construct WHERE portion
        if adds:
            stmt += ' WHERE '
            stmt += ' AND '.join(adds)

        ## get only distinct symbols if query includes looking at historical table data
        if includingHistorical:
            stmt += f' GROUP BY {",".join([f"s.{c}" for c in symbolsSnakeCaseTableColumns])} '

        if gconfig.testing.enabled and gconfig.testing.GET_SYMBOLS_LIMIT > 0: 
            stmt += ' LIMIT ' + str(gconfig.testing.GET_SYMBOLS_LIMIT)
        elif gconfig.testing.REDUCED_SYMBOL_SCOPE: 
            stmt += ' LIMIT ' + str(gconfig.testing.REDUCED_SYMBOL_SCOPE)            

        ## so query inserted into other queries before execution
        if rawStmt:
            return stmt, args

        # print('executing',stmt, args)
        return self.dbc.execute(stmt, tuple(args)).fetchall()

    ## assumes you are looking for rows that have details missing
    def getSymbolsTempInfo(self, api):
        stmt = f'SELECT * FROM {self.getTableString("staging_symbol_info_d")} ts JOIN symbols s ON ts.exchange=s.exchange AND ts.symbol=s.symbol'
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

    def getStagedSymbolRows(self) -> List[StagingSymbolInfoDRow]:
        return self.dbc.execute(f'SELECT * FROM {self.getTableString("staging_symbol_info_d")}').fetchall()

    ## get symbols of which financials retrieval has not already been attempted
    def getSymbols_forFinancialStaging(self, api, ftype: FinancialReportType=None) -> List[SymbolsRow]:
        # stmt = 'SELECT s.exchange, s.symbol FROM symbols s LEFT JOIN {self.getTableString("staging_financials_d")} sf ON s.exchange = sf.exchange AND s.symbol = sf.symbol WHERE sf.exchange IS NULL AND sf.symbol IS NULL AND s.api_' + api + ' = 1'
        # if ftype:
        #     stmt += ' AND sf.period = \'' + ftype.name + '\''
        substmt = f'SELECT * FROM {self.getTableString("staging_financials_d")} WHERE exchange = symbols.exchange AND symbol = symbols.symbol AND ' + api + ' IS NOT NULL'
        if ftype: substmt += ' AND period = \'' + ftype.name + '\''
        stmt = 'SELECT * FROM symbols WHERE NOT EXISTS (' + substmt + ') AND api_' + api + ' = 1'
        return self.dbc.execute(stmt).fetchall()

    ## get the row for each symbol with the latest datetime from historical_data_minute
    def getLatestMinuteDataRows(self, api):
        stmt = '''
            SELECT s.exchange, s.symbol, MAX(h.timestamp) AS timestamp FROM symbols s LEFT JOIN historical_data_minute h
            ON s.exchange = h.exchange AND s.symbol = h.symbol
            WHERE s.api_{api} = 1
            GROUP BY s.exchange, s.symbol
        '''.format(api=api)
        return self.__purgeUnusableTickers(self.dbc.execute(stmt).fetchall())

    ## get raw data from last_updates
    def getLastUpdatedInfo(self, seriesType, dt=None, dateModifier=OperatorDict.EQUAL, **kwargs):
        symbolsStmt, symbolsArgs = self.getSymbols(seriesType=seriesType, rawStmt=True, **kwargs)
        stmt = f'SELECT * FROM last_updates lu JOIN ({symbolsStmt}) sl on lu.exchange=sl.exchange and lu.symbol=sl.symbol WHERE lu.type=? AND lu.api IS NOT NULL'
        args = symbolsArgs + [seriesType.function.replace('TIME_SERIES_','')]
        if dt:
            dt = asDate(dt)
            stmt += ' AND lu.date' + dateModifier.sqlsymbol + '? '

            ## adjust anchor date if on a weekend, so it do not result in an empty symbol list because anchor is ahead of last update date
            weekday = dt.weekday()
            if weekday > 4:
                dt = dt - timedelta(days=(weekday % 4))

            args.append(dt.isoformat())

        stmt += ' ORDER BY date ASC'
        if gconfig.testing.predictor: 
            stmt += ' LIMIT ' + str(gconfig.testing.predictorStockQueryLimit)
            # print(stmt)
            # print(args)
        return self.__purgeUnusableTickers(self.dbc.execute(stmt, tuple(args)).fetchall(), **kwargs)

    ## used by collector to determine which stocks are more in need of new/updated data
    def getLastUpdatedCollectorInfo(self, exchange=None, symbol=None, seriesType=None, api=None, googleTopicID:Union[SQLHelpers,Direction]=None, apiSortDirection:Direction=Direction.DESCENDING, apiFilter:Union[APIState, List[APIState]]=APIState.WORKING):
        stmt = 'SELECT s.*, u.api, u.date FROM last_updates u join symbols s on u.exchange=s.exchange and u.symbol=s.symbol'
        adds = []
        args = []

        if exchange is not None:    exchange = asList(exchange)
        else:                       exchange = standardExchanges
        adds.append('(' + ' OR '.join(['u.exchange=?' for a in exchange]) + ')')
        args.extend(exchange)

        if symbol:
            adds.append('u.symbol = ?')
            args.append(symbol)
        if seriesType:
            adds.append('type = ?')
            args.append(seriesType.function.replace('TIME_SERIES_',''))
        if type(googleTopicID) == str:
            adds.append('google_topic_id=?')
            args.append(googleTopicID)
        elif type(googleTopicID) == SQLHelpers:
            adds.append('google_topic_id IS ?')
            args.append(googleTopicID)

        if adds:
            stmt += ' WHERE '
            adds.append('(' + ' OR '.join(['api_{}={}'.format(a, st.value) for a in ([api] if api else apiList) for st in (apiFilter if type(apiFilter) is list else [apiFilter])]) + ')')
            stmt += ' AND '.join(adds)

        stmt += ' ORDER BY ' + \
            (f'api_{api} {apiSortDirection.value}, ' if api else '') + \
            'api_polygon ASC, date ASC, ' + \
            (f'google_topic_id {googleTopicID.value}' if type(googleTopicID) == Direction else '')

        return self.dbc.execute(stmt, tuple(args))

    ## get network stats
    ## used by setManager when getting a saved data set
    def getSetInfo(self, id) -> NetworksRow:
        stmt = 'SELECT * FROM networks WHERE id = ?'
        return self.dbc.execute(stmt, (id,)).fetchone()

    ## get all historical data for ticker and seriesType
    ## sorted date ascending
    def getStockData(self, exchange: str, symbol: str, seriesType: SeriesType, minDate=None, fillGaps=False, queryLimit=None) -> List[HistoricalDataRow]:
        stmt = 'SELECT * from historical_data WHERE exchange=? AND symbol=? AND series_type=? ' 
        # return self._queryOrGetCache(stmt, (exchange, symbol, type.name), self._getHistoricalDataCount(), exchange+';'+symbol+';'+type.name)
        if minDate:    stmt += 'AND period_date > \'' + asISOFormat(minDate) + '\''
        stmt += ' ORDER BY period_date'
        if queryLimit: stmt += ' DESC LIMIT ' + str(queryLimit)

        data = self.dbc.execute(stmt, (exchange.upper(), symbol.upper(), seriesType.name)).fetchall()

        return data

    ## get saved data set for network
    def getDataSet(self, id, setid) -> List:
        stmt = 'SELECT * FROM data_sets WHERE network_id = ? AND network_set_id = ?'
        return self.dbc.execute(stmt, (id, setid)).fetchall()

    ## get all neural networks including factories and training config
    def getNetworks(self):
        stmt = 'SELECT n.*, ntc.*, ivf.factory, ivf.config FROM networks n JOIN input_vector_factories ivf ON n.factory_id = ivf.id JOIN network_training_config ntc ON n.id = ntc.id'
        return self.dbc.execute(stmt).fetchall()

    ## setup helper for iterating through historical data in chronological order, stock by stock
    def getHistoricalStartEndDates(self, exchange=None, symbol=None, seriesType:SeriesType=SeriesType.DAILY):
        stmt = 'SELECT min(period_date) as start, max(period_date) as finish, exchange, symbol FROM historical_data WHERE series_type=? '
        tuple = (seriesType.name,)
        if exchange:
            stmt += 'AND exchange=? '
            tuple += (exchange, )
        if symbol:
            stmt += 'AND symbol=? '
            tuple += (symbol, )
        stmt += 'GROUP BY exchange, symbol'
        return self.dbc.execute(stmt, tuple).fetchall()
    
    ## gets columns, including ones that are normalization associated, i.e. columns beginning with 'highest' of the form 'highest_<grouping name>_<table column>'
    def getNetworkTrainingConfigColumns(self):
        return self.dbc.execute('PRAGMA table_info(network_training_config)').fetchall()

    ## performs imperfect calculation of maxes, using column averages grouped by ticker rather than the raw values across all tickers (allows filtering out of unusable tickers while possibly saving memory/cpu time)
    def getNormalizationData(self, seriesType: SeriesType=None, standardDeviationCount=2.5, normalizationGrouping: Union[NormalizationGroupings, List[NormalizationGroupings]]=None, **kwargs) -> NormalizationDataHandler:
        ## determine which data will be collected
        normalizationGrouping = asList(normalizationGrouping)
        if normalizationGrouping:
            ngroups = normalizationGrouping
        else:
            ngroups = [NormalizationGroupings.STOCK]
            if seriesType: ngroups.append(NormalizationGroupings.HISTORICAL)
            if False: ngroups.append(NormalizationGroupings.FINANCIAL) ## TODO

        normalizationData = NormalizationDataHandler.buildFromDBColumns(self.getNetworkTrainingConfigColumns())
        ## get averages for each normalization data column
        for c in normalizationData:
            stmt = f'SELECT *, avg({c.columnName}) FROM {c.normalizationGrouping.tableName} '
            args = []
            if c.normalizationGrouping == NormalizationGroupings.HISTORICAL:
                stmt += ' WHERE series_type=? GROUP BY exchange, symbol'
                args.append(seriesType.name)
            # elif c.normalizationGrouping == NormalizationGroupings.STOCK:
            #     pass ## nothing to do
            # elif c.normalizationGrouping == NormalizationGroupings.FINANCIAL:
            #     pass ## TODO
            
            if gconfig.testing.REDUCED_SYMBOL_SCOPE: stmt += f' LIMIT {gconfig.testing.REDUCED_SYMBOL_SCOPE}'
            data = self.__purgeUnusableTickers(self._queryOrGetCache(stmt, tuple(args), self._getHistoricalDataCount(), 'getsandavg'))

            ## extract row values
            vals = [r[f'avg({c.columnName})'] for r in data]
            std = np.std(vals)
            avg = np.mean(vals)
            lowerlimit = max(0, avg - std * standardDeviationCount)
            upperlimit = avg + std * standardDeviationCount
            c.value = upperlimit

        return normalizationData

    ## returns normalizationColumns, normalizationMaxes, symbolList
    def getNormalizationData_old(self, seriesType, normalizationInfo=None, exchange=None, excludeExchange=None, sectors=[], excludeSectors=[], assetTypes=[], **kwargs):
        DEBUG = True
        normalizationColumns = ['high', 'volume']

        if normalizationInfo:
            normalizationMaxes = [normalizationInfo[x + 'Max'] for x in normalizationColumns]
        else:
            print('Getting symbols and averages')
            normalizationLists = []
            stmt = ('SELECT exchange, symbol' + ', avg({})' * len(normalizationColumns) + ' FROM historical_data WHERE series_type=? GROUP BY exchange, symbol').format(*normalizationColumns)
            if gconfig.testing.enabled and gconfig.testing.GET_SYMBOLS_LIMIT > 0: stmt += ' LIMIT ' + str(gconfig.testing.GET_SYMBOLS_LIMIT)

            data = self._queryOrGetCache(stmt, (seriesType.name,), self._getHistoricalDataCount(), 'getsandavg')

            for c in normalizationColumns:
                normalizationLists.append(
                    [x['avg(%s)' % c] for x in
                        [y for y in data if (y.exchange, y.symbol) not in unusableSymbols]
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
                    if DEBUG: print(sdc, 'standard deviations of range will include', pinside / len(normalizationLists[i]) * 100, '% of symbols')


        ## get symbols data that meet normalization and other criteria        
        stmt = '''SELECT s.exchange, s.symbol, s.sector, s.industry, s.founded, s.asset_type, s.google_topic_id 
            FROM historical_data h JOIN symbols s'''
        stmt2 = ' ON h.exchange=s.exchange AND h.symbol=s.symbol '
        stmt3 = 'WHERE h.series_type=?'
        # stmt = f'SELECT * FROM historical_data h JOIN symbols s, {self.getTableString("staging_symbol_info_d")} st ON h.exchange=s.exchange AND h.symbol=s.symbol and h.exchange = st.exchange and h.symbol = st.symbol WHERE h.series_type=?'
        # stmt = 'SELECT h.exchange as exchange, h.symbol as symbol, s.asset_type as asset_type, s.google_topic_id as google_topic_id FROM historical_data h JOIN symbols s ON h.exchange=s.exchange AND h.symbol=s.symbol WHERE h.series_type=?'

        if gconfig.feature.financials.enabled and gconfig.feature.financials.dataRequired:
            stmt += ' , vwtb_edgar_quarters q'
            stmt2 += ' AND h.exchange = q.exchange AND h.symbol = q.symbol '
            stmt3 += ' AND h.exchange||h.symbol IN (SELECT DISTINCT q.exchange||q.symbol FROM vwtb_edgar_quarters q) AND REPLACE(h.period_date, \'-\', \'\') >= q.filed'

        if normalizationInfo or gconfig.testing.enabled:
            exchange = asList(exchange)
            if gconfig.testing.enabled:
                exchange.append(gconfig.testing.exchange)

            if exchange:
                stmt3 += self._andXContainsListStatement('h.exchange', exchange)
            elif excludeExchange:
                stmt3 += self._andXContainsListStatement('h.exchange', asList(excludeExchange), notIn=True)

            if sectors:
                stmt3 += self._andXContainsListStatement('h.sector', sectors)
            elif excludeSectors:
                stmt3 += self._andXContainsListStatement('h.sector', excludeSectors, notIn=True)

            if assetTypes:
                stmt3 += self._andXContainsListStatement('s.asset_type', assetTypes)
        else:
            if gconfig.feature.googleInterests.enabled: 
                stmt3 += 'AND s.google_topic_id IS NOT NULL'
            if gconfig.feature.companyAge.enabled and gconfig.feature.companyAge.dataRequired: 
                stmt3 += ' AND s.founded IS NOT NULL'
            if gconfig.feature.sector.enabled and gconfig.feature.sector.dataRequired:
                stmt3 += ' AND s.sector IS NOT NULL'


        tuple = (seriesType.name,)
        for i in range(len(normalizationColumns)):
            stmt3 += ' AND h.%s <= ? ' % normalizationColumns[i]
            tuple += (normalizationMaxes[i],)

        stmt = stmt + stmt2 + stmt3

        stmt += ' GROUP BY h.exchange, h.symbol'
        if gconfig.testing.enabled and gconfig.testing.GET_SYMBOLS_LIMIT > 0: stmt += ' LIMIT ' + str(gconfig.testing.GET_SYMBOLS_LIMIT)
        elif gconfig.testing.REDUCED_SYMBOL_SCOPE: stmt += ' LIMIT ' + str(gconfig.testing.REDUCED_SYMBOL_SCOPE)

        symbolList = self._queryOrGetCache(stmt, tuple, self._getHistoricalDataCount(), 'getnormsymbolist')
        # symbolList = self.dbc.execute(stmt, tuple).fetchall()

        if DEBUG and not normalizationInfo: print (len(symbolList), '/', len(normalizationLists[0]), 'are within thresholds')

        return normalizationColumns, normalizationMaxes, symbolList

    def _andXContainsListStatement(self, column, lst, notIn=False):
        return ' AND ' + column + (' not' if notIn else '') + ' in (\'' + '\',\''.join(lst) + '\')'

    ## generally one time use
    def getGoogleTopicIDsForSymbols(self, symbol=None, dryrun=False):
        print('Getting topic IDs from Google')
        DEBUG = True
        gapi = GoogleAPI()
        stmt = 'UPDATE symbols SET google_topic_id=? WHERE exchange=? AND symbol=? '
        symbols = shortc(asList(symbol), self.getSymbols(api=['alphavantage', 'polygon'], googleTopicId=SQLHelpers.NULL))
        topicsFound = []
        alreadyFound = 0
        for s in tqdm(symbols):
            if not s.google_topic_id:
                ex = s.exchange.replace(' ','').replace('TSX','TSE').replace('MKT', 'AMERICAN')
                kw = ex + ':' + s.symbol
                topics = gapi.suggestions(kw)
                for t in topics:
                    if t['type'] == 'Topic' and t['title'] == kw:
                        if not dryrun: self.dbc.execute(stmt, (t['mid'], s.exchange, s.symbol))
                        else: print(t['mid'], s.exchange, s.symbol)
                        topicsFound.append(kw)
            else:
                alreadyFound += 1
        if DEBUG: 
            for t in topicsFound: print(t)
        print(len(topicsFound), '/', len(symbols) - alreadyFound, 'topics found')

    def getFinancialData(self, exchange, symbol, raw=False):
        stmt = 'SELECT * FROM vwtb_edgar_financial_nums n JOIN vwtb_edgar_quarters q ON n.exchange = q.exchange AND n.symbol = q.symbol AND n.ddate = q.period WHERE n.exchange=? AND n.symbol=? ORDER BY q.period'
        res = self.dbc.execute(stmt, (exchange, symbol)).fetchall()

        return processDBQuartersToDicts(res) if not raw else res

    def getVIXData(self) -> List[CboeVolatilityIndexRow]:
        stmt = 'SELECT * FROM cboe_volatility_index ORDER BY date'
        return self.dbc.execute(stmt).fetchall()

    def getVIXMax(self) -> float:
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


    def getSectors(self, asRowDict=False):
        stmt = 'SELECT * FROM sectors ORDER BY rowid'
        res = self.dbc.execute(stmt).fetchall()
        return res if asRowDict else [r['sector'] for r in res]

    def getMostRecentNetworkAccuracyUpdateRows(self, nnid) -> List[AccuracyLastUpdatesRow]:
        stmt = 'SELECT * FROM accuracy_last_updates WHERE network_id=?'
        return self.dbc.execute(stmt, (str(nnid),)).fetchall()

    def getNetworkAccuracy(self, nnid, acctype: AccuracyAnalysisTypes, arg1: Union[PrecedingRangeType, str], arg2=None) -> List[NetworkAccuraciesRow]:
        stmt = 'SELECT subtype2, sum, count FROM network_accuracies WHERE network_id=? AND accuracy_type=? AND subtype1=?'
        tple = [str(nnid), acctype.value]
        if acctype == AccuracyAnalysisTypes.STOCK:
            stmt += ' AND subtype2=?'
            tple += [arg1, arg2]
        elif acctype == AccuracyAnalysisTypes.PRECEDING_RANGE:
            tple.append(arg1.value)
        
        res = self.dbc.execute(stmt, tuple(tple)).fetchall()

        if acctype == AccuracyAnalysisTypes.STOCK:
            count = res[0]['count']
            if count == 0: return 0
            return res[0]['sum']/count
        elif acctype == AccuracyAnalysisTypes.PRECEDING_RANGE:
            r1type = res[0]['subtype2']
            r1count = res[0]['count']
            r2count = res[1]['count']
            total = r1count + r2count
            if CorrBool(r1type) == CorrBool.CORRECT:
                correct = r1count
            else:
                correct = r2count
            return correct/total

    def getTickerSplit(self, nnid, setCount):
        stmt = 'SELECT pickled_split FROM ticker_splits WHERE network_id=? AND set_count=?'
        res = self.dbc.execute(stmt, (nnid, setCount)).fetchall()
        if len(res) > 1:
            raise ValueError('Too many returned rows')
        return recdotobj(res[0]['pickled_split'])

    def getLatestSplitDate(self, exchange=None) -> str:
        stmt = 'SELECT max(date) as date FROM stock_splits'
        args = []
        exchange = asList(shortc(exchange, []))
        if exchange:
            stmt += ' WHERE exchange in ({})'.format(','.join(['?' for e in exchange]))
            args.extend(exchange)

        print(stmt, args)
        res = self.dbc.execute(stmt, tuple(args)).fetchone()['date']
        if not res:
            return '1970-01-01'
        else:
            return res
    
    def getStockSplits(self, exchange=None, symbol=None) -> List[StockSplitsPolygonDRow]:
        # stmt = 'SELECT * FROM stock_splits'
        stmt = f'SELECT * FROM {self.getTableString("stock_splits_polygon_d")}'
        args = []
        exchange = asList(shortc(exchange, []))
        if exchange:
            stmt += ' WHERE exchange in ({})'.format(','.join(['?' for e in exchange]))
            args.extend(exchange)
            if symbol:
                stmt += ' AND symbol=?'
                args.append(symbol)
        return self.dbc.execute(stmt, tuple(args)).fetchall()

    def getGoogleInterests(self, exchange=None, symbol=None, gtopicid=None, itype:InterestType=InterestType.DAILY, stream=None, artificial=None, dt=None, raw=False, queryLimit=None):
        stmt = ''
        args = []
        gitable = self.getTableString(f'google_interests{"_d" if raw else "_c"}')
        if gtopicid:
            stmt = f'SELECT * FROM {gitable} gi JOIN symbols s ON gi.exchange=s.exchange AND gi.symbol=s.symbol WHERE gi.google_topic_id=? '
            args.append(gtopicid)
        elif exchange and symbol:
            stmt += f'SELECT * FROM {gitable} gi WHERE gi.exchange=? and gi.symbol=? '
            args.extend([exchange, symbol])

        if raw:
            stmt += 'AND gi.type = ? '
            args.append(itype.name)

            if itype is not None:
                stmt += ' AND gi.type=? '
                args.append(itype.name)
            if stream is not None:
                stmt += ' AND gi.stream=? '
                args.append(stream)
            if artificial is not None:
                stmt += ' AND gi.artificial=? '
                args.append(artificial)
        if dt is not None:
            stmt += ' AND gi.date=? '
            args.append(asISOFormat(dt))
        stmt += 'ORDER BY gi.date ASC'
        if queryLimit: stmt += ' LIMIT ' + str(queryLimit)

        return self.dbc.execute(stmt, tuple(args)).fetchall()

    def getMaxGoogleInterestStream(self, exchange=None, symbol=None, gtopicid=None, itype:InterestType=InterestType.DAILY) -> int:
        stmt = f'SELECT MAX(stream) AS maxstream FROM {self.getTableString("google_interests_d")} gi '
        args = []
        if gtopicid:
            stmt = ' JOIN symbols s ON gi.exchange=s.exchange AND gi.symbol=s.symbol WHERE gi.google_topic_id=? '
            args.append(gtopicid)
        elif exchange and symbol:
            stmt += ' WHERE gi.exchange=? and gi.symbol=? '
            args.extend([exchange, symbol])

            stmt += 'AND gi.type = ? '
            args.append(itype.name)

        if itype is not None:
            stmt += ' AND gi.type=? '
            args.append(itype.name)

        res = self.dbc.execute(stmt, tuple(args)).fetchall()
        if len(res) > 0:
            return res[0].maxstream
        else:
            return -1

    def getTechnicalIndicatorData(self, exchange, symbol, indicator: IndicatorType, seriesType: SeriesType=SeriesType.DAILY, date=None, period=None, valuesOnly=True):
        stmt = f'SELECT {"*" if not valuesOnly else "value"} FROM {self.getTableString("technical_indicator_data_c")} WHERE exchange=? and symbol=? and indicator=? AND date_type=? '
        args = [exchange, symbol, indicator.key, seriesType.name]
        if date:
            stmt += ' AND date=? '
            args.append(date)
        if period:
            stmt += ' AND period=? '
            args.append(period)

        res = self.dbc.execute(stmt, tuple(args)).fetchall()
        if valuesOnly:
            return [indicator.sqlParser(d.value) for d in res]
        return res

    def getDistinctExchangesForHistoricalData(self):
        stmt = 'SELECT DISTINCT exchange FROM historical_data'
        res = self.dbc.execute(stmt).fetchall()
        return [e for e in res]
    
    def getVectorSimilarity(self, exchange, symbol, seriesType: SeriesType=None, dt=None, vclass: OutputClass=None, precedingRange=None, followingRange=None, threshold=None, orderBy='date') -> List[VectorSimilaritiesCRow]:
        stmt = f'SELECT * FROM {self.getTableString("vector_similarities_c")} WHERE exchange=? and symbol=? '
        args = [exchange, symbol]

        if seriesType:
            stmt += 'AND date_type=? '
            args.append(seriesType.name)
        if dt:
            stmt += 'AND date=? '
            args.append(asISOFormat(dt))
        if vclass:
            stmt += 'AND vector_class=? '
            args.append(vclass.name)
        if precedingRange:
            stmt += 'AND preceding_range=? '
            args.append(precedingRange)
        if followingRange:
            stmt += 'AND following_range=? '
            args.append(followingRange)
        if threshold:
            stmt += 'AND change_threshold=? '
            args.append(threshold)
        
        stmt += f' ORDER BY {orderBy} ASC'

        return self.dbc.execute(stmt, tuple(args)).fetchall()

    def getYahooSymbolInfo(self, symbol):
        return self.dbc.execute(f'SELECT * FROM {self.getTableString("symbol_info_yahoo_d")} WHERE symbol=?', (symbol,)).fetchall()

    def getDumpEarningsDates(self, api: EarningsCollectionAPI, exchange=None, symbol=None, **kwargs):
        wherestmt = ''
        args = []
        if api == EarningsCollectionAPI.NASDAQ:
            table = 'earnings_dates_nasdaq_d'
            if symbol:
                wherestmt = ' WHERE symbol=? '
                args = [symbol]
        else:
            if api == EarningsCollectionAPI.MARKETWATCH:
                table = 'earnings_dates_marketwatch_d'
            elif api == EarningsCollectionAPI.YAHOO:
                table = 'earnings_dates_yahoo_d'

            if exchange or symbol:
                wherestmt = ' WHERE '
                if exchange:
                    wherestmt += 'exchange=? '
                    args.append(exchange)
                    if symbol:
                        wherestmt += 'AND symbol=?'
                        args.append(symbol)
                else:
                    wherestmt += 'symbol=?'
                    args.append(symbol)

        stmt = f'SELECT * FROM {self.getTableString(table)} {wherestmt}'
        return self.dbc.execute(stmt, args).fetchall()

    def getUniqueEarningsCollectionDates(self, api: EarningsCollectionAPI):
        if api == EarningsCollectionAPI.NASDAQ:
            table = 'earnings_dates_nasdaq_d'
        elif api == EarningsCollectionAPI.MARKETWATCH:
            table = 'earnings_dates_marketwatch_d'
        elif api == EarningsCollectionAPI.YAHOO:
            table = 'earnings_dates_yahoo_d'
        
        stmt = f'SELECT DISTINCT input_date AS date FROM {self.getTableString(table)} ORDER BY date ASC'
        return [r.date for r in self.dbc.execute(stmt).fetchall()]

    def getLatestEarningsCollectionDate(self, api: EarningsCollectionAPI):
        ''' returns latest anchor date, i.e. date on which collection was done but the (most recent market) day's data was not updated yet '''
        wherestmt = 'WHERE surprise_percentage IS NOT NULL'
        if api == EarningsCollectionAPI.NASDAQ:
            table = 'earnings_dates_nasdaq_d'
        elif api == EarningsCollectionAPI.MARKETWATCH:
            table = 'earnings_dates_marketwatch_d'
        elif api == EarningsCollectionAPI.YAHOO:
            table = 'earnings_dates_yahoo_d'
        
        stmt = f'SELECT MAX(input_date) AS date FROM {self.getTableString(table)} {wherestmt}'

        return self.dbc.execute(stmt).fetchone()['date']

    def getEarningsDate(self, exchange=None, symbol=None, inputDate=None, earningsDate=None):
        additionalStmt, arguments = generateSQLAdditionalStatementAndArguments(**locals())
        stmt = f'SELECT * FROM {self.getTableString("earnings_dates_c")}'
        return self.dbc.execute(stmt + additionalStmt, arguments).fetchall()


    ## end gets ####################################################################################################################################################################
    ####################################################################################################################################################################
    ## sets ####################################################################################################################################################################

    ## ensures there are corresponding rows in the last_updates table for each ticker in the symbols table
    def addLastUpdatesRowsForAllSymbols(self, exchange=None, verbose=1):
        stmt = 'SELECT exchange, symbol FROM symbols'
        args = []
        if exchange:
            stmt += ' WHERE exchange=?'
            args.append(exchange)
        tickers = self.dbc.execute(stmt, tuple(args)).fetchall()
        # tickers = self.dbc.execute("SELECT exchange, symbol FROM symbols WHERE exchange='TSX'").fetchall()
        if verbose > 0: print(len(tickers),'tickers found')

        tot = 0
        for t in tickers:
            exchange, symbol = t.values()

            for e in SeriesType:
                try:
                    self.dbc.execute('INSERT INTO last_updates(exchange, symbol, type, date) VALUES (?,?,?,?)', (exchange, symbol, e.name, '1970-01-01'))
                    tot += self.dbc.rowcount
                except sqlite3.IntegrityError:
                    pass
        if verbose > 0: print(tot, 'rows added')

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

    def insertHistoricalData(self, tuples, modifier: SQLInsertHelpers=SQLInsertHelpers.NONE):
        '''exchange, symbol, seriesType enum, ISO date string, open, high, low, close, volume, artifical bool'''

        self._resetCachedHistoricalDataCount()

        stmt = f'INSERT {modifier.value} INTO historical_data VALUES (?,?,?,?,?,?,?,?,?,?)'
        self.dbc.executemany(stmt, tuples)

    ## insert data in historical_data table and update the last_updates table with the API used and current date
    def insertData(self, exchange, symbol, seriesType: SeriesType, api, data: Dict[str, Dict], currentDate=date.today()):
        tuples = [(exchange, symbol, seriesType.name, str(d), r.open, r.high, r.low, r.close, r.volume, 0) for d,r in data.items()]
        self.insertHistoricalData(tuples, modifier=SQLInsertHelpers.REPLACE)

        ## insert successful, log the updation date and api
        stmt = 'UPDATE last_updates SET date=?, api=? WHERE exchange=? AND symbol=? AND type=?'
        self.dbc.execute(stmt, (str(currentDate), api, exchange, symbol, seriesType.name))
        # print('Data inserted and updated')

    ## insert data in historical_data_minute table
    def insertMinuteBatchData(self, exchange, symbol, data):
        stmt = 'INSERT OR REPLACE INTO historical_data_minute VALUES (?,?,?,?,?,?,?,?,?,?,?)'
        tuples = [(exchange, symbol, unixToDatetime(d.unixTimePeriod), d.open, d.high, d.low, d.close, d.volumeWeightedAverage, d.volume, d.transactions, shortcdict(d, 'artificial', 0, shortcValue=False)) for d in data]
        self.dbc.executemany(stmt, tuples)  

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
        #         # print('d', h.data[i.index], h.data[i.index].period_date)
        #         tpls.append((id, h.exchange, h.symbol, h.seriesType.name, h.data[i.index].period_date, setId, stype.name))
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
        
        def _saveSet(dset, stype):
            for i in tqdm(dset, desc='Saving ' + stype.name + ' set and interests'):
                ## save to data_sets
                h = i.handler
                self.dbc.execute(ds_stmt, (id, h.symbolData.exchange, h.symbolData.symbol, h.seriesType.name, h.data[i.index].period_date, setId, stype.name))
            
        # for t in SetType
        _saveSet(trainingSet, SetType.TRAINING)
        _saveSet(validationSet, SetType.VALIDATION)
        _saveSet(testingSet, SetType.TESTING)

    ## insert or update network table data
    def pushNeuralNetwork(self, 
        nn, ##: NeuralNetworkInstance ## removed to reduce inter-module dependencies on tensorflow, for EC2 collection
        dryrun=False
    ):
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
                if not dryrun: self.dbc.execute(stmt, tpl)
                else: print('inserting input vector factory\n', stmt, tpl)
                factoryId = self.dbc.lastrowid
            nn.stats.factoryId = factoryId
        else:
            factoryId = nn.stats.factoryId
        
        args = list(nn.stats.getNetworksTableData(dbInsertReady=True).values())
        stmt = f'INSERT OR REPLACE INTO networks VALUES ({generateCommaSeparatedQuestionMarkString(args)})'
        if not dryrun: self.dbc.execute(stmt, tuple(args))
        else: print('inserting network\n', stmt, args)

        args = list(nn.stats.getNetworkTrainingConfigTableData(dbInsertReady=True).values())
        stmt = f'INSERT OR REPLACE INTO network_training_config VALUES ({generateCommaSeparatedQuestionMarkString(args)})'
        if not dryrun: self.dbc.execute(stmt, tuple(args))
        else: print('inserting network/training config\n', stmt, args)

    def insertVIXRow(self, row=None, point=None):
        stmt = 'INSERT OR REPLACE INTO cboe_volatility_index(date, open, high, low, close, artificial) VALUES (?,?,?,?,?,?)'
        val = self._convertVIXDataPoint(row) if row else point
        self.dbc.execute(stmt, (*val,))

    def insertVectorSimilarity(self, exchange, symbol, seriesType: SeriesType, dt, vclass: OutputClass, precedingRange, followingRange, threshold, val, upsert=True):
        stmt = f'INSERT {"OR IGNORE" if upsert else ""} INTO {self.getTableString("vector_similarities_c")} VALUES (?,?,?,?,?,?,?,?,?)'
        args = [exchange, symbol, seriesType.name, asISOFormat(dt), vclass.name, precedingRange, followingRange, threshold]
        self.dbc.execute(stmt, tuple(args + [val]))
        if upsert:
            stmt = f'UPDATE {self.getTableString("vector_similarities_c")} SET value=? WHERE exchange=? AND symbol=? AND date_type=? AND date=? AND vector_class=? AND preceding_range=? AND following_range=? AND change_threshold=?'
            self.dbc.execute(stmt, tuple([val] + args))

    ## for updating symbol details like sector, industry, founded
    ## updateDetails is expected to be a dict with keys corresponding to the column names
    def updateSymbolTempInfo(self, updateDetails, infoPrefix, exchange=None, symbol=None):
        stmt = f'UPDATE {self.getTableString("staging_symbol_info_d")} SET '
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
        stmt = f'INSERT INTO {self.getTableString("staging_financials_d")}({api}, exchange, symbol, period, calendarDate) VALUES (?,?,?,?,?) ON CONFLICT(exchange, symbol, period, calendarDate) DO UPDATE SET {api} = 0'
        self.dbc.execute(stmt, (0, exchange, symbol, ftype.name, '1970-01-01'))

    def insertFinancials_staging_old(self, api, exchange, data: List[dict], period=None, symbol=None):
        symbolcol = 'symbol'
        periodcol = 'period'
        datecol = 'calendarDate'
        ## confirm columns are present in staging table; construct statement
        pkcolumnnames = ['exchange', symbolcol, periodcol, datecol]

        for d in data:
            columnnames = [r[0] for r in self.dbc.execute(f'SELECT * FROM {self.getTableString("staging_financials_d")}').description]

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
                    self.dbc.execute(f'ALTER TABLE {self.getTableString("staging_financials_d")} ADD COLUMN {coln} TEXT')
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
            stmt = f'INSERT INTO {self.getTableString("staging_financials_d")}({columnsstr}) VALUES ({ generateCommaSeparatedQuestionMarkString(final_overall_tpl) })'
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
        self.__insertAPIDumpData('staging_financials_d', pkObj, data, api, columnNameRemapping, pkcolumnValueRemapping)

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
        self.__insertAPIDumpData('symbol_info_polygon_d', pkObj, data, api, columnNameRemapping, pkcolumnValueRemapping)
       
    ## dump table should have the following columns: PRIMARY_KEY(s), API(s)
    def __insertAPIDumpData(self, table, pkObj: dict, data, api, columnNameRemapping={}, pkcolumnValueRemapping={}):
        columnNames = [r[0] for r in self.dbc.execute(f'SELECT * FROM {self.getTableString(table)}').description]

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
                    self.dbc.execute(f'ALTER TABLE {self.getTableString(table)} ADD COLUMN {coln} TEXT')
               

            final_insertstmt_pkcolumnnames = [api] + insertstmt_pkcolumnNames
            final_pktpl = [True] + pktpl
            final_overall_tpl = tpl + final_pktpl


            columnsstr = ','.join(insertstmt_columnNames) + ',' + ','.join(final_insertstmt_pkcolumnnames)
            stmt = f'INSERT INTO {self.getTableString(table)}({columnsstr}) VALUES ({ generateCommaSeparatedQuestionMarkString(final_overall_tpl) }'
            stmt += f' ON CONFLICT({ ",".join(insertstmt_pkcolumnNames) }) DO UPDATE SET {api} = 1, { ",".join([ f"{k} = {processRawValueToInsertValue(v)}" for k,v in zip(insertstmt_columnNames, tpl) ]) }'

            try:
                self.dbc.execute(stmt, tuple(final_overall_tpl))
            except sqlite3.OperationalError:
                print(stmt)
                raise sqlite3.OperationalError

    def insertEDGARFinancialDump(self, period, sub: list, tag: list, num: list, pre=None, ptype='quarter'):
        if len(sub) == 0:
            return

        sub_stmt = f'INSERT INTO {self.getTableString("financial_stmts_sub_data_set_edgar_d")} VALUES ({ generateCommaSeparatedQuestionMarkString(len(sub[0].keys())+2) })'
        tag_stmt = f'INSERT INTO {self.getTableString("financial_stmts_tag_data_set_edgar_d")} VALUES ({ generateCommaSeparatedQuestionMarkString(tag[0].keys()) })'
        num_stmt = f'INSERT INTO {self.getTableString("financial_stmts_num_data_set_edgar_d")} VALUES ({ generateCommaSeparatedQuestionMarkString(len(num[0].keys())+1) })'
        if pre:
            pre_stmt = f'INSERT INTO {self.getTableString("dump_edgar_pre")} VALUES ({ generateCommaSeparatedQuestionMarkString(pre[0].keys()) })'
            pass

        print('Inserting data...')
        try:
            self.startBatch()

            notfound = 0
            for s in tqdm(sub, desc='Submissions'):
                try:
                    ticker = self.dbc.execute(f'SELECT * FROM {self.getTableString("symbol_info_polygon_d")} WHERE polygon_cik IN (?,?)', (s.cik, s.cik.rjust(10, '0'))).fetchall()[0]
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
                    # print(self.dbc.execute('SELECT * FROM {self.getTableString("financial_stmts_tag_data_set_edgar_d")} WHERE tag=? AND version=?', (t.tag, t.version)).fetchall())
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
                    #     print(self.dbc.execute(f'SELECT * FROM {self.getTableString("financial_stmts_num_data_set_edgar_d")} WHERE adsh=? AND tag=? AND version=? AND ddate=? AND qtrs=?', (n.adsh, n.tag, n.version, n.ddate, n.qtrs)).fetchall())

                    #     raise e
                    # else:
                    # existingkey_row = self.dbc.execute('SELECT * FROM {self.getTableString("financial_stmts_num_data_set_edgar_d")} WHERE adsh=? AND tag=? AND version=? AND coreg=? AND ddate=? AND qtrs=? AND uom=?', (n.adsh, n.tag, n.version, n.coreg, n.ddate, n.qtrs, n.uom)).fetchall()[0]
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

            self.dbc.execute(f'INSERT INTO {self.getTableString("financial_stmts_loaded_periods_d")} VALUES (?,?)', (ptype, period))

            self.commitBatch()
            
                
        except Exception as e:
            print('Transaction error', e)
            self.rollbackBatch()
            raise e

    def updateStockAccuracyForNetwork(self, nnid, exchange, symbol, acc, count):
        wherestmt = ' WHERE network_id=? AND accuracy_type=? AND subtype1=? and subtype2=?'
        stmt = 'SELECT * FROM network_accuracies' + wherestmt
        tple = [nnid, AccuracyAnalysisTypes.STOCK.value, exchange, symbol]
        currentrow = self.dbc.execute(stmt, tuple(tple)).fetchone()

        stmt = 'UPDATE network_accuracies SET sum=?, count=?' + wherestmt
        tple = [currentrow.sum + acc * count, currentrow.count + count] + tple
        self.dbc.execute(stmt, tuple(tple))

    def updatePrecedingRangeAccuraciesForNetwork(self, nnid, accs: Dict[PrecedingRangeType, Dict[CorrBool, int]]):
        wherestmt = ' WHERE network_id=? AND accuracy_type=? AND subtype1=? and subtype2=?'
        stmt = 'SELECT * FROM network_accuracies' + wherestmt
        stmt2 = 'UPDATE network_accuracies SET count=?' + wherestmt
        tple = [nnid, AccuracyAnalysisTypes.PRECEDING_RANGE.value]

        for k,v in accs.items():
            tple2 = tple + [k.value]
            for cb in CorrBool:
                tple3 = tple2 + [cb.value]
                currentrow = self.dbc.execute(stmt, tuple(tple3)).fetchone()
                self.dbc.execute(stmt2, tuple([currentrow.count + v[cb]] + tple3))

    def updateAccuraciesLastUpdated(self, nnid, acctype: AccuracyAnalysisTypes, dataCount, minDate=None, lastExchange=None, lastSymbol=None):
        if not minDate and not lastExchange and not lastSymbol: raise ValueError
        stmt = 'UPDATE accuracy_last_updates SET data_count=?{} WHERE network_id=? AND accuracy_type=?'.format(
            (', min_date=?' if minDate else '') + ', last_exchange=?, last_symbol=?'
        )
        tpl = [dataCount] + ([minDate] if minDate else []) + [lastExchange, lastSymbol, nnid, acctype.value]
        self.dbc.execute(stmt, tuple(tpl))

    def saveTickerSplit(self, nnid, setCount, splitList):
        tickerCount = sum([ len(w) for w in splitList])
        stmt = 'INSERT INTO ticker_splits VALUES (?,?,?,?)'
        tpl = (nnid, setCount, tickerCount, pickle.dumps(splitList))
        self.dbc.execute(stmt, tpl)

    def insertStockSplit(self, exchange, symbol, date, split_from, split_to):
        stmt = 'INSERT INTO stock_splits VALUES (?,?,?,?,?)'
        tpl = (shortc(exchange, SQLHelpers.UNKNOWN.value), symbol, date, split_from, split_to)
        self.dbc.execute(stmt, tpl)

    def insertRawGoogleInterest(self, exchange, symbol, itype:InterestType, date, value, stream=0, artificial=False, upsert=False):
        stmt = f'INSERT{" OR IGNORE" if upsert else ""} INTO {self.getTableString("google_interests_d")} VALUES (?,?,?,?,?,?,?)'
        lst = [exchange, symbol, asISOFormat(date), itype.name, stream]
        self.dbc.execute(stmt, lst + [value, artificial])
        if upsert:
            stmt = f'UPDATE {self.getTableString("google_interests_d")} SET relative_interest=? WHERE exchange=? AND symbol=? AND date=? AND type=? AND stream=?'
            self.dbc.execute(stmt, [value] + lst)

    def insertCalculatedGoogleInterest(self, exchange, symbol, dt, val, upsert=True):
        stmt = f'INSERT OR IGNORE INTO {self.getTableString("google_interests_c")} VALUES (?,?,?,?)'
        args = [exchange, symbol, dt]
        self.dbc.execute(stmt, tuple(args + [val]))
        if upsert:
            stmt = f'UPDATE {self.getTableString("google_interests_c")} SET relative_interest=? WHERE exchange=? AND symbol=? AND date=?'
            self.dbc.execute(stmt, tuple([val] + args))

    def insertEarningsDateDump(self, api: EarningsCollectionAPI, **kwargs):
        if api == EarningsCollectionAPI.NASDAQ:
            table = 'earnings_dates_nasdaq_d'
            cccols = earningsDatesNasdaqDCamelCaseTableColumns
        elif api == EarningsCollectionAPI.MARKETWATCH:
            table = 'earnings_dates_marketwatch_d'
            cccols = earningsDatesMarketwatchDCamelCaseTableColumns
        elif api == EarningsCollectionAPI.YAHOO:
            table = 'earnings_dates_yahoo_d'
            cccols = earningsDatesYahooDCamelCaseTableColumns

        proccessedkwargs = {}
        for k,v in kwargs.items():
            if v is not None and v != 'N/A':
                if k not in cccols: raise ValueError(f'"{k}" argument not in {table} columns')
                proccessedkwargs[k] = v.isoformat() if type(v) == date else v

        stmt = f'INSERT INTO {self.getTableString(table)} VALUES ({ generateCommaSeparatedQuestionMarkString(len(cccols)) })'
        args = [shortcdict(proccessedkwargs, argName) for argName in cccols]

        self.dbc.execute(stmt, args)

    def insertEarningsDate(self, exchange, symbol, inputDate, earningsDate):
        self.dbc.execute(f'INSERT INTO {self.getTableString("earnings_dates_c")} VALUES ({generateCommaSeparatedQuestionMarkString(4)})', (exchange, symbol, inputDate, earningsDate))

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
        # stmt = f'DELETE FROM {self.getTableString("google_interests_c")} WHERE network_id = ?'
        # self.dbc.execute(stmt, (id,))

        # stmt = 'DELETE FROM data_sets WHERE network_id = ?'
        # self.dbc.execute(stmt, (id,))

        ## SQL cascade should handle deletion
        stmt = 'DELETE FROM networks WHERE id = ?'
        self.dbc.execute(stmt, (id,))

    def deleteVectorSimilarities(self, exchange, symbol, seriesType: SeriesType=None, dt=None, vclass: OutputClass=None, precedingRange=None, followingRange=None, threshold=None):
        stmt = f'DELETE FROM {self.getTableString("vector_similarities_c")} WHERE exchange=? AND symbol=?'
        args = [exchange, symbol]
        if seriesType:
            stmt += ' AND date_type=?'
            args.append(seriesType.name)
        if dt:
            stmt += ' AND date=?'
            args.append(asDate(dt).isoformat())
        if vclass:
            stmt += ' AND vector_class=?'
            args.append(vclass.name)
        if precedingRange:
            stmt += ' AND preceding_range=?'
            args.append(str(precedingRange))
        if followingRange:
            stmt += ' AND following_range=?'
            args.append(str(followingRange))
        if threshold is not None:
            stmt += ' AND change_threshold=?'
            args.append(str(threshold))

        self.dbc.execute(stmt, tuple(args))


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
                        # self.dbc.execute(f'UPDATE {self.getTableString("staging_symbol_info_d")} SET founded=? WHERE exchange=? AND symbol=?', (tf, s.exchange, s.symbol))
                        tpls.append((tf, s.exchange, s.symbol))
                else:
                    # print('Unable to determine a date', s.exchange, s.symbol)
                    pass
        

        return tpls

    def _condenseSectorTuples(self):
        stmt = f'SELECT * FROM {self.getTableString("staging_symbol_info_d")} WHERE fmp_sector IS NOT NULL AND polygon_sector IS NOT NULL AND alphavantage_sector IS NOT NULL AND migrated=0'
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
                        earliestdate = date.fromisoformat(data[0].period_date)
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
                    # self.dbc.execute(f'UPDATE {self.getTableString("staging_symbol_info_d")} SET ipo=? WHERE exchange=? AND symbol=?', (ti, s.exchange, s.symbol))
                    pass
            else:
                ## no ipo
                pass

    def staging_condenseFounded(self):
        tpls = self._condenseFoundedTuples()

        self.dbc.executemany(f'UPDATE {self.getTableString("staging_symbol_info_d")} SET founded=? WHERE exchange=? AND symbol=?', tpls)

    def staging_condenseSector(self):
        tpls = self._condenseSectorTuples()
        self.dbc.executemany(f'UPDATE {self.getTableString("staging_symbol_info_d")} SET sector=? WHERE exchange=? AND symbol=?', tpls)


    def symbols_pullStagedSector(self):
        tpls = self._condenseSectorTuples()

        print('Moving', len(tpls), 'sector items')

        ## transfer info
        self.dbc.executemany('UPDATE symbols SET sector=? WHERE exchange=? AND symbol=?', tpls)
        # self.dbc.executemany(f'UPDATE {self.getTableString("staging_symbol_info_d")} SET migrated=1 WHERE migrated <> ? AND exchange=? and symbol=?', tpls)

    def symbols_pullStagedFounded(self):
        tpls = self._condenseFoundedTuples()

        print('Moving', len(tpls), 'founded items')

        ## transfer info
        self.dbc.executemany('UPDATE symbols SET founded=? WHERE exchange=? AND symbol=?', tpls)
        # self.dbc.executemany(f'UPDATE {self.getTableString("staging_symbol_info_d")} SET migrated=1 WHERE migrated <> ? AND exchange=? and symbol=?', tpls)        


    ## end migrations ####################################################################################################################################################################
    ####################################################################################################################################################################
    ## limited use utility ####################################################################################################################################################################

    ## generally only used after VIX update dumps
    ## fill any data gaps with artificial data using last real trading day
    ## artificial 0 = real data
    ## artificial 1 = fake data
    ## artificial 2 = fake data for US market holiday
    def fillVIXHistoricalGaps(self, fillForNonUSMarkets=True, dryrun=False):
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
                holidays = MarketDayManager.getMarketHolidays(cdate.year)
                cyear = cdate.year
                if DEBUG: print('holidays for', cyear, holidays)

            ## actual gap checker
            if cdate != date.fromisoformat(data[dindex].period_date):
                artificial = 1
                if cdate in holidays:
                    if fillForNonUSMarkets:
                        artificial = 2
                    else:
                        if DEBUG: print('is holiday')
                        continue
                
                if not dryrun:
                    self.dbc.execute(stmt, (str(cdate), prevclose, prevclose, prevclose, prevclose, artificial))
                else: 
                    print(str(cdate), prevclose, artificial)
                gapsFilled += 1
                # if debugcount > 20: break
                pass
            else:
                prevclose = data[dindex].close
                dindex += 1
        
        print(gapsFilled, 'gaps filled')

    ## detects order of magnitude jumps in stock price from one day to next, that may be representative of a stock split
    def detectStockSplits(self, exchange=None, symbol=None, seriesType:SeriesType=SeriesType.DAILY, verbose=0):
        MULTIPLE = exchange or not symbol
        results = self.getSymbols(exchange, symbol)

        splitDates = {} if MULTIPLE else []
        if verbose > 0: print('Detecting {} stock splits'.format(seriesType.name))
        # for r in tqdm(results):
        for r in results:
            if (r.exchange, r.symbol) in unusableSymbols: continue

            data = self.dbc.execute('SELECT * from historical_data WHERE exchange=? AND symbol=? AND series_type=? ORDER BY period_date', (r.exchange, r.symbol, seriesType.name)).fetchall()

            for idx, d in enumerate(data):
                try:
                    ratio = d.close / data[idx+1].close
                    if ratio >= 2 or ratio <= 0.5:
                        if MULTIPLE:
                            try:
                                splitDates[d.period_date].append((r.exchange, r.symbol))
                            except KeyError:
                                splitDates[d.period_date] = [(r.exchange, r.symbol)]
                        else:
                            splitDates.append(d.period_date)

                        ## determine split
                        ratio = Decimal(ratio).as_integer_ratio()

                        if verbose > 0: 
                            print(r.exchange, r.symbol, '{} : {}'.format(math.ceil(ratio[0]*10)/10, math.ceil(ratio[1]*10)/10), d.period_date)
                            print('\t', d.close, '->', data[idx+2].close)                        

                except IndexError:
                    break

        return splitDates

    ## detects stock symbols which have excessive strings of artificial dates within the historical data which may be representative of damage caused by abherrant data prior to proper symbol IPO and later gap filling attempts
    def detectArtificiallyDamagedSymbols(self, exchange=None, symbol=None, seriesType:SeriesType=SeriesType.DAILY, verbose=0):
        results = self.getSymbols(exchange, symbol)

        damagedSymbols = []
        damageThresholdLength = 50
        if verbose > 0: print('Detecting damage for {} data'.format(seriesType.name))
        # for r in tqdm(results):
        for r in results:

            if r.exchange=='NYSE': continue

            if (r.exchange, r.symbol) in unusableSymbols: continue

            data = self.dbc.execute('SELECT * from historical_data WHERE exchange=? AND symbol=? AND series_type=? ORDER BY period_date', (r.exchange, r.symbol, seriesType.name)).fetchall()

            artificialStringLength = 0
            for d in data:
                if artificialStringLength > damageThresholdLength:
                    if verbose > 0: print('{} : {}'.format(r.exchange, r.symbol))
                    damagedSymbols.append((r.exchange, r.symbol))
                    break
                if d.artificial:
                    artificialStringLength += 1
                else:
                    artificialStringLength = 0

        return damagedSymbols        

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
            data = self.dbc.execute('SELECT * FROM historical_data WHERE exchange=? AND symbol=? AND series_type=?', (t.exchange, t.symbol, seriesType.name)).fetchall()
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

    ## generates initial rows for accuracy_last_updates and network_accuracies tables to track accuracy stats
    def setupAccuracyTables(self, nnid=None):
        lastupdates_stmt = 'INSERT OR IGNORE INTO accuracy_last_updates VALUES (?,?,?,?,?,?)'
        networkacc_stmt = 'INSERT OR IGNORE INTO network_accuracies(network_id, accuracy_type, subtype1, subtype2) VALUES (?,?,?,?)'
        tickers = self.getSymbols()
        for nn in self.getNetworks():
            if nnid and nnid != nn.id: continue
            for acctype in AccuracyAnalysisTypes:
                self.dbc.execute(lastupdates_stmt, (nn.id, acctype.value, 0, '0000-01-01', None, None))

            for t in tqdm(tickers):
                if t.symbol == '0E13': print(t)
                self.dbc.execute(networkacc_stmt, (nn.id, AccuracyAnalysisTypes.STOCK.value, t.exchange, t.symbol))

            for prectype in PrecedingRangeType:
                for cb in CorrBool:
                    self.dbc.execute(networkacc_stmt, (nn.id, AccuracyAnalysisTypes.PRECEDING_RANGE.value, prectype.value, cb.value))

    ## set all values back to defaults in the accuracy tracking related tables
    def resetAccuracyTables(self, nnid=None):
        lastupdates_stmt = 'UPDATE accuracy_last_updates SET data_count=0, min_date=\'0000-01-01\', last_exchange=NULL, last_symbol=NULL'
        networkacc_stmt = 'UPDATE network_accuracies SET sum=0, count=0'
        if nnid:
            lastupdates_stmt += ' WHERE network_id=' + str(nnid)
            networkacc_stmt += ' WHERE network_id=' + str(nnid)
        self.dbc.execute(lastupdates_stmt)
        self.dbc.execute(networkacc_stmt)

    ## https://en.wikipedia.org/wiki/Ticker_symbol#Canada
    def _determineAssetType(self, exchange: str, symbol: str, name: str, basic=False):
        symbol = symbol.lower()
        name = name.lower()
        if exchange == 'BATS':
            if basic: return 'Non-CS'
            else:
                pass
        elif exchange == 'NASDAQ':
            if basic and len(symbol) == 5:
                return 'Non-CS'
            lastchar = symbol[-1]
            if lastchar == 'a' and (len(symbol) == 5 or name.endswith('cl a') or name.endswith('cl. a')):
                if basic: return 'CLA'
                else:
                    pass
            elif lastchar == 'b' and (len(symbol) == 5 or name.endswith('cl b') or name.endswith('cl. b')):
                if basic: return 'CLB'
                else:
                    pass
            elif lastchar == 'c' and len(symbol) == 5:
                return 'NXSH'
            # elif lastchar == 'd':
            # elif lastchar == 'e': ## none at len(5)
            # elif lastchar == 'f':
            # elif lastchar == 'g': ## "notes due XXXX"
            # elif lastchar == 'h': ## "notes due XXXX"
            # elif lastchar == 'i': ## "notes due XXXX"
            # elif lastchar == 'j': ## none at len(5)
            # elif lastchar == 'l':
            # elif lastchar == 'm':
            # elif lastchar == 'n':
            # elif lastchar == 'f':
            # elif lastchar == 'o':
            elif lastchar == 'p' and (len(symbol) == 5 or ' pfd' in name or 'preferred' in name):
                if basic: return 'PFD'
                else:
                    pass
            # elif lastchar == 'q':
            elif lastchar == 'r' and (len(symbol) == 5 or name.endswith(' right') or name.endswith(' rights')):
                return 'RIGHT'
            # elif lastchar == 's':
            # elif lastchar == 't':
            elif lastchar == 'u' and (len(symbol) == 5 or ' unit' in name):
                return 'UNIT'
            # elif lastchar == 'v':
            elif lastchar == 'w' and (len(symbol) == 5 or name.endswith(' wt') or name.endswith(' wts')):
                return 'WT'
            elif lastchar == 'x' and len(symbol) == 5:
                return 'MF'
            # elif lastchar == 'y':
            # elif lastchar == 'z':


        elif exchange == 'NYSE':
            if basic and '-' in symbol or '.' in symbol or ' ' in symbol:
                return 'Non-CS'


        ## unable to determine based on last char, special code
        ## check for other indicators that it is a special symbol
        if 'cl a' in name or 'cl. a' in name or 'class a' in name:
            return 'CLA'
        elif name.endswith(' etf') or ' etf ' in name or 'indexetf' in name or 'vanguard' in name:
            return 'ETF'
        elif name.endswith(' etn'):
            if basic: return 'Non-CS'
            else: pass
        elif name.endswith(' ft'):
            if basic: return 'Non-CS'
            else: pass
        elif name.endswith(' fund') or ' fund ' in name or name.endswith(' fd') or ' fd ' in name:
            if basic: return 'Non-CS'
            else: pass
        elif name.endswith(' adr') or 'american depositary receipt' in name:
            if basic: return 'Non-CS'
            else: pass
        elif name.endswith(' ads') or 'american depositary share' in name or 'american depository share' in name or ' ads each' in name:
            if basic: return 'Non-CS'
            else: pass
        elif 'notes due' in name:
            if basic: return 'Non-CS'
            else: pass
        elif 'warrant' in name:
            if basic: return 'Non-CS'
            else: pass
        elif ' bond' in name:
            if basic: return 'Non-CS'
            else: pass
        elif ' unit' in name or 'common unit' in name:
            if basic: return 'Non-CS'
            else: pass
        elif ' index' in name:
            if basic: return 'Non-CS'
            else: pass
        elif ' due' in name:
            if basic: return 'Non-CS'
            else: pass
        elif ' pfd' in name or 'preferred' in name:
            if basic: return 'Non-CS'
            else: pass
        elif ' trust' in name:
            if basic: return 'Non-CS'
            else: pass
        elif ' right' in name:
            if basic: return 'Non-CS'
            else: pass
        elif '%' in name:
            if basic: return 'Non-CS'
            else: pass


        ## probably normal share, double check
        if 'ordinary share' in name or 'ord sh' in name or 'common stock' in name or 'common share' in name:
            return 'CS'

        ## some other wierd kind of share, e.g. proshares, ishares, victoryshares
        if 'share' in name:
            return 'Non-CS'

        return 'CS'


    ## BATS seems to be all non-CS
    def analyzePossibleSymbolAssetTypes(self, exchange=['NYSE','NASDAQ','NYSE MKT','NYSE ARCA']):
        exchange = asList(exchange)
        stmt = 'SELECT * FROM symbols WHERE (api_polygon=1 OR api_fmp=1 or api_alphavantage=1) '
        if exchange:
            stmt += self._andXContainsListStatement('exchange', exchange)
        stmt += ' ORDER BY symbol'

        res = self.dbc.execute(stmt).fetchall()
        symbolGroups = { e: {} for e in exchange }
        for s in tqdm(res, desc='Sorting symbols'):
            sdict = symbolGroups[s.exchange]
            try:
                for k,v in sdict.items():
                    if k in s.symbol and s.name.lower().startswith(v[0].name.split(' ')[0].lower()):
                        v.append(s)
                        raise BufferError
                sdict[s.symbol] = [s]
            except BufferError:
                pass

        return symbolGroups

    ## determines tickers that have stock splits that are less than a certain period apart, possibly indicating a problem with one of them
    def checkForDumpStockSplitsTooClose(self,period:timedelta=timedelta(days=90), onlyTickersWithData=True,  verbose=1):
        substmt = 'JOIN (SELECT DISTINCT exchange AS hexchange,symbol AS hsymbol FROM historical_data) ON exchange=hexchange AND symbol=hsymbol' if onlyTickersWithData else ''
        stmt = f'SELECT * FROM {self.getTableString("stock_splits_polygon_d")} {substmt} WHERE exchange <> "UNKNOWN" AND split_from <> split_to ORDER BY symbol, date'
        res = self.dbc.execute(stmt)
        cursym = ''
        lastdate = ''
        offendingTickers = []
        for r in res:
            if r.symbol != cursym:
                cursym = r.symbol
                lastdate = r.date
                continue
            diff = (date.fromisoformat(r.date) - date.fromisoformat(lastdate)).days
            if diff < period.days:
                if verbose > 0: print(r.exchange, r.symbol, lastdate, r.date)
                offendingTickers.append(r)
            lastdate = r.date
        return offendingTickers

# NYSE	LAIX	2022-03-04	14	1	0
# NYSE	LAIX	DAILY	2022-03-03	0.48	0.48	0.44	0.44	277293	0
# NYSE	LAIX	DAILY	2022-03-04	5.36	5.36	4.53	4.61	61399	0

    ## check if stock splits are garbage/duplicate/invalid and update status column
    def validateStockSplits(self, dryRun=False, verbose=0):
        stmt = 'SELECT * FROM stock_splits sp JOIN (SELECT DISTINCT exchange, symbol FROM historical_data) h ON sp.exchange = h.exchange AND sp.symbol = h.symbol WHERE sp.exchange <> ? AND sp.status = ?'
        tpl = ('UNKNOWN', 0)
        tickersToCheck = self.dbc.execute(stmt, tpl).fetchall()

        errorTickers = []
        ratioErrorTickers = []
        selectStmt = 'SELECT * FROM historical_data WHERE period_date >= ? AND period_date <= ? AND exchange = ? AND symbol = ? AND series_type=? ORDER BY period_date DESC LIMIT 2'
        updateStmt = 'UPDATE stock_splits SET status=? WHERE date=? AND exchange=? AND symbol=?'
        c=0
        for t in tqdm(tickersToCheck, desc='Validating stock splits') if verbose > 0 and not dryRun else tickersToCheck:
            tpl = (t.date, t.exchange, t.symbol)
            try:
                splitDayData, prevDayData = self.dbc.execute(selectStmt, ((date.fromisoformat(t.date)-timedelta(days=4)).isoformat(),)+tpl+(SeriesType.DAILY.name,)).fetchall()
                if splitDayData.period_date != t.date: raise ValueError
            except (ValueError, AttributeError):
            # except Exception as e:
                # print(e)
                # print(e)
                # exit()
                errorTickers.append(tpl)
                continue

            splitRatio = t.split_from / t.split_to
            # priceDiff = abs(splitDayData.open - prevDayData.close)
            priceDiff = splitDayData.open - prevDayData.close
            try: 
                multiplesOfChange = abs(min(prevDayData.close, splitDayData.open) / priceDiff)
                inverseMultiplesOfChange = 1 / multiplesOfChange
            except ZeroDivisionError: 
                multiplesOfChange = 0
                inverseMultiplesOfChange = 0
            expectedVsActualError = abs(1-(prevDayData.close * splitRatio / splitDayData.open))

            ## actual next day value is near to expected value
            passCriteria1 = expectedVsActualError <= 0.2
            ## orders of magnitude of change in price is near to expected based on the split ratio
            passCriteria2 = multiplesOfChange > splitRatio*1/3 and multiplesOfChange < splitRatio*2#(1+(2/3))
            passCriteria3 = inverseMultiplesOfChange > splitRatio*1/3 and inverseMultiplesOfChange < splitRatio*2#(1+(2/3))
            ## tiny splits may only be detectable via the direction of price change
            splitRatioLessThanDouble = splitRatio < 2 and splitRatio > 0.5
            passCriteria4_1 = splitRatio > 1 and priceDiff > 0
            passCriteria4_2 = splitRatio < 1 and priceDiff < 0
            passCriteria4 = splitRatioLessThanDouble and (passCriteria4_1 or passCriteria4_2)

            if not passCriteria1 and not passCriteria2 and not passCriteria3 and not passCriteria4:
                print(passCriteria1,passCriteria2,passCriteria3,passCriteria4)
                print(t, 'invalid')
                # print('bef aft', prevDayData.close, splitDayData.open)
                print('bef', prevDayData.close, prevDayData)
                print('aft', splitDayData.open, splitDayData)
                print('expectedVsActualError', expectedVsActualError)
                print('splitRatio', splitRatio)
                print('multiplesOfChange', splitRatio*1/3, multiplesOfChange, inverseMultiplesOfChange, splitRatio*2)#(1+(2/3)))

                if prevDayData.close == splitDayData.open:
                    self.dbc.execute(updateStmt, (-1,) + tpl)
                    c+=1
            else:
                continue
                print(passCriteria1,passCriteria2,passCriteria3,passCriteria4)
                print(t, 'valid')
                print('bef aft', prevDayData.close, splitDayData.open)
                print('expectedVsActualError', expectedVsActualError)
                print('splitRatio', splitRatio)
                print('multiplesOfChange', multiplesOfChange)

            continue

            # historicalRatio = splitDayData.open / prevDayData.close
            # error = abs((splitRatio / historicalRatio)-1)
            # error = 1 - (splitDayData.open - prevDayData.close) / splitDayData.open + 1 / splitRatio
            # error = abs(1-((prevDayData.close * splitRatio) / splitDayData.open))
            error = abs(1-(prevDayData.close * splitRatio / splitDayData.open))

            if error > 0.2:
                priceDiff = abs(splitDayData.open - prevDayData.close)
                ## within some multiples threshold
                if priceDiff / prevDayData.close > splitRatio * 1/3:
                    pass
                else:
                    print(t, 'invalid')
                    print('err', error)
                    print('bef aft', prevDayData.close, splitDayData.open)
                    print('splitRatio', splitRatio)
                    print('actual mult', priceDiff / prevDayData.close)

                if dryRun:
                    # if error < 0.5:
                    #     print(t, 'invalid')
                    #     print('splitRatio', splitRatio)
                    #     # print('historicalRatio', historicalRatio, splitDayData.open, prevDayData.close)
                    #     print('diff', prevDayData.close, splitDayData.open, splitDayData.open - prevDayData.close)
                    #     print('error', error)
                    # else:
                    #     pass
                    pass
                else:
                    self.dbc.execute(updateStmt, (-1,) + tpl)
                ratioErrorTickers.append((t, prevDayData.close, splitDayData.open))
            
            if dryRun:
                # print(tpl, 'valid')
                pass
            else:
                self.dbc.execute(updateStmt, (1,) + tpl)

        print(c,'tickers marked as -1')
        if verbose > 0 and not dryRun:
            print('Error tickers', errorTickers)
            print('Ratio errors', ratioErrorTickers)

        ## symbols loaded from FMP? came with a .TO suffix, so this should clean them up by either merging them with their non-suffixed existing tickers and delete the suffixed row, or update the symbol if there is no non-suffixed match. 
        ## should run a foreign key constraint check and cleanup of last_updates after since ON DELETE CASCADE does not appear work:
        ##      DELETE FROM last_updates WHERE rowid IN (SELECT rowid FROM pragma_foreign_key_check('last_updates'));
        def mergeAndEliminateDotTOSymbols(self, verbose=0):
            def getAPIVal(a1, a2):
                if a1==a2: return a1
                if a1==0: return a2
                if a2==0: return a1
                return 0

            tickers = self.dbc.execute('SELECT * FROM symbols WHERE exchange=? AND symbol LIKE ?', ('TSX','%.TO')).fetchall()

            for idx, t in enumerate(tickers):
                massagedSymbol = t.symbol.replace('.TO','').replace('-','.')
                res = d.getSymbols('TSX', massagedSymbol)

                if len(res) == 0:
                    if verbose > 0: print('missing .TO match',t)
                    d.dbc.execute('UPDATE symbols SET symbol=? WHERE exchange=? AND symbol=?', (massagedSymbol, 'TSX', t.symbol))
                    if verbose > 0: print('migrated', massagedSymbol)
                elif len(res) > 1:
                    if verbose > 0: print('too many results', t)
                else:
                    res = res[0]
                    ## combine
                    newrow = (
                        ## name
                        res.name.strip() if len(res.name.strip()) > len(t.name.strip()) else t.name.strip(),
                        ## asset_type
                        shortc(res.asset_type, t.asset_type),
                        ## api_alphavantage
                        getAPIVal(res.api_alphavantage, t.api_alphavantage),
                        ## api_polygon
                        getAPIVal(res.api_polygon, t.api_polygon),
                        ## google_topic_id
                        shortc(res.google_topic_id, t.google_topic_id),
                        ## sector
                        shortc(res.sector, t.sector),
                        ## industry
                        shortc(res.industry, t.industry),
                        ## founded
                        shortc(res.founded, t.founded),
                        ## api_fmp
                        getAPIVal(res.api_fmp, t.api_fmp),
                        ## exchange
                        'TSX',
                        ## symbol
                        res.symbol,
                    )

                    d.dbc.execute('UPDATE symbols SET name=?,asset_type=?,api_alphavantage=?,api_polygon=?,google_topic_id=?,sector=?,industry=?,founded=?,api_fmp=? WHERE exchange=? AND symbol=?', newrow)
                    d.dbc.execute('DELETE FROM symbols WHERE exchange=? AND symbol=?', ('TSX', t.symbol))

                    if verbose > 0: 
                        print(t)
                        print(res)
                        print('new:',newrow)
                
        ## check for symbol and symbol.TO collisions in historical data
        # tickers = d.getSymbols('TSX')
        # dottotickerswithdata = []
        # for t in tickers:
        #     if '.TO' in t.symbol:
        #         data = d.getStockData(t.exchange, t.symbol)
        #         if len(data) > 0:
        #             print(t.exchange,t.symbol,len(data))
        #             dottotickerswithdata.append(t)

        # for t in dottotickerswithdata:
        #     for subt in tickers:
        #         if subt.symbol == t.symbol.replace('.TO',''):
        #             print('collision', t.exchange, t.symbol)

        ################################################################

    ## determines sum of all interests (0-100) in given period
    def analyzeGoogleInterests_totalInterestInCollectionPeriod(self, itype:InterestType=InterestType.DAILY, period=timedelta(weeks=34)):
        direction = Direction.DESCENDING

        symbollist = self.getSymbols(googleTopicId=SQLHelpers.NOTNULL)
        print(f'Checking {len(symbollist)} symbols')    
        for s in symbollist:
            tickergid = (s.exchange, s.symbol, s.google_topic_id)

            ginterests = self.getGoogleInterests(s.exchange, s.symbol, itype=itype, raw=True)
            if ginterests:

                directionmodifier = -1 if direction == Direction.DESCENDING else 1

                ind = len(ginterests) -1
                periodtotals = []
                startdate = date.fromisoformat(ginterests[-1].date)
                try:
                    while True:
                        periodtotal = []
                        enddate = startdate + (period * directionmodifier)
                        while date.fromisoformat(ginterests[ind].date) != enddate + (timedelta(days=1) * directionmodifier):
                            periodtotal.append(ginterests[ind].relative_interest)
                            ind += directionmodifier
                        
                        periodtotals.append(periodtotal)
                        startdate = enddate
                        break
                except IndexError:
                    pass

                res = []
                for perd in periodtotals:
                    zerocount = 0
                    for p in perd:
                        if p == 0: zerocount += 1
                    res.append(('sum',sum(perd),0,zerocount,'avg',sum(perd)/len(perd),'rel0',zerocount/len(perd)))

                print(*tickergid, *res)

    ## correcting issue where only first day of week/month has WEEKLY/MONTHLY Google Interest data, should be duplicated for all days in week/month
    def fillOutXlyGIData(self, itype=InterestType.MONTHLY, dryrun=False):
        monthly = itype == InterestType.MONTHLY
        symbols = self.getSymbols()
        for s in symbols:
            print('Checking', s.exchange, s.symbol)
            gidata = self.getGoogleInterests(s.exchange, s.symbol, itype=itype, raw=True)
            if len(gidata) > 2: ## has more than first and last dates
                if gidata[-1 if monthly else -2].date != '2022-09-30': ## week/month dates not already filled out
                    print('Fixing', s.exchange, s.symbol)
                    for gidx in range(len(gidata)):
                        curdate = date.fromisoformat(gidata[gidx].date)
                        if gidx != len(gidata) - 1: ## last
                            ## further integrity check next data point is in next week/month
                            if monthly and curdate.month == date.fromisoformat(gidata[gidx+1].date).month:
                                    raise IndexError(f'GIDX-(monthly):{gidx} - {curdate.month} -> {date.fromisoformat(gidata[gidx+1].date).month}')
                            elif curdate + timedelta(days=1) == date.fromisoformat(gidata[gidx+1].date):
                                    raise IndexError(f'GIDX-(weekly):{gidx} - {curdate} -> {date.fromisoformat(gidata[gidx+1].date)}')

                        
                        rinterest = gidata[gidx].relative_interest
                        loopdate = curdate + timedelta(days=1)
                        while (loopdate.month == curdate.month) if monthly else (loopdate.weekday() != 6):
                            if not dryrun: self.insertRawGoogleInterest(s.exchange, s.symbol, itype, loopdate, rinterest)
                            else: print('Inserting', s.exchange, s.symbol, itype, loopdate, rinterest)
                            loopdate += timedelta(days=1)
        self.commit()


    ## builds a DB copy with just enough info for Google Interests collector to run and input data to
    def buildGIDBCopy(self, verbose=1):
        dest_db_path = os.path.join(path, f'data\\gidbcopy-{str(int(time.time()))}.db')
        destination_connect, destination_cursor = _getDBHandles(dest_db_path)

        destination_cursor.execute('PRAGMA foreign_keys=0')

        ## write required tables to new DB
        requiredmaintablesTuple = ('main', ['symbols', 'historical_data'])
        requireddumptablesTuple = (self.dumpDBAlias, ['google_interests_d'])
        for dbalias, tables in [requiredmaintablesTuple, requireddumptablesTuple]:
            src_tables = self.dbc.execute(f'SELECT * from {dbalias}.sqlite_master WHERE type=\'table\' AND tbl_name IN ({ generateCommaSeparatedQuestionMarkString(tables) })', tables).fetchall()
            for table in src_tables:
                try:
                    destination_cursor.execute(table['sql'])
                except sqlite3.OperationalError as e:
                    if verbose>=1: print(f'Operational Error: {e}')
                    pass

        ## write only symbols with Google Topic IDs
        src_tickers = self.getSymbols(googleTopicId=SQLHelpers.NOTNULL)
        for t in src_tickers:
            destination_cursor.execute(f'INSERT INTO symbols VALUES ({ generateCommaSeparatedQuestionMarkString(src_tickers[0]) })', list(t.values()))

        # write only max and min dated data for each symbol for google_interests and historical_data tables
        for t in tqdmLoopHandleWrapper(src_tickers, verbose, desc='Transfering stock and GI data'):
            histdata = self.getStockData(t.exchange, t.symbol, SeriesType.DAILY)
            if len(histdata) == 0:
                if verbose>=1: print(f'No stock data, deleting {t.exchange}:{t.symbol}')
                destination_cursor.execute('DELETE FROM symbols WHERE exchange=? and symbol=?', (t.exchange, t.symbol))
                continue
            stmt = f'INSERT INTO historical_data VALUES ({ generateCommaSeparatedQuestionMarkString(histdata[0]) })'
            destination_cursor.execute(stmt, list(histdata[0].values()))
            destination_cursor.execute(stmt, list(histdata[-1].values()))

            # gidata = self.getGoogleInterests(t.exchange, t.symbol, raw=True)
            for itype in InterestType:
                maxStream = self.getMaxGoogleInterestStream(t.exchange, t.symbol, itype=itype)
                gidata = self.getGoogleInterests(exchange=t.exchange, symbol=t.symbol, itype=itype, stream=maxStream, raw=True)
                if len(gidata) > 0:
                    stmt = f'INSERT INTO google_interests_d VALUES ({ generateCommaSeparatedQuestionMarkString(gidata[0]) })'
                    destination_cursor.execute(stmt, list(gidata[0].values()))
                    destination_cursor.execute(stmt, list(gidata[-1].values()))
        
        destination_connect.commit()
        destination_connect.close()

        ## for batch script
        sys.stdout.write(dest_db_path) 
        sys.stdout.write('\n')

    ## take stock of data from DB copy used for collecting Google Interests data
    def analyzeGIDBCopy(self, src_db_path):
        source_connect, source_cursor = _getDBHandles(src_db_path)

        ## DB copy should all have topic IDs, stock data, and probably some GI data already
        symbolerrors = source_cursor.execute('SELECT * FROM symbols WHERE google_topic_id IS NULL').fetchall()
        for s in symbolerrors:
            print (f'{s.exchange}:{s.symbol} had topic ID removed', end=' ')
            gidata = source_cursor.execute('SELECT * FROM google_interests_d WHERE exchange=? AND symbol=?', (s.exchange, s.symbol)).fetchall()
            if len(gidata) == 0:
                print('and no data')
            else:
                if len(gidata) < 3:
                    print('and no data collected')
                else:
                    print('and had some more data collected')
                print('GI:', gidata[0].date, '->', gidata[-1].date)

            hdata = source_cursor.execute('SELECT * FROM historical_data WHERE exchange=? and symbol=?', (s.exchange, s.symbol)).fetchall()
            print('SD:', hdata[0].period_date, '->', hdata[-1].period_date)

        # print()
        # symbols = source_cursor.execute('SELECT * FROM symbols').fetchall()
        # for s in symbols:
        #     gidata = source_cursor.execute('SELECT * FROM google_interests_d WHERE exchange=? AND symbol=?', (s.exchange, s.symbol)).fetchall()
        #     print (f'{s.exchange}:{s.symbol} - f{len(gidata)} data points')

        source_connect.close()

    ## import Google Interests data from a DB copy from elsewhere (e.g. EC2 instance)
    def importFromGIDBCopy(self, src_db_path, interestType: InterestType=None, dryrun=False, verbose=1):
        destination_cursor = self.dbc
        source_connect, source_cursor = _getDBHandles(src_db_path)

        ## update deleted topic IDs
        symbolerrors = source_cursor.execute('SELECT * FROM symbols WHERE google_topic_id IS NULL').fetchall()
        for s in symbolerrors:
            if dryrun:  print('Deleting google_topic_id for', s.exchange, s.symbol)
            else:       destination_cursor.execute('UPDATE symbols SET google_topic_id=NULL WHERE exchange=? AND symbol=?', (s.exchange, s.symbol))
        if verbose>=1: print(f'Deleted {len(symbolerrors)} topic IDs')

        ## transfer GI data
        gidata = source_cursor.execute(f'''
            SELECT * FROM google_interests_d 
            {" WHERE type=? " if interestType else ""} 
            ORDER BY exchange, symbol, date {", type" if not interestType else ""}
        ''', (interestType.name,) if interestType else ()).fetchall()
        for g in tqdm(gidata, desc='Inserting data') if verbose > 0 else gidata:
            if dryrun:  print('Inserting values', list(g.values()))
            else:       destination_cursor.execute(f'INSERT OR IGNORE INTO {self.getTableString("google_interests_d")} VALUES ({ generateCommaSeparatedQuestionMarkString(gidata[0]) })', list(g.values()))
        if verbose>=1: print(f'Inserted {len(gidata)} data points')

        self.commit()
        source_connect.close()

    ## end limited use utility ####################################################################################################################################################################
    ####################################################################################################################################################################
    




def printSectorColumnInfos(dbm: DatabaseManager):
    ## compare sectors from temp table
    stmt = 'SELECT DISTINCT {}_sector' + f' FROM {dbm.getTableString("staging_symbol_info_d")} ORDER BY 1'
    # ds_fmp = [d['fmp_sector'] for d in d.dbc.execute(stmt.format('fmp')).fetchall()]
    # ds_polygon = [d['polygon_sector'] for d in d.dbc.execute(stmt.format('polygon')).fetchall()]
    # ds_alphavantage = [d['alphavantage_sector'] for d in d.dbc.execute(stmt.format('alphavantage')).fetchall()]
    # dss = [ds_fmp, ds_polygon, ds_alphavantage]
    dss = []
    for a in apiList:
        dss.append([d[a + '_sector'] for d in dbm.dbc.execute(stmt.format(a)).fetchall()])


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
    stmt = f'SELECT count(*) as count FROM {dbm.getTableString("staging_symbol_info_d")} WHERE ' + '{}_sector=?'
    counts = []
    for ac in range(len(apiList)):
        dcl = []
        for dc in dss[ac]:
            dcl.append(dbm.dbc.execute(stmt.format(apiList[ac]), (dc,)).fetchone()['count'])
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

    opts, kwargs = parseCommandLineOptions()
    if opts.function:
        getattr(d, opts.function)(**kwargs)
    else:

        d.getEarningsDate(symbol='test', inputDate=SQLHelpers.NOTNULL, earningsDate=['2023-01-01', '2022-09-09'])
        exit()

        # updatedrows = 0
        # for col in stagingEarningsDatesSnakeCaseTableColumns:
        #     stmt = f'UPDATE {self.getTableString("staging_earnings_dates")} SET {col}=null WHERE ({col}=\'\' OR {col}=\'N/A\')'
        #     d.dbc.execute(stmt)
        #     updatedrows += d.dbc.rowcount
        # print(updatedrows)

        ## graph earnings dates
        # edata = d.dbc.execute(f'SELECT * FROM {self.getTableString("staging_earnings_dates")}').fetchall()
        edata = flatten([d.getDumpEarningsDates(eapi, symbol='AA') for eapi in EarningsCollectionAPI])
        uniquetickerdates = set()
        for e in tqdm(edata, desc='Creating tuples'):
            uniquetickerdates.add((shortcdict(e, 'exchange', 'NASDAQ'), e.symbol, e.earnings_date))
        
        daybuckets = [0 for x in range(365)]
        leapyeardaybuckets = [0 for x in range(366)]
        for _,_,edate in tqdm(uniquetickerdates, desc='Converting to days'):
            dt = date.fromisoformat(edate)
            yday = dt.timetuple().tm_yday -1
            if calendar.isleap(dt.year): leapyeardaybuckets[yday] += 1
            else: daybuckets[yday] += 1
        
        zerocountdts = []
        for i in tqdm(range(len(leapyeardaybuckets)), desc='Checking'):
            if leapyeardaybuckets[i] == 0:
                offset = 0
                if i >= 31+28:
                    offset=1
                if daybuckets[i-offset] == 0:
                    zerocountdts.append(i)

        # print(zerocountdts)


        import matplotlib.pyplot as plt
        fig = plt.figure()
        ax = fig.add_axes([0,0,1,1])
        ax.bar([i for i in range(1,len(leapyeardaybuckets)+1)], [daybuckets[i + (0 if i < 31+28 else -1)] + leapyeardaybuckets[i] for i in range(len(leapyeardaybuckets))])
        plt.show()

        exit()

        pass
        # nd = d.getLatestNasdaqEarningsCollectionDate()
        # d._generateDatabaseAnnotationObjectsFile()
        # t = d.getNetworks()
        # res = d.getHistoricalStartEndDates(exchange='NASDAQ')
        # print(res)

        ############
        # checking uniqueness of symbols retrieved for earnings date data dumps
        ## appears marketwatch symbols are covered by nasdaq and yahoo APIs, only a few OTCBB symbols are not but none of the 4 stock data APIs can get them
        ## nasdaq is mostly covered by yahoo, only ~375 symbols are unique
        nasdaqtablesymbols = [r.symbol for r in d.dbc.execute(f'select distinct symbol from {d.getTableString("earnings_dates_nasdaq_d")}').fetchall()]
        marketwatchtablesymbols = [r.symbol for r in d.dbc.execute(f'select distinct symbol from {d.getTableString("earnings_dates_marketwatch_d")}').fetchall()]
        yahootablesymbols = [r.symbol for r in d.dbc.execute(f'select distinct symbol from {d.getTableString("earnings_dates_yahoo_d")}').fetchall()]

        print('nasdaq vs marketwatch uniques')
        nasdaquniques = []
        marketwatchuniques =[]
        for s in nasdaqtablesymbols:
            if s not in marketwatchtablesymbols:
                nasdaquniques.append(s)
        for s in marketwatchtablesymbols:
            if s not in nasdaqtablesymbols:
                marketwatchuniques.append(s)
        print('nasdaquniques:', len(nasdaquniques))
        print('marketwatchunqies:', len(marketwatchuniques))
        print('shared:', len(nasdaqtablesymbols) + len(marketwatchtablesymbols) - len(nasdaquniques) - len(marketwatchuniques))
        print()

        print('nasdaq vs yahoo uniques')
        y = Yahoo()
        exchaliasdict = d.getAliasesDictionary()
        nasdaquniques = []
        yahoouniques =[]
        for s in nasdaqtablesymbols:
            if s not in yahootablesymbols:
                nasdaquniques.append(s)
        for s in yahootablesymbols:
            if s not in nasdaqtablesymbols:
                yahoouniques.append(s)

        print('nasdaquniques:', len(nasdaquniques))
        print('yahoounqies:', len(yahoouniques))
        print('shared:', len(nasdaqtablesymbols) + len(yahootablesymbols) - len(nasdaquniques) - len(yahoouniques))
        print('nasdaquniques', nasdaquniques)

        for u in [sobj['symbol'] for sobj in nasdaquniques]:
            tickers = d.getSymbols(symbol=u)
            for ti in tickers:
                for k,v in ti.items():
                    if k.startswith('api') and v == 1:
                        print(ti)
                        break
        print()

        print('marketwatch vs yahoo uniques')
        marketwatchuniques = []
        yahoouniques =[]
        for s in marketwatchtablesymbols:
            if s not in yahootablesymbols:
                marketwatchuniques.append(s)
        for s in yahootablesymbols:
            if s not in marketwatchtablesymbols:
                yahoouniques.append(s)
        print('marketwatchuniques:', len(marketwatchuniques))
        print('yahoounqies:', len(yahoouniques))
        print('shared:', len(marketwatchtablesymbols) + len(yahootablesymbols) - len(marketwatchuniques) - len(yahoouniques))
        print()


        print('marketwatch vs nasdaq+yahoo uniques')
        marketwatchuniques = []
        nasdaqyahoouniques =[]
        for s in marketwatchtablesymbols:
            if s not in yahootablesymbols and s not in nasdaqtablesymbols:
                marketwatchuniques.append(s)
        for s in yahootablesymbols + nasdaqtablesymbols:
            if s not in marketwatchtablesymbols:
                nasdaqyahoouniques.append(s)
        print('marketwatchuniques:', len(marketwatchuniques))
        print('nasdaqyahoounqies:', len(nasdaqyahoouniques))
        print('shared:', len(marketwatchtablesymbols) + len(yahootablesymbols) + len(nasdaqtablesymbols) - len(marketwatchuniques) - len(nasdaqyahoouniques))
        print('marketwatchuniques', marketwatchuniques)

        for mwu in [sobj['symbol'] for sobj in marketwatchuniques]:
            tickers = d.getSymbols(symbol=mwu)
            for ti in tickers:
                for k,v in ti.items():
                    if k.startswith('api') and v == 1:
                        print(ti)
                        break

        print('|')        

        exit()
        ###########
        # res = d.dbc.execute('select * from symbols where exchange=? and (api_polygon=1 or api_fmp=1 or api_alphavantage=1 or api_neo=1)', ('NYSE ARCA',)).fetchall()
        # res = d.dbc.execute('select * from symbols where (api_polygon=1 or api_fmp=1 or api_alphavantage=1 or api_neo=1) and exchange in (select distinct exchange from historical_data)').fetchall()
        # for r in res:
        #     # if not d._determineAssetType(r.exchange, r.symbol, r.name, basic=True):
        #     #     print(r.exchange, r.symbol, r.name)
        #     d.dbc.execute('update symbols set asset_type=? where exchange=? and symbol=?', (d._determineAssetType(r.exchange, r.symbol, r.name, basic=True), r.exchange, r.symbol))
        #     # print(r.exchange, r.symbol, r.name)
        #     # print(d._determineAssetType(r.exchange, r.symbol, r.name, basic=True))


        ## check if any 100 daily dates are within the same week, which will cause problems when framing using weekly and monthly data
        # gidata = d.dbc.execute('select * from google_interests_raw where relative_interest=100 and type=\'DAILY\' order by exchange,symbol,date').fetchall()
        # curticker = None
        # lastdate = None
        # count=0
        # print('gidata', len(gidata))
        # for g in gidata:
        #     if curticker != (g.exchange, g.symbol):
        #         curticker = (g.exchange, g.symbol)
        #     else:
        #         curdate = date.fromisoformat(g.date)
        #         if (curdate - lastdate).days < 7:
        #             if (curdate.weekday() + 1) % 7 > (lastdate.weekday() + 1) % 7:
        #                 print(curticker, g.date, lastdate.isoformat())
        #                 count+=1
        #                 # d.dbc.execute('delete from google_interests_raw where exchange=? and symbol=? and type=?', (g.exchange, g.symbol, InterestType.DAILY.name))
        #     lastdate = date.fromisoformat(g.date)
        # print(count, 'found with close 100 dates')

        
        # gapi = GoogleAPI()
        # for s in tqdm(['BATRA','CLSN', 'FMTX', 'XLRN', 'ZGNX', 'ZIXI']):
        #     # ex = s.exchange.replace(' ','')
        #     kw = 'NASDAQ' + ':' + s
        #     topics = gapi.suggestions(kw)
        #     for t in topics:
        #         print(t)
        #         if t['type'] == 'Topic' and t['title'] == kw:
        #             # self.dbc.execute(stmt, (t['mid'], s.exchange, s.symbol))
        #             # topicsFound.append(kw)
        #             print(kw, t['mid'])


        ## deleting google interest data under conditions, e.g. interest = 100 for dates past threshold 2022-09-30
        # src_tickers = []
        # messedupgidatatickers = d.dbc.execute('select DISTINCT exchange,symbol from google_interests_raw where date>=\'2022-10-01\' and type=\'DAILY\'').fetchall()
        # for t in messedupgidatatickers:
        #     src_tickers.append(d.dbc.execute('SELECT * FROM symbols WHERE exchange=? AND symbol=?', (t.exchange, t.symbol)).fetchone())
        # for t in src_tickers:
        #     # dest_cursor.execute(f'INSERT INTO symbols VALUES ({getValueQS(src_tickers[0])})', list(t.values()))
        #     d.dbc.execute('DELETE FROM google_interests_raw WHERE exchange=? AND symbol=? AND type=\'DAILY\' and date>=\'2022-10-01\'', (t.exchange, t.symbol))
        #     print(t.exchange, t.symbol)
        #########################################################################################################


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


    # print(d.getFinancialData('BATS','CBOE'))



        d.updateCalculatedTechnicalIndicatorData()

        pass

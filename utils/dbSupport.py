
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import pickle, re, sqlite3
from enum import Enum
from datetime import datetime
from typing import List, Tuple

from constants.enums import NormalizationGroupings, SQLHelpers
from constants.values import normalizationColumnPrefix, unusableSymbols, tab
from managers.configManager import StaticConfigManager
from structures.sql.sqlArgumentObj import SQLArgumentObj
from structures.sql.sqlOrderObj import SQLOrderObj
from utils.other import parseCommandLineOptions
from utils.support import asList, recdotdict, recdotlist, shortc, shortcdict

mainDBAlias = 'main'
computedDBAlias = 'computeddbalias'
dumpDBAlias = 'dumpdb'

def recdotdict_factory(cursor, row):
    '''for SQLite connect.row_factory'''
    retdict = {}
    for idx, col in enumerate(cursor.description):
        if col[0] == 'timestamp' and re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}', shortc(row[idx], '')):
            retdict[col[0]] = datetime.strptime(row[idx], '%Y-%m-%d %X')
        elif col[0].startswith('pickled'):
            retdict[col[0]] = pickle.loads(row[idx])
        else: retdict[col[0]] = row[idx]
    return recdotdict(retdict)

def processDBQuartersToDicts(qlist):
    createQuarterObj = lambda rw: { 'period': rw.period, 'quarter': rw.quarter, 'filed': rw.filed, 'nums': { rw.tag: rw.value }}
    ret = []
    curquarter = createQuarterObj(qlist[0])
    for r in qlist[1:]:
        if curquarter['period'] != r.period:
            ret.append(curquarter)
            curquarter = createQuarterObj(r)
        else:
            curquarter['nums'][r.tag] = r.value
    ret.append(curquarter)

    return recdotlist(ret)

def convertToCamelCase(string):
    '''example_string_text -> exampleStringText'''
    ret = ''
    capitalizeCurrent = False
    for char in string:
        if capitalizeCurrent: ret += str(char).capitalize()
        elif char != '_': ret += char
        capitalizeCurrent = char == '_'
    return ret

def convertToPascalCase(string):
    '''example_string_text -> ExampleStringText'''
    ret = convertToCamelCase(string)
    return str(ret[0]).capitalize() + ret[1:]

def convertToSnakeCase(arg):
    '''exampleStringText -> example_string_text\n
       for acronyms this conversion is one-way'''

    if isinstance(arg, list):
        if arg and isinstance(arg[0], dict):
            for a in arg:
                for k in list(a.keys()):
                    snkk = convertToSnakeCase(k)
                    if k != snkk:
                        ## i.e. not in snake case, need to replace
                        a[snkk] = a[k]
                        del a[k]
            return arg
        else:
            return [convertToSnakeCase(a) for a in arg]

    ## otherwise arg is a normal string
    words = []
    char: str
    for char in arg:
        if len(words) == 0 or char.isupper(): words.append(char.lower())
        else: words[-1] += char
    
    ret = ''
    for windx,w in enumerate(words):
        if len(ret) == 0: ret += w
        elif len(w) == 1 and len(words[windx-1]) == 1: ret += w
        else: ret += f'_{w}'

    return ret

def isNormalizationColumn(c):
    return str(c).startswith(normalizationColumnPrefix)

def generateCommaSeparatedQuestionMarkString(val):
    if hasattr(val, '__len__'): val = len(val)
    if type(val) != int: raise ValueError('Must be an integer')
    return ','.join(('?',) * val)

def combineSQLStatementAndArguments(stmt, args=[]):
    '''replaces '?'s with the actual argument values'''

    if args:
        for a in args:
            stmt = stmt.replace('?', a, 1)
    return stmt

def parseNormalizationColumn(c) -> Tuple[NormalizationGroupings, str]:
    '''splits a raw normalization column into its grouping enum and snake-case column name'''

    csplit = c.split('_')
    if not isNormalizationColumn(csplit[0]): raise ValueError('Not a normalization column')

    normalizationGrouping = NormalizationGroupings[str(csplit[1]).upper()]
    columnName = '_'.join(csplit[2:])

    return normalizationGrouping, columnName

def generateExcludeTickersSnippet(tickerList, alias=None):
    '''returns "exchange||symbol NOT IN (...)" snippet for SQL WHERE clause'''
    aliasString = f'{alias}.' if alias else ''
    tickersPipedPairString = ','.join([f"'{exchange}||{symbol}'" for exchange, symbol in tickerList])
    return f" {aliasString}exchange||{aliasString}symbol NOT IN ({tickersPipedPairString})"

def generateExcludeUnusableTickersSnippet(alias=None):
    return generateExcludeTickersSnippet(unusableSymbols, alias)

def generateSQLConditionSnippet(key, value, tableAlias=None):
    if value is None: return '', []

    tableAlias = f'{tableAlias}.' if tableAlias else ''
    if type(value) == SQLHelpers:
        return f' {tableAlias}{key} is {value.value} ', []
    elif type(value) == SQLArgumentObj:
        value: SQLArgumentObj
        return f' ? {value.modifier.sqlsymbol} {tableAlias}{key} ', [value.value]
    else:
        if issubclass(value.__class__, Enum): value = value.name
        vlist = asList(value)
        return f' {tableAlias}{key} in ({",".join(["?" for x in range(len(vlist))])}) ', vlist

def generateAllSQLConditionSnippets(tableAlias=None, **kwargs):
    snippets = []
    args = []
    for argKey, argVal in kwargs.items():
        if argVal is None: continue
        snippet, snpargs = generateSQLConditionSnippet(argKey, argVal, tableAlias)
        snippets.append(snippet)
        if snpargs: args.extend(snpargs)
    return snippets, args

def generateSQLSuffixStatementAndArguments(excludeKeys=[], tableAlias=None, **kwargs):
    '''converts arguments (passed to a DBM SQL GET function) into the appropriate WHERE statement; including order, group by'''

    # excludeKeys = ['self', 'kwargs', 'table', 'exclude_keys'] + [convertToSnakeCase(k) for k in asList(shortcdict(kwargs, 'excludeKeys', []))]
    ## remove unnecessary keys
    excludeKeys = ['self', 'kwargs'] + asList(excludeKeys)
    for exk in excludeKeys:
        if exk in kwargs.keys(): del kwargs[exk]

    ## extract and generate order by statement
    orderByStmt = ''
    orderbys: List[SQLOrderObj] = asList(shortcdict(kwargs, 'orderBy', []))
    if orderbys:
        # orderByStmt = f' ORDER BY {",".join([f"{ob.column} {ob.modifier.value}" for ob in orderbys])} '
        oblist = []
        for ob in orderbys:
            if type(ob) == str:
                col = ob
                mod = ''
            else:
                col = ob.column
                mod = ob.modifier.value
            oblist.append(f'{col} {mod}')
        orderByStmt = f' ORDER BY {",".join(oblist)}'
        del kwargs['orderBy']
    
    ## extract and generate group by statement
    groupByStmt = ''
    groupbys = asList(shortcdict(kwargs, 'groupBy', []))
    if groupbys:
        groupByStmt = f' GROUP BY {",".join(groupbys)}'
        del kwargs['groupBy']

    ## extract and generate limit statement
    limitStmt = ''
    if shortcdict(kwargs, 'limit') is not None:
        limitStmt = f' LIMIT {str(kwargs["limit"])}'
        del kwargs['limit']

    ## process remaining kwargs, dropping any that are None
    processedkwargs = {}
    for k,v in kwargs.items():
        k = convertToSnakeCase(k)
        # if k not in excludeKeys and v is not None:
        if k not in excludeKeys and v is not None:
            processedkwargs[k] = v

    additions = []
    args = []

    ## add all column-keyword args to the query
    snippets, snpargs = generateAllSQLConditionSnippets(tableAlias=tableAlias, **processedkwargs)
    additions.extend(snippets)
    args.extend(snpargs)

    stmt = f' {groupByStmt} {orderByStmt} {limitStmt} '
    rtargs = []
    if additions:
        stmt = f" WHERE {' AND '.join(additions)} " + stmt
        rtargs.extend(args)

    return stmt, rtargs

def _dbGetter(table, sqlColumns='*', onlyColumn_asList=None, rawStatement=False, **kwargs):
    '''generalized SELECT statement builder and executor'''
    dbm = kwargs['self']
    additionalStmt, arguments = generateSQLSuffixStatementAndArguments(**kwargs)
    stmt = f'SELECT {",".join(asList(sqlColumns))} FROM {getTableString(table)}' + additionalStmt
    if rawStatement:
        return stmt, arguments
    else:
        rows = dbm.dbc.execute(stmt, arguments).fetchall()
        if onlyColumn_asList and len(rows) > 0:
            return [r[onlyColumn_asList] for r in rows]
        else:
            return rows

def getDBAliases():
    '''return list containing all DB aliases'''
    return [mainDBAlias, computedDBAlias, dumpDBAlias]

def getAllDBAliasesWithTables(dbc):
    '''returns list of tuples: (dbAlias, [table names])'''
    return [(dbalias, [r.tbl_name for r in dbc.execute(f'SELECT * FROM {dbalias}.sqlite_master WHERE type=?', ('table',)).fetchall()]) for dbalias in getDBAliases()]

def getDBAliasForTable(tableName: str):
    '''returns correct DB alias for given table name'''
    if tableName.endswith('_d'): return dumpDBAlias
    elif tableName.endswith('_c'): return computedDBAlias
    return 'main'

def getDBConnectionAndCursor(dbpath, row_factory=recdotdict_factory):
    '''return (connection, cursor) for given database path'''
    dbconnect = sqlite3.connect(dbpath, timeout=15)
    dbconnect.row_factory = row_factory
    return dbconnect, dbconnect.cursor()

def attachDB(dbc: sqlite3.Cursor, dbpath, alias):
    dbc.execute(f'ATTACH ? AS ?', (dbpath, alias))

def generateCompleteDBConnectionAndCursor(propertiesDatabasePath=None, computedDatabasePath=None, dumpDatabasePath=None):
    '''returns (connection, cursor) with all DB aliases attached'''
    configManager: StaticConfigManager = StaticConfigManager()

    connect, dbc = getDBConnectionAndCursor(shortc(propertiesDatabasePath, configManager.get('propertiesdatabase', required=True)))
    attachDB(dbc, shortc(computedDatabasePath, configManager.get('computeddatabase', required=True)), computedDBAlias)
    attachDB(dbc, shortc(dumpDatabasePath, configManager.get('dumpdatabase', required=True)), dumpDBAlias)
    return connect, dbc

def getTableString(tableName) -> str:
    '''returns full table name with DB alias if it is not 'main': dbalias.tableName'''
    if '.' in tableName:
        ## table string already generated
        return tableName
    dbalias = getDBAliasForTable(tableName)
    if dbalias == mainDBAlias: return tableName
    else: return f'{dbalias}.{tableName}'

def getTableColumns(dbc, tableName) -> List:
    '''returns all table column objects'''
    return dbc.execute(f'PRAGMA {getDBAliasForTable(tableName)}.table_info({tableName})').fetchall()

def generateDatabaseAnnotationObjectsFile(propertiesDatabasePath=None, computedDatabasePath=None, dumpDatabasePath=None):
    '''auto-generates file with annotation objects for the rows of each table in the database, at _generatedDatabaseExtras/databaseRowObjects.py'''
    connect, dbc = generateCompleteDBConnectionAndCursor(propertiesDatabasePath, computedDatabasePath, dumpDatabasePath)

    def __generateArgTypeString(cname, t):
        if t in ['TEXT', 'STRING']: return ': str'
        elif t in ['', 'NUMERIC', 'INTEGER'] and cname in ['artificial', 'migrated', 'fmp_isetf', 'duplicate', 'wksi', 'prevrpt', 'detail', 'custom', 'abstract', 'tradeable', 'crypto_tradeable']: return ': bool'
        elif t in ['REAL', 'BIGDOUBLE', 'NUMERIC']: return ': float'
        elif t in ['NUM', 'NUMBER', 'INTEGER', 'INT', 'BIGINT']: return ': int'
        elif t in ['BYTE', 'BLOB']: return ': bytes'
        elif t in ['DATETIME']: return ': datetime'
        return ''

    fileString = '## AUTO-GENERATED BY _generateDatabaseAnnotationObjectsFile() IN managers/databaseManager.py ##\n\n'
    fileString += 'from datetime import datetime\n\n'
    for dbalias, tables in getAllDBAliasesWithTables(dbc):
        for t in tables:
            columns = dbc.execute(f'PRAGMA {dbalias}.table_info({t})').fetchall()

            commaSeparatedSnakeCaseColumnNames = ', '.join([f"'{c['name']}'" for c in columns])
            commaSeparatedCamelCaseColumnNames = ', '.join([f"'{convertToCamelCase(c['name'])}'" for c in columns])

            initargsList = []
            initfuncString = ''
            for c in columns:
                cname = convertToCamelCase(c.name)
                initargsList.append(f"{cname}Value{__generateArgTypeString(c['name'], c['type'])}")
                initfuncString += f'{tab}{tab}self.{cname} = {cname}Value\n'

            fileString += f'## TABLE: {t} ######################################\n'
            fileString += f'{convertToCamelCase(t)}SnakeCaseTableColumns = [{commaSeparatedSnakeCaseColumnNames}]\n'
            fileString += f'{convertToCamelCase(t)}CamelCaseTableColumns = [{commaSeparatedCamelCaseColumnNames}]\n'
            fileString += f'class {convertToPascalCase(t)}Row():\n'
            fileString += f"{tab}def __init__(self, {', '.join(initargsList)}):\n"
            fileString += initfuncString
            fileString += '\n'

    with open(os.path.join(path, 'managers', '_generatedDatabaseExtras', 'databaseRowObjects.py'), 'w') as f:
        f.write(fileString)

    connect.close()

def generateDatabaseGeneralizedGettersForDBM():
    '''generates generalized SELECT functions for each database table, written directly into managers/databaseManager.py'''
    ## ensure annotations objects are up-to-date first
    generateDatabaseAnnotationObjectsFile()

    _, dbc = generateCompleteDBConnectionAndCursor()

    rowAnnotationNames = []
    functionsString = ''
    for _, tables in getAllDBAliasesWithTables(dbc):
        for t in tables:
            ## function definition
            if t.endswith('_d'):
                functionName = f'Dump{convertToPascalCase(t[:-2])}' ## trim dump db identifier, add as English to function name
            elif t.endswith('_c'):
                functionName = convertToPascalCase(t[:-2]) ## drop computed db identifier
            else:
                functionName = convertToPascalCase(t)
            functionName = f'get{functionName}_basic'

            rowAnnotationName = f'{convertToPascalCase(t)}Row'
            rowAnnotationNames.append(rowAnnotationName)

            columns = getTableColumns(dbc, t)
            argumentPKStrings = []
            argumentStrings = []
            for c in columns:
                astring = f'{convertToCamelCase(c.name)}=None'
                if c['pk']: argumentPKStrings.append(astring)
                else: argumentStrings.append(astring)
            suffixArgumentStrings = ['groupBy=None', 'orderBy=None', 'limit=None', 'excludeKeys=None', 'onlyColumn_asList=None', 'sqlColumns=\'*\'', 'rawStatement=False']

            argumentLineSeparator = f',\n{tab}{tab}{tab}'
            arglists = [['self']]
            if argumentPKStrings: arglists.append(argumentPKStrings)
            if argumentStrings: arglists.append(argumentStrings)
            arglists.append(suffixArgumentStrings)
            argumentString = argumentLineSeparator.join([', '.join(al) for al in arglists])

            ## construct function
            functionsString += f'''\n{tab}def {functionName}({argumentString}) -> List[{rowAnnotationName}]:\n{tab}{tab}return _dbGetter("{t}", **locals())\n'''
    functionsString += '\n'

    newDBMString = ''
    basicGetsRegionDone = False
    basicGetsRegionStarted = False
    rowObjectImportDone = False
    with open(os.path.join(path, 'managers', 'databaseManager.py'), 'r') as f:
        for line in f:
            if not rowObjectImportDone and line.startswith('from managers._generatedDatabaseExtras.databaseRowObjects') and line.endswith('Row\n'):
                newDBMString += f'from managers._generatedDatabaseExtras.databaseRowObjects import {", ".join(rowAnnotationNames)}\n'
                rowObjectImportDone = True
                continue
            elif not basicGetsRegionDone and line.startswith(f'{tab}#region basic generic gets - AUTO-GENERATED SECTION'):
                basicGetsRegionStarted = True
                newDBMString += line
                newDBMString += f'{tab}## MANUALLY TRIGGERED, AUTO-GENERATED BY generateDatabaseGeneralizedGettersForDBM() FROM utils/dbSupport.py ##\n'
                newDBMString += functionsString
                continue
            elif not basicGetsRegionDone and basicGetsRegionStarted:
                if line.startswith(f'{tab}#endregion basic generic gets - AUTO-GENERATED SECTION'):
                    basicGetsRegionStarted = False
                    basicGetsRegionDone = True
                else:
                    continue
            
            newDBMString += line

    if not rowObjectImportDone:
        raise RuntimeError('Row import line not found')
    if not basicGetsRegionDone:
        raise RuntimeError('Basic gets region not completed')

    ## write back to DBM file
    with open(os.path.join(path, 'managers', 'databaseManager.py'), 'w') as f:
        f.write(newDBMString)

if __name__ == '__main__':
    opts, kwargs = parseCommandLineOptions()
    if opts.function:
        locals()[opts.function](**kwargs)
    else:
        generateDatabaseGeneralizedGettersForDBM()

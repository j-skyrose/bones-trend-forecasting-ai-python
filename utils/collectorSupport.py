import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import difflib, sqlite3
from typing import Tuple, Union

from constants.values import usExchanges, multiExchangeSymbols
from managers.databaseManager import DatabaseManager
from managers._generatedDatabaseAnnotations.databaseRowObjects import dumpSymbolInfoYahooCamelCaseTableColumns
from structures.api.yahoo import Yahoo
from utils.support import generateCommaSeparatedQuestionMarkString, getItem, shortcdict, tqdmLoopHandleWrapper

dbm: DatabaseManager = DatabaseManager()
yapi = Yahoo()
exchaliasdict = dbm.getAliasesDictionary()

## error accumulation
# e0nx = ['ALO', 'CBOE']
# e1n1 = ['BGSF', 'BHP', 'COMS']
e0nx = []
e1n1 = []
e1nx = []

def getYahooExchangeForSymbol(symbol, companyName, verbose=1):
    ret = getYahooExchangeForSymbolWithDetails(symbol, companyName, verbose)
    return ret[0]

## attempts to determine the correct exchange given a symbol (from a datapoint in the Yahoo earnings date response)
def getYahooExchangeForSymbolWithDetails(symbol, companyName, verbose=1) -> Tuple[Union[None, str], bool]:
    ''' return tuple: <exchange>, <is unable to match symbol to any existing ticker> '''
    acceptablewithoutotherconfirmation = ['PNK']

    ## manually determined matches
    manualMatches = {
        'XM': 'NASDAQ'
    }
    try: return manualMatches[symbol]
    except: pass
    try: return multiExchangeSymbols[symbol][0]
    except: pass
    
    ## check if Yahoo symbol info API (or cache) has a record
    yahooSymbol = dbm.getYahooSymbolInfo(symbol)
    if not yahooSymbol:
        ## nothing cached (i.e. in DB), retrieve
        yahooSymbol = yapi.getSymbol(symbol)

        ## if no still results, ensure at least a placeholder is cached to DB 
        if not yahooSymbol: yahooSymbol = {'symbol': symbol, 'exchange': 'UNKNOWN'}

        ## insert data
        proccessedkwargs = {}
        for k,v in yahooSymbol.items():
            if v is not None:
                if k not in dumpSymbolInfoYahooCamelCaseTableColumns: 
                    ## only appears for limited number of symbols (e.g. MYO), ignore unless real data is apparent
                    ## ['underlyingExchangeSymbol', 'headSymbol', 'uuid', 'underlyingSymbol']
                    if k not in ['uuid']:
                        raise ValueError(f'"{k}" argument not in table columns')
                proccessedkwargs[k] = v
        args = [shortcdict(proccessedkwargs, argName) for argName in dumpSymbolInfoYahooCamelCaseTableColumns]
        dbm.dbc.execute(f'INSERT INTO {dbm.dumpDBAlias}.dump_symbol_info_yahoo VALUES ({generateCommaSeparatedQuestionMarkString(dumpSymbolInfoYahooCamelCaseTableColumns)})', args)

    elif len(yahooSymbol) > 1:
        raise ValueError(f'too many DB results for {symbol}')
    elif len(yahooSymbol) == 1:
        yahooSymbol = yahooSymbol[0]

    ## check if exchange or alias is known
    try:
        exchange = exchaliasdict[yahooSymbol['exchange']]
    except KeyError as e:
        try:
            exchange = yahooSymbol['exchange']
        except KeyError:
            if list(yahooSymbol.keys()) != ['symbol', 'quoteType', 'messageBoardId', 'gmtOffSetMilliseconds', 'isEsgPopulated']:
                pass ## for breakpoint debug inspecting
            exchange = None
    # except TypeError as e:
    #     exchange = None

    ## now attempt to match the symbol to an existing ticker
    tickers = dbm.getSymbols(symbol=symbol)
    ## eliminate non-US exchanges
    for t in tickers[:]:
        if t.exchange not in usExchanges + ['OTCBB']:
            tickers.remove(t)

    if len(tickers) == 0:
        return exchange, True

    elif len(tickers) > 0:
        exchangeMatches = []
        for t in tickers:
            if t.exchange == exchange:# and exchange in usExchanges + ['OTCBB']: 
                exchangeMatches.append(t)

        ## attempt to match company name to the company name of existing tickers
        ######################################################################
        ## method 1: old manual company name conversion and checks
        ######################################################################
        # namematches = []
        # dnamelower = data[0].name.lower()
        # dnamealphanum = re.sub(r'\W+', '', dnamelower)
        # dnamereplaced1 = dnamealphanum.replace('international', 'intl')
        # dnamereplaced2 = dnamereplaced1.replace('technologies', 'tech')
        # dnamereplaced3 = dnamereplaced2.replace('inc', '')
        # dnamereplaced4 = dnamereplaced3.replace('limited', '')
        # dnamereplaced5 = dnamereplaced4.replace('group', 'gp')
        ######################################################################
        ## method 2: likeness comparison using difflib.get_close_matches
        ######################################################################
        nameMatches = []
        if companyName:
            cutoff = 0.999 ## default 0.6
            dname = companyName
            dnamelower = dname.lower()
            tnamelist = [f"{t.name}{indx}".lower() for indx,t in enumerate(tickers)]
            difflibnamematches = difflib.get_close_matches(dnamelower, tnamelist, cutoff=cutoff)
            if verbose > 1: print(f'"{dname}"', 'vs', f'"{tnamelist}"')
            if verbose > 1: print('matches:', difflibnamematches)
            if len(difflibnamematches) == 0:
                tnamelist2 = [(tn[:max(int(len(tn)/2), len(dnamelower))] + tn[-1]) for tn in tnamelist]
                difflibnamematches = difflib.get_close_matches(dnamelower, tnamelist2, cutoff=cutoff)
                if verbose > 1: print(f'"{dname}"', 'vs2', f'"{tnamelist2}"')
                if verbose > 1: print('matches2:', difflibnamematches)

            nameMatches = [tickers[int(nm[-1])] for nm in difflibnamematches]
            pass
            '''
                "ABIVAX Société Anonyme" vs "['abivax s.a.\n0']"
                matches: []
                accepting {'symbol': 'AAVXF', 'quoteType': 'EQUITY', 'exchange': 'PNK',

                "Atlas Air Worldwide Holdings, Inc." vs "['atlas air ww0']"
                matches: []
                no exchange matches
            '''
        ######################################################################


        if verbose > 1: print(symbol, companyName, '\nexchmatches', exchangeMatches, '\nnamematches', nameMatches, '\ntickers', tickers)

        ## filter out name matches from non-US exchanges
        if len(nameMatches) > 1: 
                namematches2 = []
                for t in tickers:
                    if t.exchange in usExchanges:
                        namematches2.append(t)
                nameMatches = namematches2

        if len(exchangeMatches) == 0:
            if len(nameMatches) == 0:
                if exchange in acceptablewithoutotherconfirmation:
                    if verbose > 1: print('accepting', yahooSymbol)
                    pass
                else:
                    # raise ValueError('no matches found')
                    # print('no matches, new symbol', s)
                    # notfound.append(s)
                    ## unable to determine match
                    return exchange, True
            elif len(nameMatches) == 1:
                if verbose > 1: print(f'{exchange} not found,' if exchange else '', 'using', nameMatches[0])
                exchange = nameMatches[0].exchange
            elif len(nameMatches) > 1:
                e0nx.append(symbol)
                if verbose > 1: print('e0nx too many name matches error')
                raise ValueError('e0nx, too many matches found')
        elif len(exchangeMatches) == 1:
            if len(nameMatches) == 0:
                if verbose > 1: print('no name matches for exch match, using', exchangeMatches[0], '\ntickers', tickers)
                exchange = exchangeMatches[0].exchange
            elif len(nameMatches) == 1:
                if exchangeMatches[0].exchange == nameMatches[0].exchange:
                    if verbose > 1: print('matched\n', exchangeMatches[0], '\n', nameMatches[0])
                    exchange = exchangeMatches[0].exchange
                else:
                    e1n1.append(symbol)
                    if verbose > 1: print('e1n1 mismatch error')
                    raise ValueError('e1n1, exchange mismatch')
            elif len(nameMatches) > 1:
                matchesfound = []
                for nm in nameMatches:
                    if exchangeMatches[0].exchange == nm.exchange:
                        matchesfound.append(nm)
                if len(matchesfound) < 2:
                    if verbose > 1: print('matched\n', exchangeMatches[0], '\n', shortcdict(matchesfound, 0))
                    exchange = exchangeMatches[0].exchange
                elif len(matchesfound) > 1:
                    e1nx.append(symbol)
                    if verbose > 1: print('e1nx too many name matches error')
                    raise ValueError('e1nx, too many matches found')
        elif len(exchangeMatches) > 1:
            if len(nameMatches) == 0:
                raise ValueError('too many matches found')
            elif len(nameMatches) == 1:
                matchesfound = []
                for em in exchangeMatches:
                    if nameMatches[0].exchange == em.exchange:
                        matchesfound.append(em)
                if len(matchesfound) < 2:
                    if verbose > 1: print('matched\n', nameMatches[0], '\n', shortcdict(matchesfound, 0))
                    exchange = nameMatches[0].exchange
                elif len(matchesfound) > 1:
                    if verbose > 1: print('exn1 too many matches error')
                    raise ValueError('too many matches found')
            elif len(nameMatches) > 1:
                if verbose > 1: print('exnx too many matches error')
                raise ValueError('too many matches found')
                ## todo, double loop?
                matchesfound = []
                for em in exchangeMatches:
                    if nameMatches[0].exchange == em.exchange:
                        matchesfound.append(em)
                if len(matchesfound) < 2:
                    exchange = nameMatches[0].exchange
                elif len(matchesfound) > 1:
                    raise ValueError('too many matches found')

        return exchange, False

## possibly only single use, meant to consolidate earnings date dump data from multiple apis/tables into a single table, which would receive all future retrieved data
## OBSOLETE: data moved back to individual tables based on the API supplying the data (2023-08-16)
def transferYahooEarningsDateDumpTableToStaging(symbolList=[], dryrun=False, verbose=1):
        ## nasdaq is mostly covered by yahoo, only ~375 symbols are unique
        # nasdaqtablesymbols = [r.symbol for r in dbm.dbc.execute('select distinct symbol from dump_nasdaq_earnings_dates').fetchall()]
        if symbolList:
            yahootablesymbols = symbolList if type(symbolList[0]) == str else [r.symbol for r in symbolList]
        else:
            yahootablesymbols = [r.symbol for r in dbm.dbc.execute('select distinct symbol from dump_yahoo_earnings_dates').fetchall()]

        # brokensymbols = ['AACQ']
        ## Exantas Capital Corp. Changes Name to ACRES: NYSE:ACR
        ## Advent Technologies Inc. and AMCI Acquisition Corp. ... Feb 4, 2021 — The combined company, Advent Technologies Holdings, Inc.

        ## nasdaq only in staging, rowid 216991; passed will be from yahoo

        notfound = []
        checkpoint = False
        for indx,s in enumerate(tqdmLoopHandleWrapper(yahootablesymbols, verbose, desc='Migrating data')):
            # anyrow = dbm.dbc.execute(f'''select * from {dbm.dumpDBAlias}.staging_earnings_dates where symbol=?''', (s,)).fetchone()
            # if anyrow: continue

            # if s in brokensymbols: continue
            # if s == 'ISDCF': checkpoint = True
            # if indx == 1800: checkpoint = True
            # elif not checkpoint: continue
            if verbose > 1: print(f'----- {indx}/{len(yahootablesymbols)}: {s} --------------------------------------------')

            data = dbm.dbc.execute(f'select * from {dbm.dumpDBAlias}.dump_yahoo_earnings_dates WHERE symbol=?', (s,)).fetchall()
            totalexceptionslength = len(e0nx) + len(e1n1) + len(e1nx)

            try:
                exchange = getYahooExchangeForSymbol(s, data[0].name, verbose)
            except ValueError as e:
                if len(e0nx) + len(e1n1) + len(e1nx) == totalexceptionslength:
                    raise e ## some unknown exception occurred
                else:
                    continue

            existingRows = dbm.dbc.execute(f'''select * from {dbm.dumpDBAlias}.staging_earnings_dates where exchange=? and symbol=?''', (exchange, s)).fetchall()

            for r in data:
                ## check if row should be new
                existingRow = None
                if exchange == 'NASDAQ':
                    existingRow = getItem(existingRows, lambda x: x.input_date == r.input_date and x.earnings_date == r.earnings_date)

                if exchange != 'NASDAQ' or not existingRow:
                    if verbose > 1 and not existingRow and exchange == 'NASDAQ': print('inserting new NASDAQ row:', s, r.input_date, r.earnings_date)
                    if dryrun: continue
                    try:
                        dbm.dbc.execute(f'''insert into {dbm.dumpDBAlias}.staging_earnings_dates(
                                    exchange, symbol, input_date, earnings_date,yahoo_name,yahoo_event_name,yahoo_eps_forecast,yahoo_eps,yahoo_surprise_percentage,yahoo_start_date_time,yahoo_start_date_time_type,yahoo_time_zone_short_name,yahoo_gmt_offset_milli_seconds 
                                    ) VALUES ({generateCommaSeparatedQuestionMarkString(13)})''', (exchange, *list(r.values())))
                    except sqlite3.IntegrityError:
                        ## already migrated
                        if verbose > 1: print(f'integrity error, probably already migrated, skipping symbol {s}')
                        break
                else:
                    if dryrun:
                        if verbose > 1: print('updating NASDAQ row(s) with yahoo data')
                        break
                    dbm.dbc.execute(f'''update {dbm.dumpDBAlias}.staging_earnings_dates SET 
                                yahoo_event_name=?, yahoo_name=?,yahoo_eps_forecast=?,yahoo_eps=?,yahoo_surprise_percentage=?,yahoo_start_date_time=?,yahoo_start_date_time_type=?,yahoo_time_zone_short_name=?,yahoo_gmt_offset_milli_seconds =?
                                WHERE exchange=? AND symbol=? AND input_date=? AND earnings_date=?
                                ''', (r.event_name,r.name,r.eps_forecast,r.earnings_per_share,r.surprise_percentage,r.start_date_time,r.start_date_time_type,r.time_zone_short_name,r.gmt_offset_milli_seconds,   'NASDAQ', r.symbol, r.input_date, r.earnings_date))

########################################################################################################################################################################
if __name__ == '__main__':
    try:
        # transferYahooEarningsDateDumpTableToStaging(dryrun=False)
        # transferMarketwatchEarningsDateDumpTableToStaging(dryrun=False)
        pass
    finally:
        print('e0nx, too many matches found:', ','.join(e0nx))
        print('e1n1, exchange mismatch', ','.join(e1n1))
        print('e1nx, too many matches found', ','.join(e1nx))

    # exceptionsymbols = ['ACST','AGI','AKU','BEPC','COMS','CP','DCBO','FNV','FSV','FTS','HST','KOR','NTR','RDI','RZB','SHOP','SKY','UGRO','VFF','VNET','WMT']

    # # integrity checks
    # for s in exceptionsymbols:
    #     print(f'-----{s} --------------------------------------------')
    #     try:
    #         # anyrow = dbm.dbc.execute(f'''select * from {dbm.dumpDBAlias}.dump_yahoo_earnings_dates where symbol=?''', (s,)).fetchone()
    #         # exchange = getYahooExchangeForSymbol(s, shortcdict(anyrow, 'name'), 2)
    #         # print('exchange:', exchange)
    #         histdata = dbm.dbc.execute('select * from historical_data where symbol=?', (s,)).fetchall()
    #         histdatatickers = dbm.dbc.execute('select distinct exchange,symbol from historical_data where symbol=?', (s,)).fetchall()
    #         lastupd = dbm.dbc.execute('select * from last_updates where symbol=? and api is not null', (s,)).fetchall()
    #         lastupdtickers = dbm.dbc.execute('select distinct exchange,symbol from last_updates where symbol=? ', (s,)).fetchall()
    #         syms = dbm.getSymbols(symbol=s)
    #         ysym = dbm.dbc.execute(f'''select * from {dbm.dumpDBAlias}.dump_symbol_info_yahoo where symbol=?''', (s,)).fetchall()

    #         if len(histdata) > 0:
    #             print('has hist data')
    #             print(len(histdatatickers), 'unique')
    #             print(histdatatickers)
    #         else:
    #             print('no hist data')

    #         print(len(lastupdtickers), 'unique lastupd tickers')
    #         print(lastupdtickers)
    #         if len(lastupd) > 0:
    #             print('some updates done')
            
    #         hasfmp = None
    #         nonfmp = None
    #         if len(syms) > 2:
    #             print('too many symbols')
    #         for sy in syms:
    #             if sy.api_fmp == 1:
    #                 print('is fmp', sy.exchange)
    #                 hasfmp = sy.exchange
    #             else:
    #                 print('not', sy.exchange)
    #                 nonfmp = sy.exchange

    #         if len(ysym) > 1:
    #             print('too many ysyms', ysym)
    #         else:
    #             print('exchange should be', ysym[0].exchange)

    #         if hasfmp and nonfmp == 'OTCBB' and ysym[0].exchange == 'PNK':
    #             print('delete for', hasfmp, s)

    #     except ValueError as e:
    #         pass
        

    pass
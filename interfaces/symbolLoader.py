import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import sqlite3
from managers.databaseManager import DatabaseManager
from utils.support import recdotdict
import json

sdpath=os.path.dirname(os.path.realpath(__file__))

def getAliasesDictionary(dbc, api):
    ret = {}
    for r in dbc.execute('SELECT exchange, alias FROM exchange_aliases WHERE api=?', (api,)).fetchall():
        ret[r['alias']] = r['exchange']
    return recdotdict(ret)

def importFromFMP():
    dbc: DatabaseManager = DatabaseManager().dbc
    aldict = getAliasesDictionary(dbc, 'fmp')

    ## NMS should not perfectly equal NASDAQ, in theory
    ## todo: Amsterdam(124), XETRA(852), Swiss(16), Oslo(30), Other OTC(930), FGI(1), NZSE(1), OSL(1), AMEX(1), SIX(236), OTC(1), Frankfurt(2), Paris(720), HKG(5), Brussels(148), YHD(9), MCE(1), EURONEXT(2), Irish(36), Lisbon(40), Sao Paolo(12), OSE(154), Canadian Sec(3), MCX(186)

    includelist = ['Nasdaq Global Select', 'NMS', 'NasdaqGS', 'NYSE American', 'New York Stock Exchange Arca', 'LSE', 'BATS', 'NCM', 'Nasdaq Capital Market', 'BATS Exchange', 'NYSEArca', 'NASDAQ', 'TSXV', 'NSE', 'Toronto', 'Nasdaq', 'NASDAQ Global Market', 'Nasdaq Global Market', 'ASE', 'HKSE', 'New York Stock Exchange']

    # print(aldict)
    # return

    with open(os.path.join(path, 'data/symbol_dumps/fmp/list.json'), 'r') as f:
        symlist = json.load(f)
        # exchanges = set()

        for s in symlist:
            # exchanges.add(s['exchange'])
            if s['exchange'] not in includelist:
                continue

            try: exchange=aldict[s['exchange']]
            except KeyError: exchange=str(s['exchange']).upper()
            existing = dbc.execute('SELECT * from symbols WHERE exchange=? AND symbol=?', (exchange, s['symbol'])).fetchone()

            if existing:
                dbc.execute('UPDATE symbols SET api_fmp=1 WHERE exchange=? AND symbol=?', (exchange, s['symbol']))
                pass
            else:
                dbc.execute('INSERT INTO symbols (exchange, symbol, name, api_fmp) VALUES (?,?,?,1)', (exchange, s['symbol'], s['name']))
                # print('adding', (exchange, s['symbol'], s['name']))



def importFromPolygon(dbc):
    overlapList = []
    aldict = getAliasesDictionary(dbc, 'polygon')
    with open(os.path.join(sdpath, 'polygon/reference_tickers.csv')) as f:
        f.readline() ## dump header line
        for line in f:
            ticker,name,market,locale,type,currency,active,primaryExch,updated,url = line.split(',')
            exchange = None
            try: exchange=aldict[primaryExch]
            except KeyError: exchange=primaryExch

            ## TODO: otc, otcqx, obb, grey, oto, otcqb ,,, ndd, ngs
            ## poly otc = alpha otcbb = google otcmkts (see aairf)
            ## poly otcqb = barchart otc us
            ## gids, mdx, nsx, spic: only few records, ignore?
            if exchange not in ['NYSE','NASDAQ','BATS','NYSE ARCA','NYSE MKT']: continue

            existing = dbc.execute('SELECT * from symbols WHERE exchange=? AND symbol=?', (exchange, ticker)).fetchone()

            if existing:
                # if existing['asset_type']:
                #     overlapList.append((primaryExch, ticker, type, existing['asset_type']))



                newName = name if existing['name'].strip() in name else existing['name'].strip()
                newAssetType = type if type else existing['asset_type']

                dbc.execute('UPDATE symbols SET name=?, asset_type=?, api_polygon=1 WHERE exchange=? AND symbol=?', (newName, newAssetType, exchange, ticker))
            else:
                dbc.execute('INSERT INTO symbols (exchange, symbol, name, asset_type, api_polygon) VALUES (?,?,?,?,1)', (exchange, ticker, name, type if type else None))

    # print(len(overlapList))
    # for a in overlapList:
    #     print(a)


def importFromSymbolDumps(dbc):
    project_path = os.path.dirname(os.path.realpath(__file__))
    symbol_dumps_folder = os.path.join(project_path,'symbol_dumps')
    for source in ['eoddata','alphavantage']:
        linecount = 0
        lineupdated = 0
        path = os.path.join(symbol_dumps_folder, source)
        for file in [f for f in os.listdir(path) if os.path.isfile(path + '/' + f)]:

            with open(os.path.join(path, file), 'r') as f:
                f.readline() ## dump header line

                if source == 'eoddata':
                    # continue

                    exchange = file.split('.')[0]
                    if exchange == 'AMEX': continue ## AMEX has since become NYSE MKT
                    for line in f:
                        symbol, name = line.split('\t',1)

                        try:
                            dbc.execute('INSERT INTO symbols (exchange, symbol, name, api_alphavantage) VALUES (?,?,?,-1)', (exchange, symbol, name))
                            linecount += 1
                        except sqlite3.IntegrityError:
                            pass
                elif source == 'alphavantage':
                    for line in f:
                        symbol, name, exchange, assetType, ipoDate, delistingDate, status = line.split(',')
                        symbol = symbol.replace('-','.')
                        # print(symbol, name, exchange, assetType)
                        # exit()
                        if assetType != 'Stock' and assetType != 'ETF':
                            print('type not found',symbol, name, exchange, assetType)
                            exit()

                        try:
                            dbc.execute('INSERT INTO symbols (exchange, symbol, name, asset_type, api_alphavantage) VALUES (?,?,?,?,1)', (exchange, symbol, name, assetType))
                            linecount += 1
                        except sqlite3.IntegrityError:
                            try:
                                if dbc.execute("SELECT asset_type FROM symbols WHERE exchange=? AND symbol=?", (exchange, symbol)).fetchone()[0] is None:
                                    dbc.execute('UPDATE symbols SET asset_type=?, api_alphavantage=1 WHERE exchange=? AND symbol=?', (assetType, exchange, symbol))
                                    lineupdated += 1
                            except Exception as e:
                                print('update exception',e, ' for',symbol, name, exchange, assetType)
                                exit()



        print(linecount, 'symbols added from', source)
        print(lineupdated, 'symbols updated from', source)
## END importFromSymbolDumps END #################################################################################




# dbi = DatabaseManager()
# dbc = dbi.dbc
# importFromPolygon(dbc)

# importFromFMP()
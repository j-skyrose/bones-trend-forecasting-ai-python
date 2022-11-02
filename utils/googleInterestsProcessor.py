import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time, tqdm

from globalConfig import config as gconfig
from structures.dailyDataHandler import DailyDataHandler
from managers.configManager import ConfigManager
from managers.databaseManager import DatabaseManager
from utils.support import recdotdict, shortcdict
from constants.enums import InterestType, SQLHelpers, SeriesType

dbm: DatabaseManager = DatabaseManager()

def getMaxRowID():
    return dbm.dbc.execute('SELECT MAX(rowid) FROM google_interests_raw').fetchone()['MAX(rowid)']

def processRawGoogleInterests(exchange=None, symbol=None):
    '''pulls daily/weekly/monthly data from google_interests_raw then calculates and inserts overall relative interest for each day that has stock data into google_interests table'''
    
    config = ConfigManager()
    if config.get('google', 'lastprocessedrowid') == getMaxRowID():
        print('Already up-to-date')
        return
    
    if exchange and symbol:
        symbolList = [recdotdict({'exchange': exchange, 'symbol': symbol})]
    else:
        # symbolList = dbm.dbc.execute('SELECT DISTINCT exchange, symbol FROM google_interests_raw').fetchall()
        symbolList = dbm.getSymbols(googleTopicId=SQLHelpers.NOTNULL)

    ddh: DailyDataHandler
    for s in tqdm.tqdm(symbolList, desc='Processing symbols'):
        ## get daily
        dailydata = dbm.getGoogleInterests(s.exchange, s.symbol, itype=InterestType.DAILY, raw=True)
        if len(dailydata) == 0: continue
        ddh = DailyDataHandler(dailydata, dbm.getStockData(s.exchange, s.symbol, SeriesType.DAILY))

        ## get weekly
        weeklydata = dbm.getGoogleInterests(s.exchange, s.symbol, itype=InterestType.WEEKLY, raw=True)
        weeklyDataDict = {}
        for d in weeklydata:
            weeklyDataDict[d.date] = d.relative_interest

        ## overall/monthly
        overalldata = dbm.getGoogleInterests(s.exchange, s.symbol, itype=InterestType.MONTHLY, raw=True)
        overallDataDict = {}
        ## if no overall data, generate based on stream 0
        if gconfig.testing.enabled and not overalldata:
            maxweeksum = 0
            dailyblocks = ddh.getStream(0).blocks
            for b in dailyblocks:
                if b.sum() > maxweeksum: maxweeksum = b.sum()
            for b in dailyblocks:
                for d in b.data.keys():
                    overallDataDict[d] = b.sum() / maxweeksum * 100   
        else:
            for d in overalldata:
                overallDataDict[d.date] = d.relative_interest

        ## verify stream 0 daily data has a match in overall data set
        stream0blocks = ddh.getStream(0).blocks
        for bindex in range(len(stream0blocks)):
            d = stream0blocks[bindex].getStartDate() if bindex < len(stream0blocks)-1 else stream0blocks[bindex].getEndDate()
            if d not in overallDataDict.keys():
                raise ValueError(f'Missing Google Interest overall data point for {d} -- {s.exchange}:{s.symbol}')

        ## verify adjacent streams share an overlapping block
        for sindex in range(ddh.numberOfStreams()-1):
            if ddh.getStream(sindex).getLastFullBlock() != ddh.getStream(sindex+1).getFirstFullBlock():
                raise ValueError(f'Missing Google Interest overlapping blocks between stream {sindex} and {sindex+1} -- {s.exchange}:{s.symbol}')

        ## compare overlap between streams and determine back-modifier
        for sindex in range(ddh.numberOfStreams()-1):
            week1block = ddh.getStream(sindex).getLastFullBlock()
            week1newblock = ddh.getStream(sindex+1).getFirstFullBlock()

            #####
            ## predict overall values for stream sindex+1, past the overlapping block
            factor = overallDataDict[week1block.getEndDate()] / week1block.sum()
            
            nextStreamManager = ddh.getStream(sindex+1)
            ## if last block is partial, prepare an approximated sum
            lastBlockIsPartial = nextStreamManager.getLastBlock().isPartial()
            weekdaySums = [0 for x in range(7)]

            pastoverlapingblock = False
            for b in nextStreamManager.blocks:
                ## approximated sum preparation
                if lastBlockIsPartial and not b.isPartial():
                    blockvals = list(b.data.values())
                    for w in range(7):
                        weekdaySums[w] += blockvals[w]

                ## skip overlap week
                if not pastoverlapingblock:
                    if not b.isPartial(): pastoverlapingblock = True
                    continue

                ## predict overall value for the week and write
                weeksum = b.sum()
                if b.isPartial():
                    approximateWeekdayPercentages = [weekdaySums[w] / sum(weekdaySums) for w in range(7)]
                    weeksum /= sum(approximateWeekdayPercentages[:len(b.data)])
                for d in b.data.keys():
                    overallDataDict[d] = weeksum * factor


            ## overall values have shifted, back modification required
            if week1newblock.sum() < week1block.sum():
                backfactor = week1newblock.sum() / week1block.sum()
                lastdate = week1block.getEndDate()
                for d in overallDataDict.keys():
                    overallDataDict[d] *= backfactor
                    ## stop once end of original data is reached
                    if d == lastdate:
                        break

            elif week1newblock.sum() != week1block.sum():
                ## equal is an expected scenario, indicates no shift for overall values
                raise Exception('Unexpected comparison result of overlap sums')

        ## calculate relative interest for each day based on daily, weekly (if available), and overall numbers
        for k,v in ddh.getConsolidatedDict().items():
            # self.relativeDataDict[k] = v * shortcdict(weeklyDataDict, k, 100) / 100 * overallDataDict[k] / 100
            relativev = v * shortcdict(weeklyDataDict, k, 100) / 100 * overallDataDict[k] / 100
            ## upsert
            dbm.dbc.execute('INSERT OR IGNORE INTO google_interests VALUES (?,?,?,?)', (s.exchange, s.symbol, k, relativev))
            dbm.dbc.execute('UPDATE google_interests SET relative_interest=? WHERE exchange=? AND symbol=? AND date=?', (relativev, s.exchange, s.symbol, k))
            ## v, weeklyData, overallData: {1-100}
    
    if not exchange or symbol:
        ## save row count as snapshot for when data was processed and up to date
        maxrowid = getMaxRowID()
        config.set('google', 'lastprocessedrowid', maxrowid)
        print(f'Finished processing {maxrowid} raw data points')
        config.save()

    dbm.commit()

if __name__ == '__main__':
    # print(dbm.dbc.execute('SELECT MAX(rowid) FROM google_interests_raw').fetchone()['MAX(rowid)'])
    # processRawGoogleInterests('NASDAQ','VTSI')
    processRawGoogleInterests()

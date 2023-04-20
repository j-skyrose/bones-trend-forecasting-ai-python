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
from managers.configManager import ConfigManager
from managers.databaseManager import DatabaseManager
from structures.dailyDataHandler import DailyDataHandler
from utils.support import recdotdict, shortcdict, tqdmLoopHandleWrapper
from constants.enums import InterestType, SQLHelpers, SeriesType

dbm: DatabaseManager = DatabaseManager()


def processRawGoogleInterests(exchange=None, symbol=None, verbose=1):
    '''pulls daily/weekly/monthly data from google_interests_raw then calculates and inserts overall relative interest for each day that has stock data into google_interests table. Essentially rebuilds all data in google_interests table every execution as backfactor modification may be performed'''
    
    config = ConfigManager()
    if config.get('google', 'lastprocessedrowid') == dbm.getMaxRowID():
        print('Already up-to-date')
        return
    
    if exchange and symbol:
        symbolList = [recdotdict({'exchange': exchange, 'symbol': symbol})]
    else:
        # symbolList = dbm.dbc.execute('SELECT DISTINCT exchange, symbol FROM google_interests_raw').fetchall()
        symbolList = dbm.getSymbols(exchange=exchange, googleTopicId=SQLHelpers.NOTNULL)

    ddh: DailyDataHandler
    for s in tqdmLoopHandleWrapper(symbolList, verbose, desc='Processing symbols'):
        if verbose>=2: print(s.exchange, s.symbol)
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
        monthlydata = dbm.getGoogleInterests(s.exchange, s.symbol, itype=InterestType.MONTHLY, raw=True)
        monthlyDataDict = {}
        ## if no overall data, generate based on stream 0
        if gconfig.testing.enabled and not monthlydata:
            maxweeksum = 0
            dailyblocks = ddh.getStream(0).blocks
            for wkbl in dailyblocks:
                if wkbl.sum() > maxweeksum: maxweeksum = wkbl.sum()
            for wkbl in dailyblocks:
                for d in wkbl.data.keys():
                    monthlyDataDict[d] = wkbl.sum() / maxweeksum * 100   
        else:
            for d in monthlydata:
                monthlyDataDict[d.date] = d.relative_interest

        ## verify stream 0 daily data has a match in overall data set
        stream0blocks = ddh.getStream(0).blocks
        for bindex in range(len(stream0blocks)):
            d = stream0blocks[bindex].getStartDate() if bindex < len(stream0blocks)-1 else stream0blocks[bindex].getEndDate()
            if d not in monthlyDataDict.keys():
                raise ValueError(f'Missing Google Interest overall data point for {d} -- {s.exchange}:{s.symbol}')

        ## verify adjacent streams share an overlapping block
        for sindex in range(ddh.numberOfStreams()-1):
            if ddh.getStream(sindex).getLastFullBlock() != ddh.getStream(sindex+1).getFirstFullBlock():
                raise ValueError(f'Missing Google Interest overlapping blocks between stream {sindex} and {sindex+1} -- {s.exchange}:{s.symbol}')

        ## compare overlap between streams and determine back-modifier
        for sindex in range(ddh.numberOfStreams()-1):
            currentStreamManager = ddh.getStream(sindex)
            nextStreamManager = ddh.getStream(sindex+1)
            week1block = currentStreamManager.getLastFullBlock()
            week1newblock = nextStreamManager.getFirstFullBlock()
            week1BlockSum = week1block.sum()
            week1NewBlockSum = week1newblock.sum()

            #####
            ## predict overall values for stream sindex+1, past the overlapping block
            factor = monthlyDataDict[week1block.getEndDate()] / week1BlockSum
            
            ## if last block is partial, must prepare an approximated sum
            lastBlockIsPartial = nextStreamManager.getLastBlock().isPartial()
            weekdaySums = [0 for x in range(7)]

            pastoverlapingblock = False
            for wkbl in nextStreamManager.blocks:
                ## sum preparation, for use in approximating the last partial block
                if lastBlockIsPartial and not wkbl.isPartial():
                    blockvals = list(wkbl.data.values())
                    for w in range(7):
                        weekdaySums[w] += blockvals[w]

                ## skip overlap week
                if not pastoverlapingblock:
                    if not wkbl.isPartial(): pastoverlapingblock = True
                    continue

                weeksum = wkbl.sum()
                ## approximate weeksum if block is only partial
                if wkbl.isPartial():
                    approximateWeekdayPercentages = [weekdaySums[w] / sum(weekdaySums) for w in range(7)]
                    weeksum /= sum(approximateWeekdayPercentages[:len(wkbl.data)])


            ## overall values have shifted, back modification required
            if week1NewBlockSum < week1BlockSum:
                backfactor = week1NewBlockSum / week1BlockSum
                lastdate = week1block.getEndDate()
                for d in monthlyDataDict.keys():
                    monthlyDataDict[d] *= backfactor
                    ## stop once end of original data is reached
                    if d == lastdate:
                        break

            elif week1NewBlockSum != week1BlockSum:
                ## equal is an expected scenario, indicates no shift for overall values
                raise Exception('Unexpected comparison result of overlap sums')

        ## calculate relative interest for each day based on daily, weekly (if available), and overall numbers
        for k,v in ddh.getConsolidatedDict().items():
            relativev = v * shortcdict(weeklyDataDict, k, 100) / 100 * monthlyDataDict[k] / 100
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
    # print(dbm.dbc.execute('SELECT MAX(rowid) FROM google_interests_raw').fetchone()['MAX(rowid)'])
    # processRawGoogleInterests('NASDAQ','VTSI')
    processRawGoogleInterests()

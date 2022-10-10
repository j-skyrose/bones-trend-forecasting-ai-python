import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import Dict

from globalConfig import config as gconfig
from structures.dailyDataHandler import DailyDataHandler

class GoogleInterestsHandler:
    # exchange = None
    # symbol = None
    # dailyData: DailyDataManager = None
    # ## will include predicted values
    # overallData: Dict[str,int] = {}
    # relativeDataDict: Dict[str,float] = {}

    def __init__(self, exchange, symbol, dailydata, overalldata):
        self.exchange = exchange
        self.symbol = symbol
        self.dailyData: DailyDataHandler = None
        ## will include predicted values
        self.overallData: Dict[str,int] = {}
        self.relativeDataDict: Dict[str,float] = {}

        if len(dailydata) == 0: return

        self.dailyData = DailyDataHandler(dailydata)

        ## if no overall data, generate based on stream 0
        if gconfig.testing.enabled and not overalldata:
            maxweeksum = 0
            dailyblocks = self.dailyData.getStream(0).blocks
            for b in dailyblocks:
                if b.sum() > maxweeksum: maxweeksum = b.sum()
            for b in dailyblocks:
                for d in b.data.keys():
                    self.overallData[d] = b.sum() / maxweeksum * 100   
        else:
            for d in overalldata:
                self.overallData[d.date] = d.relative_interest

        ## verify stream 0 daily data has a match in overall data set
        stream0blocks = self.dailyData.getStream(0).blocks
        for bindex in range(len(stream0blocks)):
            d = stream0blocks[bindex].getStartDate() if bindex < len(stream0blocks)-1 else stream0blocks[bindex].getEndDate()
            if d not in self.overallData.keys():
                raise ValueError(f'Missing Google Interest overall data point for {d}')
                
        ## verify adjacent streams share an overlapping block
        for sindex in range(self.dailyData.numberOfStreams()-1):
            if self.dailyData.getStream(sindex).getLastFullBlock() != self.dailyData.getStream(sindex+1).getFirstFullBlock():
                raise ValueError(f'Missing Google Interest overlapping blocks between stream {sindex} and {sindex+1}')


        ## compare overlap between streams and determine back-modifier
        for sindex in range(self.dailyData.numberOfStreams()-1):
            week1block = self.dailyData.getStream(sindex).getLastFullBlock()
            week1newblock = self.dailyData.getStream(sindex+1).getFirstFullBlock()

            #####
            ## predict overall values for stream sindex+1, past the overlapping block
            factor = self.overallData[week1block.getEndDate()] / week1block.sum()
            
            nextStreamManager = self.dailyData.getStream(sindex+1)
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
                    self.overallData[d] = weeksum * factor


            ## overall values have shifted, back modification required
            if week1newblock.sum() < week1block.sum():
                backfactor = week1newblock.sum() / week1block.sum()
                lastdate = week1block.getEndDate()
                for d in self.overallData.keys():
                    self.overallData[d] *= backfactor
                    ## stop once end of original data is reached
                    if d == lastdate:
                        break

            elif week1newblock.sum() != week1block.sum():
                ## equal is an expected scenario, indicates no shift for overall values
                raise Exception('Unexpected comparison result of overlap sums')

        ## calculate relative interest for each day based on daily and overall numbers
        for k,v in self.dailyData.getConsolidatedDict().items():
            self.relativeDataDict[k] = v * self.overallData[k] / 100
        

    def getTickerTuple(self):
        return (self.exchange, self.symbol)

    def getDict(self):
        return self.relativeDataDict

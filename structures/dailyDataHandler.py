import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time
from copy import deepcopy
from datetime import date
from typing import List, Set

from managers.statsManager import StatsManager
from structures.weekBlock import WeekBlock
from structures.weekBlockList import WeekBlockList
from utils.support import asMonthKey

sm: StatsManager = StatsManager()
collectStats = True

## helper for googleInterestsHandler: parses and organizes the raw data into a more accessible form for the purposes of calculating the overall relative interest for each day
class DailyDataHandler:
    ## streams
    # blockManagers: List[WeekBlockList] = []

    def __init__(self, dailygdata, stockdata) -> None:
        self.blockManagers: List[WeekBlockList] = []

        if collectStats: startt = time.time()
        ## setup streams
        maxstream = -1
        for d in dailygdata:
            if d.stream > maxstream: maxstream = d.stream
        rawblocks = [[] for x in range(maxstream+1)]
        if collectStats: sm.ddhsetupstreams += time.time() - startt
        
        if collectStats: startt = time.time()
        ## separate data into streams and omit anything not within range of actual stock data
        for d in dailygdata:
            if d.date >= stockdata[0].date and d.date <= stockdata[-1].date:
                rawblocks[d.stream].append(d)
        if collectStats: sm.ddhseparatetostreams += time.time() - startt

        if collectStats: startt = time.time()
        ## sort streams
        for s in range(len(rawblocks)):
            rawblocks[s].sort(key=lambda a: a.date)
        if collectStats: sm.ddhsortstreams += time.time() - startt

        if collectStats: startt = time.time()
        ## convert streams from data points to weekblocks
        for s in range(len(rawblocks)):
            runningdata = []
            runningblocks = []
            for d in rawblocks[s]:
                runningdata.append((d.date, d.relative_interest))
                if date.fromisoformat(d.date).weekday() == 5: ## saturday, end of week block
                    runningblocks.append(WeekBlock(runningdata))
                    runningdata = []
            if runningdata: ## partial block at end
                runningblocks.append(WeekBlock(runningdata))

            self.blockManagers.append(WeekBlockList(runningblocks))
        if collectStats: sm.ddhconverttoweekblocks += time.time() - startt

        if collectStats: startt = time.time()
        ## trim partial blocks between streams, leaving only possibly one at beginning of stream 0 and one at end of highest stream
        for s in range(len(self.blockManagers)):
            firstblock = self.blockManagers[s].getFirstBlock()
            lastblock = self.blockManagers[s].getLastBlock()
            if s != 0:
                if firstblock.isPartial(): self.blockManagers[s].blocks.remove(firstblock)
            if s != len(self.blockManagers) - 1:
                if lastblock.isPartial(): self.blockManagers[s].blocks.remove(lastblock)
        if collectStats: sm.ddhtrimpartials += time.time() - startt

    def getStream(self, index) -> WeekBlockList:
        return self.blockManagers[index]
    def numberOfStreams(self):
        return len(self.blockManagers)
    
    ## return set of all unique months for which there is some data
    def getMonths(self) -> Set[date]:
        if hasattr(self, 'monthCoverage'): return self.monthCoverage

        self.monthCoverage = set()
        for s in range(self.numberOfStreams()):
            curstream = self.getStream(s)
            for blk in curstream.blocks:
                self.monthCoverage.add(asMonthKey(blk.getStartDate()))
                self.monthCoverage.add(asMonthKey(blk.getEndDate()))
        return self.monthCoverage

    ## merge all streams, keeping original block over new blocks on conflict
    def getConsolidatedDict(self):
        # if collectStats: startt = time.time()
        # consolidatDict = {}
        # for s in range(self.numberOfStreams()):
        #     for b in self.blockManagers[s].blocks:
        #         if s > 0 and b in self.blockManagers[s-1].blocks: continue
        #         consolidatDict = {**consolidatDict, **b.data}
        # if collectStats: sm.consoldictloopspread1 += time.time() - startt

        ## alt2, very marginally faster with only stream 0, TODO retest with multiple streams
        consolidatDict = {}
        if collectStats: startt = time.time()
        for s in range(self.numberOfStreams()):
            for b in self.blockManagers[s].blocks:
                consolidatDict = {**b.data, **consolidatDict}
        if collectStats: sm.consoldictloopspread2 += time.time() - startt

        return consolidatDict

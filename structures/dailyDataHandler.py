import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from copy import deepcopy
from datetime import date
from typing import Dict, List

from globalConfig import config as gconfig
from structures.weekBlock import WeekBlock
from structures.weekBlockList import WeekBlockList

## helper for googleInterestsHandler: parses and organizes the raw data into a more accessible form for the purposes of calculating the overall relative interest for each day
class DailyDataHandler:
    ## streams
    # blockManagers: List[WeekBlockList] = []

    def __init__(self, dailygdata) -> None:
        self.blockManagers: List[WeekBlockList] = []

        ## setup streams
        maxstream = -1
        for d in dailygdata:
            if d.stream > maxstream: maxstream = d.stream
        rawblocks = [[] for x in range(maxstream+1)]
        
        ## separate data into streams
        for d in dailygdata:
            rawblocks[d.stream].append(d)

        ## sort streams
        for s in range(len(rawblocks)):
            rawblocks[s].sort(key=lambda a: a.date)

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

        ## trim partial blocks between streams, leaving only possibly one at beginning of stream 0 and one at end of highest stream
        for s in range(len(self.blockManagers)):
            firstblock = self.blockManagers[s].getFirstBlock()
            lastblock = self.blockManagers[s].getFirstBlock()
            if s != 0:
                if firstblock.isPartial(): self.blockManagers[s].blocks.remove(firstblock)
            if s != len(self.blockManagers) - 1:
                if lastblock.isPartial(): self.blockManagers[s].blocks.remove(lastblock)

    def getStream(self, index):
        return self.blockManagers[index]
    def numberOfStreams(self):
        return len(self.blockManagers)

    ## merge all streams, keeping original block over new blocks on conflict
    def getConsolidatedDict(self):
        consolidatBlocks: List[WeekBlock] = deepcopy(self.blockManagers[0].blocks)
        for s in range(1,len(self.blockManagers)):
            for b in self.blockManagers[s].blocks:
                if b in consolidatBlocks: continue
                consolidatBlocks.append(b)
        ## spread into date: value dict
        consolidatDict = {}
        for b in consolidatBlocks:
            consolidatDict = {**consolidatDict, **b.data}
        
        return consolidatDict

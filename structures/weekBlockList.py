import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import List

from structures.weekBlock import WeekBlock

class WeekBlockList:
    # blocks: List[WeekBlock] = []

    def __init__(self, blocks) -> None:
        self.blocks: List[WeekBlock] = blocks
        pass

    def getLastBlock(self):
        return self.blocks[-1]
    def getFirstBlock(self):
        return self.blocks[0]
    def getLastFullBlock(self):
        if self.blocks[-1].isPartial():
            return self.blocks[-2]
        return self.getLastBlock()
    def getFirstFullBlock(self):
        if self.blocks[0].isPartial():
            return self.blocks[1]
        return self.getFirstBlock()
    def getBlock(self, dt:str):
        for b in self.blocks:
            if dt <= b.getEndDate(): return b
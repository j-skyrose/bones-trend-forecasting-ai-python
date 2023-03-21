import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import List
from utils.support import GetMemoryUsage, getIndex, shortc

class StockSplitsHandler(GetMemoryUsage):
    exchange = None
    symbol = None
    data: List = []

    def __init__(self, exchange, symbol, data):
        self.exchange = exchange
        self.symbol = symbol
        self.data = data

    def getTickerTuple(self):
        return (self.exchange, self.symbol)

    def getForRange(self, start, end):
        startIndex = getIndex(self.data, lambda d: d.date > start)
        if startIndex is None:
            return []
        endIndex = shortc(getIndex(self.data, lambda d: d.date > end), len(self.data))
        if startIndex == endIndex:
            return []
        return self.data[startIndex:endIndex]

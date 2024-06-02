import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, math
from typing import Dict, List, Tuple

from constants.values import stockOffset
from managers.databaseManager import DatabaseManager
from structures.optionsContract import OptionsContract
from utils.support import GetMemoryUsage, asISOFormat, getItem
from utils.types import TickerKeyType


dbm: DatabaseManager = DatabaseManager()

class OptionsDataHandler(GetMemoryUsage):

    def __init__(self, exchange, symbol, offset=stockOffset, jitInitialization=True):
        self.exchange = exchange
        self.symbol = symbol

        self.dataOffset = offset
        self.jitInitialization = jitInitialization

        self.data: Dict[OptionsContract, List] = {}
        self.initializedTickers = False
        self.initializedData = False
        if not self.jitInitialization:
            self._initialize()

    def getInitializedTickerCount(self):
        if not self.initializedTickers: return 0
        return sum([1 for d in self.data.values() if type(d) == list and len(d) > 0])

    def initialized(self):
        return self.initializedTickers and self.initializedData

    def getTickerTuple(self) -> Tuple[str,str]:
        return (self.exchange, self.symbol)

    def getTickerKey(self) -> TickerKeyType:
        return TickerKeyType(*self.getTickerTuple())

    def _initialize(self):
        self._initializeTickers()
        self._initializeData()

    def _initializeTickers(self):
        if self.initializedTickers: return
        distinctTickers = DatabaseManager().getDistinct('options_contract_info_polygon_d', 'ticker', underlyingTicker=self.symbol)
        for r in distinctTickers:
            self.data[r] = None if self.jitInitialization else []
        self.initializedTickers = True

    def _initializeDatum(self, oc:str):
        self._initializeTickers()
        if self.data[oc] is None:
            self.data[oc] = DatabaseManager().getOptionsDataDaily_basic(ticker=oc, orderBy='period_date')

    def _initializeData(self):
        if self.initializedData: return
        self._initializeTickers()
        contractKeys = list(self.getOptionsContractKeys())
        if len(contractKeys) > 0:
            for tickerChunk in numpy.array_split(contractKeys, int(math.ceil(len(contractKeys)/950))): ## max sqlite args=999
                dataChunk = dbm.getOptionsDataDaily_basic(ticker=tickerChunk, orderBy='period_date')
                for d in dataChunk:
                    self.data[d.ticker].append(d)
        self.initializedData = True

    def getDay(self, ticker, dt):
        '''gets prices object at given date'''
        self._initializeTickers()
        ticker = ticker.getTicker() if type(ticker) is OptionsContract else ticker
        self._initializeDatum(ticker)
        
        return getItem(self.data[ticker], lambda x: x.period_date == asISOFormat(dt))
    
    def getOptionsContractKeys(self, asStrings=True):
        self._initializeTickers()
        if asStrings:
            return self.data.keys()
        else:
            return [OptionsContract.fromTicker(t) for t in self.data.keys()]

if __name__ == '__main__':
    pass
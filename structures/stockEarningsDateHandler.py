import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import bisect
from typing import Dict, List, Tuple

from managers.databaseManager import DatabaseManager
from utils.support import GetMemoryUsage, shortc

class StockEarningsDateHandler(GetMemoryUsage):

    def __init__(self, exchange=None, symbol=None, dbData=[]):
        self.sorted = False
        if len(dbData) > 0:
            self.exchange = shortc(exchange, dbData[0].exchange)
            self.symbol = shortc(symbol, dbData[0].symbol)

        self.data = [(r.input_date, r.earnings_date) for r in dbData]
        self._sort()

        ## cache getNextEarningsDate results
        self.cache: Dict[str, str] = {}

    ## maintains tuple list in sorted order by input date, then earnings date
    def _sort(self):
        if self.sorted: return
        self.data.sort(key=lambda r: r[0]+r[1])
        self.sorted = True

    def add(self, inputDate, earningsDate):
        bisect.insort(self.data, (inputDate, earningsDate))
    
    def _get(self, dt):
        if not self.sorted: self._sort()
        if len(self.data) == 0: return

        maxInputDate = self.data[-1][0] if dt < self.data[0][0] else dt
        for indx in range(len(self.data)-2, -1, -1):
            if self.data[indx][0] > maxInputDate: continue
            if self.data[indx][1] < dt: return self.data[indx+1][1]

        return self.data[0][1]

    def getNextEarningsDate(self, fromDate):
        try:
            return self.cache[fromDate]
        except KeyError:
            val = self._get(fromDate)
            self.cache[fromDate] = val
            return val

if __name__ == '__main__':
    dbm: DatabaseManager = DatabaseManager()
    h: StockEarningsDateHandler = StockEarningsDateHandler(dbData=dbm.getEarningsDates_basic('NASDAQ', 'CNP'))
    print(h.getNextEarningsDate('2022-08-08'))
    print(h.getNextEarningsDate('2023-05-06'))
    print(h.getNextEarningsDate('2021-05-06'))
    print(h.getNextEarningsDate('2022-05-06'))
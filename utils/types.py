import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import Dict, Tuple

class TickerKeyType:
    """tuple(exchange, symbol)"""
    exchange: str=None
    symbol: str=None

    def __init__(self, exchange:str, symbol:str):
        self.exchange = exchange
        self.symbol = symbol

    def getTuple(self) -> Tuple[str,str]:
        return (self.exchange, self.symbol)

    def __eq__(self, __o: object) -> bool:
        try:
            if type(__o) is tuple:
                return self.exchange == __o[0] and self.symbol == __o[1]
            return self.exchange == __o.exchange and self.symbol == __o.symbol
        except (KeyError, IndexError):
            return False
    
    def __hash__(self) -> int:
        # v= hash((self.exchange, self.symbol))
        # print('ticker',v)
        # return v
        return hash((self.exchange, self.symbol))

class TickerDateKeyType:
    """tuple(exchange, symbol, date[isoformat string])"""
    ticker: TickerKeyType=None
    date: str=None

    def __init__(self, exchange:str, symbol:str, date:str):
        self.ticker = TickerKeyType(exchange, symbol)
        self.date = date

    def __eq__(self, __o: object) -> bool:
        try:
            if type(__o) is tuple:
                if len(__o) == 2:
                    return self.ticker == __o[0] and self.date == __o[1]
                return self.ticker.exchange == __o[0] and self.ticker.symbol == __o[1] and self.date == __o[2]
            return self.ticker == __o.ticker and self.date == __o.date
        except KeyError:
            return False

    def __hash__(self) -> int:
        # # v=hash((self.ticker.exchange, self.ticker.symbol, self.date))
        # v=hash((self.ticker, self.date))
        # print('date',v)
        # return v
        return hash((self.ticker, self.date))

# t1 = TickerDateKeyType(1,2,3)
# t2 = (1,2,3)
# # t2 = ((1,2),3)
# t3 = TickerDateKeyType(1,2,3)
# # print(t1==t2)
# # print(t1==t3)

# d = {}
# d[t1] = 2
# print(d[t2])
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm
from datetime import timedelta
from typing import Dict, List, Tuple

from constants.enums import OptionType
from constants.values import stockOffset
from managers.databaseManager import DatabaseManager
from structures.optionsContract import OptionsContract
from structures.optionsDataHandler import OptionsDataHandler
from utils.collectorSupport import getExchange
from utils.support import Singleton, asDate

dbm: DatabaseManager = DatabaseManager()

def _getExchangeSymbol(t):
    try:
        exchange, symbol = t
    except:
        exchange = t.exchange
        symbol = t.symbol
    return exchange, symbol

class OptionsDataManager(Singleton):
    normalized = False
    shouldNormalize = False

    def __init__(self, symbolList=[], normalize=False, dataOffset=stockOffset, jitInitialization=True):
        self.shouldNormalize = normalize
        self.jitInitialization = jitInitialization
        self.symbolList = symbolList

        self.getTickersCache = {}

        self.data: Dict[Tuple[str,str],OptionsDataHandler] = {}
        self.addSymbols(self.symbolList)

    def addSymbols(self, symbolList):
        for t in tqdm.tqdm(symbolList, leave=False, desc=f"Initializing option {'placeholders' if self.jitInitialization else 'data'}"):
            exchange, symbol = _getExchangeSymbol(t)
            if exchange is None: continue
            if symbol not in self.data.keys():
                self.data[symbol] = OptionsDataHandler(exchange, symbol, offset=stockOffset, jitInitialization=self.jitInitialization)
    
    def _get(self, symbol):
        '''returns the OptionsDataHandler for given symbol'''
        if symbol not in self.data.keys():
            if not self.jitInitialization:
                raise KeyError(symbol)
            else:
                exchange = getExchange(symbol)
                if exchange is None: raise ValueError(f'Unable to determine exchange for {symbol}')
                self.addSymbols(symbolList=[(exchange, symbol)])
        return self.data[symbol]

    def getTickers(self, symbol, expiringWeekDate=None, strike=None, strikeAbove=None, strikeBelow=None, contractType:OptionType=None) -> List[OptionsContract]:
        '''gets all options tickers for the given symbol that meet the expiry week and strike parameters'''
        if list(s is not None for s in [strike, strikeAbove, strikeBelow]).count(True) > 1: raise ValueError

        if not self.jitInitialization and symbol not in self.data.keys(): return ## no tickers, no data

        expiringWeekMonday = asDate(expiringWeekDate)
        expiringWeekMonday -= timedelta(days=expiringWeekMonday.weekday())
        cacheKey = (symbol, expiringWeekMonday, strike, strikeAbove, contractType)
        try:
            return self.getTickersCache[cacheKey]
        except KeyError:
            matchLambdas = []

            ## expiring the desired week; rarely not on Friday, e.g. Thursday or Saturday
            matchLambdas.append(lambda x: 0 <= (asDate(x.expirationDate) - expiringWeekMonday).days < 6)
            
            ## fulfills desired strike(s)
            if strike: matchLambdas.append(lambda x: x.strikePrice == strike)
            elif strikeAbove: matchLambdas.append(lambda x: x.strikePrice > strikeAbove)
            elif strikeBelow: matchLambdas.append(lambda x: x.strikePrice < strikeBelow)

            ## correct contract type
            if contractType: matchLambdas.append(lambda x: x.optionType == contractType)

            res = [k for k in self._get(symbol).getOptionsContractKeys(asStrings=False) if all(m(k) for m in matchLambdas)]
            res.sort(key=lambda x: x.strikePrice)

            ## cache results
            self.getTickersCache[cacheKey] = res

            return res
    
    def getDay(self, symbol, ticker, dt):
        '''gets prices object at given date'''
        return self.data[symbol].getDay(ticker, dt)

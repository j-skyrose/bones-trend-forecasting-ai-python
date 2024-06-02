import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import re
from datetime import date
from typing import Tuple

from constants.enums import OptionType
from utils.support import asDate, asEnum

class OptionsContract:
    
    def __init__(self, symbol, expirationDate, optionType:OptionType, strikePrice) -> None:
        self.symbol = symbol
        self.expirationDate = asDate(expirationDate)
        self.optionType = asEnum(optionType, OptionType)
        self.strikePrice = strikePrice

    def __eq__(self, __o: object) -> bool:
        try:
            if type(__o) is tuple and len(__o) == 4:
                return self.symbol == __o[0] and self.expirationDate == asDate(__o[1]) and self.optionType == asEnum(__o[2], OptionType) and self.strikePrice == __o[3]
            elif type(__o) is OptionsContract:
                return self.symbol == __o.symbol and self.expirationDate == asDate(__o.expirationDate) and self.optionType == __o.optionType and self.strikePrice == __o.strikePrice
            elif type(__o) is str:
                return self.__eq__(OptionsContract.parseTicker(__o))
            return False
        except KeyError:
            return False

    def getTicker(self, withOPrefix=True):
        return f"{'O:' if withOPrefix else ''}{self.symbol}{self.expirationDate.strftime('%y%m%d')}{'C' if self.optionType == OptionType.CALL else 'P'}{int(self.strikePrice*1000):0>8}"

    def __hash__(self) -> int:
        return hash((self.symbol, self.optionType, self.expirationDate, self.strikePrice))

    @staticmethod
    def _parseDate(dt):
        if len(dt) > 6:
            # sometimes year is 3 digits, e.g. 124
            dt = dt[1:]
        year = int(dt[:2]) % 100 
        year += 1900 if year > date.today().year - 2000 else 2000
        return date(year, int(dt[2:4]), int(dt[4:]))

    @classmethod
    def parseTicker(cls, ticker:str) -> Tuple[str, date, OptionType, float]:
        '''Parses option ticker (e.g. AACQ210219C00017500) into symbol, expiration date, type, and strike price'''

        ticker = ticker.replace('O:', '')
        _, symbol, expirationDate, optionType, strikePrice, _ = re.split(r'(\D+)(\d+)(\D)(\d+)', ticker)
        expirationDate = cls._parseDate(expirationDate)
        optionType = OptionType.CALL if optionType == 'C' else OptionType.PUT
        strikePrice = int(strikePrice) / 1000

        return symbol, expirationDate, optionType, strikePrice

    @classmethod
    def fromTicker(cls, ticker):
        return cls(*cls.parseTicker(ticker))

    @classmethod
    def getSymbol(cls, ticker):
        symbol, _,_,_ = cls.parseTicker(ticker)
        return symbol
    @classmethod
    def getExpirationDate(cls, ticker):
        _, expirationDate, _,_ = cls.parseTicker(ticker)
        return expirationDate
    @classmethod
    def getOptionType(cls, ticker):
        _,_, optionType, _ = cls.parseTicker(ticker)
        return optionType
    @classmethod
    def getStrikePrice(cls, ticker):
        _,_,_, strikePrice = cls.parseTicker(ticker)
        return strikePrice
    
    
if __name__ == '__main__':
    res = OptionsContract.parseTicker('O:AACQ210219C00017500')
    print(res)
    res2 = OptionsContract.fromTicker('O:AACQ210219C00017500')
    print(res2)
    print(OptionsContract.getExpirationDate('O:AACQ210219C00017500'))
    print(res2.getTicker())
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import Dict
from utils.support import GetMemoryUsage, recdotobj

class GoogleInterestsHandler(GetMemoryUsage):
    # exchange = None
    # symbol = None
    # data: Dict[str,float]

    def __init__(self, exchange, symbol, relativedata):
        self.exchange = exchange
        self.symbol = symbol
        self.dataDict: Dict[str,float] = {}
        for r in relativedata:
            self.dataDict[r.date] = r.relative_interest

    def getTickerTuple(self):
        return (self.exchange, self.symbol)

    ## precending range of data, adjusted so max is 100
    ## dt = day before anchor date, so will have stock data
    ## offset as up-to-date data would only be available after 3 days
    def getPrecedingRange(self, dt: str, precrange, offset=2) -> Dict[str,float]:
        offsetStarted = False
        retdict = {}
        for k,v in reversed(list(self.dataDict.items())):
            if not offsetStarted:
                if k == dt: offsetStarted = True
            elif offset > 0:
                offset -= 1
            else:
                retdict[k] = v
                if len(retdict) == precrange: break
        
        if len(retdict) > 0:
            ## adjust data up
            maxv = max(retdict.values())
            if maxv > 0:
                for k in retdict.keys():
                    retdict[k] *= (100 / maxv)

        return retdict


if __name__ == '__main__':
    ## testing
    data=recdotobj([{'date':'2022-01-01', 'relative_interest':83},{'date':'2022-01-02', 'relative_interest':86},{'date':'2022-01-03', 'relative_interest':89},{'date':'2022-01-04', 'relative_interest':92},{'date':'2022-01-05', 'relative_interest':95},{'date':'2022-01-06', 'relative_interest':98},{'date':'2022-01-07', 'relative_interest':61},{'date':'2022-01-08', 'relative_interest':64},{'date':'2022-01-09', 'relative_interest':67},{'date':'2022-01-10', 'relative_interest':70},{'date':'2022-01-11', 'relative_interest':73},{'date':'2022-01-12', 'relative_interest':76},{'date':'2022-01-13', 'relative_interest':79},{'date':'2022-01-14', 'relative_interest':82},{'date':'2022-01-15', 'relative_interest':85},{'date':'2022-01-16', 'relative_interest':88},{'date':'2022-01-17', 'relative_interest':91},{'date':'2022-01-18', 'relative_interest':94},{'date':'2022-01-19', 'relative_interest':97},{'date':'2022-01-20', 'relative_interest':100}])
    g = GoogleInterestsHandler('','',data)
    print(g.getPrecedingRange('2022-01-12', 8))

    
    
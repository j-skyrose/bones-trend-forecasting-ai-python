import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"


import tqdm
from datetime import date, datetime

from managers.databaseManager import DatabaseManager
from managers.marketDayManager import MarketDayManager
from utils.support import Singleton, asList, recdotdict, shortc
from constants.enums import OperatorDict, SeriesType

dbm: DatabaseManager = DatabaseManager()

class DataAnalzer:
    result = None

    def __init__(self, limit=None):
        self.limit = limit

    def __processChangeFunction(self, anchorDate, exchanges, meetsCriteriaFunction):
        anchorDate = self._massageAnchorDate(anchorDate)
        if not self.result:
            symbols = []
            self.result = []
            for e in exchanges:
                symbols.extend(dbm.getSymbols(exchange=e))
        else:
            symbols = self.result
            self.result = []

        count = 0
        for s in tqdm.tqdm(symbols[:shortc(self.limit, len(symbols))], desc='Evaluating symbols for change'):
            if self.limit:
                count += 1
                if count > self.limit: break

            stockdata = dbm.getStockData(s.exchange, s.symbol, SeriesType.DAILY)
            anchorDateIndex = None
            for p in range(len(stockdata)):
                if stockdata[p].date == anchorDate: 
                    anchorDateIndex = p
                    break
            if not anchorDateIndex:
                continue
            
            if stockdata[anchorDateIndex].artificial: 
                ## no use checking if stock was not even traded on anchor date
                continue

            if not meetsCriteriaFunction(stockdata, anchorDateIndex):
                continue
            # op = OperatorDict.LESSTHANOREQUAL.function if change >= 1 else OperatorDict.GREATERTHANOREQUAL.function
            # if op(stockdata[anchorDateIndex].close / stockdata[anchorDateIndex-1].close, change):
            #     ## does not meet close change threshold
            #     continue

            self.result.append(s)        

        return self


    def _massageAnchorDate(self, anchorDate):
        if not anchorDate:
            anchorDate = date.today()
        if type(anchorDate) == str:
            anchorDate = date.fromisoformat(anchorDate)
        return MarketDayManager.getLastMarketDay(anchorDate).isoformat()

    def andPriceMoving(self, **kwargs):
        return self.getStocksWithPriceMoving(**kwargs)
    def getStocksWithPriceMoving(self, anchorDate=None, exchange=None, change=1):
        def meetsCriteriaFunction(data, index):
            op = OperatorDict.LESSTHANOREQUAL.function if change >= 1 else OperatorDict.GREATERTHANOREQUAL.function
            if op(data[index].close / data[index-1].close, change):
                ## does not meet close change threshold
                return False
            return True      
        return self.__processChangeFunction(anchorDate, asList(exchange), meetsCriteriaFunction)

    def andVolumeSMAMoving(self, **kwargs):
        return self.getStocksWithVolumeSMA(**kwargs)
    def getStocksWithVolumeSMAMoving(self, anchorDate=None, exchange=None, change=1, smaDays=1):
        def meetsCriteriaFunction(data, index):
            if index < smaDays:
                ## not enough days in past for volume SMA
                return False

            smaVolume = 0
            for i in range(index - (smaDays+1), index):
                smaVolume += data[i].volume
            smaVolume /= smaDays
            if data[index].volume <= smaVolume * change:
                ## does not meet volume increase threshold
                return False

            return True    
        return self.__processChangeFunction(anchorDate, asList(exchange), meetsCriteriaFunction)

# def getStocksMovingSharplyHigherOnLargeVolume(anchorDate=None, exchange=None, priceChange=1.15, volumeChange=4, volumeSMADays=20):
#     print('Anchor date:', anchorDate)


# if anchorDateIndex < volumeSMADays:
#                 ## not enough days in past for volume SMA
#                 continue

#                 smaVolume = 0
#             for i in range(anchorDateIndex - (volumeSMADays+1), anchorDateIndex):
#                 smaVolume += stockdata[i].volume
#             smaVolume /= volumeSMADays

#             if stockdata[anchorDateIndex].volume <= smaVolume * volumeChange:
#                 ## does not meet volume increase threshold
#                 continue


#     print('Stocks meeting all criteria')
#     for s in notableSymbols:
#         print(s.exchange, ':', s.symbol, '-', s.name)

def prettyPrintResults(results):
    if hasattr(results, 'result'):
        results = results.result
    print('Stocks meeting all criteria')
    for s in results:
        print(s.exchange, ':', s.symbol, '-', s.name)

if __name__ == '__main__':
    # getStocksMovingSharplyHigherOnLargeVolume(exchange=['NASDAQ'], anchorDate='2021-11-04')
    # res = DataAnalzer(100).getStocksWithPriceMoving(exchange=['NYSE'], change=1.01)
    res = DataAnalzer().getStocksWithVolumeSMAMoving(exchange=['NYSE'], change=1.01, smaDays=5).andPriceMoving(change=0.98)

    prettyPrintResults(res)

    pass
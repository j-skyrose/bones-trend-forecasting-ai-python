import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import atexit, time
from datetime import date

from constants.exceptions import APILimitReached, APITimeout, NotSupportedYet
from constants.enums import FinancialStatementType, LimitType, MarketType, TimespanType
from managers.configManager import StaticConfigManager, SavedStateManager
from structures.api.alphavantage import Alphavantage
from structures.api.polygon import Polygon
from structures.api.fmp import FMP
from structures.api.neo import NEO
from utils.support import Singleton, asDate, recdotdict, recdotobj, shortc

class APIManager(Singleton):

    def __init__(self, currentDate=date.today()):
        atexit.register(self.saveConfig)

        self.currentDate = asDate(currentDate)
        self.config = StaticConfigManager()
        self.savedState = SavedStateManager()

        self.apis = {}
        self._initializeAPI('alphavantage', Alphavantage)
        self._initializeAPI('polygon', Polygon)
        self._initializeAPI('fmp', FMP)
        self._initializeAPI('neo', NEO, requiresAPIKey=False)

        ## update 'remaining' counts
        for a in self.apis.keys():
            self._checkLimits(self.apis[a], updateOnly=True)

    def saveConfig(self):
        for api in self.apis.keys():
            self.savedState.set(api, 'remaining', self.apis[api].remaining)
            self.savedState.set(api, 'updated', self.apis[api].updatedOn)
        self.savedState.save()
        self.config.save()
        print('saved config and state')

    def _initializeAPI(self, apiName, apiClass, requiresAPIKey=True):
        url = self.config.get(apiName, 'url', required=True)
        apiKey = self.config.get(apiName, 'apikey', required=requiresAPIKey)

        self.apis[apiName] = recdotdict({
            'api': apiClass(url, key=apiKey),
            'limit': self.config.get(apiName, 'limit'),
            'limitType': self.config.get(apiName, 'limittype'),
            'priority': self.config.get(apiName, 'priority'),
            'remaining': self.savedState.get(apiName, 'remaining'),
            'updatedOn': date.fromisoformat(self.savedState.get(apiName, 'updated'))
        })


    def getAPIList(self, sort=False):
        if sort:
            return sorted(self.apis.keys(), key=lambda a: self.apis[a]['priority'], reverse=True)
        return self.apis.keys()

    def _checkLimits(self, a, seriesType=None, qdate=None, updateOnly=False):
        sameDate = False
        if a.limitType == LimitType.NONE:
            if qdate: a.updatedOn = date.fromisoformat(qdate)
            return 999
        elif a.limitType == LimitType.DAILY:
            sameDate = self.currentDate == a.updatedOn
        elif a.limitType == LimitType.WEEKLY:
            ## todo, if API found for this type
            pass
        elif a.limitType == LimitType.MONTHLY:
            sameDate = self.currentDate.month() == a.updatedOn.month()

        if sameDate:
            if a.remaining <= 0:
                if not updateOnly: raise APILimitReached
        else:
            if not updateOnly: a.updatedOn = self.currentDate
            a.remaining = a.limit

        return a.remaining

    def __executeAPIRequest(self, apih, func, verbose=0):
        ret = None
        for i in range(2):
            try:
                ret = func()
                break
            except APITimeout:
                if verbose >= 1: print('API timed out')
                time.sleep(60)
                if verbose >= 1: print('Retrying...')
        if ret is None:
            if apih.limitType != LimitType.NONE: apih.remaining = 0
            raise APILimitReached

        if apih.limitType != LimitType.NONE and apih.remaining: apih.remaining -= 1

        return ret

    def _executeRequestWrapper(self, api, requestFunc, seriesType=None, queryDate=None, verbose=0):
        apiHandle = self.apis[api]
        self._checkLimits(apiHandle, seriesType, queryDate)

        return recdotobj(self.__executeAPIRequest(apiHandle, lambda: requestFunc(apiHandle), verbose))

    def query(self, api, symbol=None, seriesType=None, qdate=None, exchange=None, fromDate=None, toDate=None, avCompact=False, verbose=0):
        ## polygon
        if qdate:
            queryArgs = (qdate, verbose)
        ## neo
        elif fromDate and toDate:
            queryArgs = (symbol, fromDate, toDate, verbose)
        ## alphavantage
        else:
            queryArgs = (seriesType, symbol, exchange, avCompact)
        return self._executeRequestWrapper(
            api,
            lambda apih: apih.api.query(*queryArgs),
            seriesType,
            qdate,
            verbose=verbose
        )
    
    def getSimpleQuote(self, symbol=None, api='fmp', verbose=0, mock=False):
        if api != 'fmp': raise NotSupportedYet
        return self._executeRequestWrapper(
            api,
            (lambda apih: apih.api.getSimpleQuote(symbol)) if not mock else (lambda apih: {'test': 'test'}),
            verbose=verbose
        )

    def getAggregates(self, api='polygon', symbol=None, multipler=None, timespan=None, fromDate=None, toDate=None, limit=50000, verbose=0):
        return self._executeRequestWrapper(
            api,
            lambda apih: apih.api.getAggregates(symbol, shortc(multipler, 1), shortc(timespan, TimespanType.MINUTE), fromDate, toDate, limit, verbose),
            verbose=verbose
        )

    ## polygon
    def getFinanicals(self, api, symbol, ftype, stype):
        lmb = lambda apih: apih.api.getFinancials(symbol, ftype)
        if api == 'fmp' or api == 'alphavantage':
            if stype == FinancialStatementType.INCOME:
                lmb = lambda apih: apih.api.getFinancials_income(symbol, ftype)
            elif stype == FinancialStatementType.BALANCE_SHEET:
                lmb = lambda apih: apih.api.getFinancials_balance(symbol, ftype)
            elif stype == FinancialStatementType.CASH_FLOW:
                lmb = lambda apih: apih.api.getFinancials_cashflow(symbol, ftype)

        return self._executeRequestWrapper(api, lmb)

    ## polygon only
    def getStockSplits(self, api, **kwargs):
        return self._executeRequestWrapper(
            api,
            lambda apih: apih.api.getStockSplits(**kwargs)
        )


    # ## fmp
    # def getFinancials_income(self, api, symbol, ftype):
    #     return self._executeRequestWrapper(
    #         api,
    #         lambda apih: apih.api.getFinancials_income(symbol, ftype)
    #     )

    # ## fmp
    # def getFinancials_balance(self, api, symbol, ftype):
    #     return self._executeRequestWrapper(
    #         api,
    #         lambda apih: apih.api.getFinancials_balance(symbol, ftype)
    #     )

    # ## fmp
    # def getFinancials_cashflow(self, api, symbol, ftype):
    #     return self._executeRequestWrapper(
    #         api,
    #         lambda apih: apih.api.getFinancials_cashflow(symbol, ftype)
    #     )                

    # def query(self, api, symbol=None, stype=None, qdate=None):
    #     apih = self.apis[api]
    #     self._checkLimits(apih, stype, qdate)

    #     func = (lambda: apih.api.query(stype, symbol)) if not qdate else (lambda: apih.api.query(qdate))

    #     ret = self.__executeAPIRequest(apih, func)

    #     return recdotobj(ret) ## if type(ret) is not list else ret

    # def getTickerDetails(self, api, symbol):
    #     apih = self.apis[api]
    #     self._checkLimits(apih)

    #     func = lambda: apih.api.getTickerDetails(symbol)
    #     ret = self.__executeAPIRequest(apih, func)

    #     return recdotobj(ret) ## if type(ret) is not list else ret

    def getTickers(self, api,  
                   onlyPage=None, limit=None, ## debugging/throttling
                   verbose=0, **kwargs):
        '''Query all ticker symbols which are supported by the given API'''

        if api != 'polygon': raise NotSupportedYet()

        apiHandle = self.apis[api]

        pageIndex = 1
        tickers = []
        resp = self.__executeAPIRequest(apiHandle, lambda: apiHandle.api.getTickers(verbose=verbose, **kwargs), verbose=verbose)
        while True:
            data = resp['results']

            if verbose: print(len(data),'tickers retrieved')
            if onlyPage is None or pageIndex == onlyPage:
                tickers.extend(data)

            if (onlyPage is not None and pageIndex == onlyPage) or (limit is not None and len(tickers) >= limit):
                if limit is not None: tickers = tickers[:limit]
                break ## got required page/amount, no need to request further
            if 'next_url' in resp.keys():
                if verbose: print('has next url')
                resp = self.__executeAPIRequest(apiHandle, lambda: apiHandle.api.getNextURL(resp['next_url']), verbose=verbose)
            else:
                if verbose: print('was last page')
                break
            pageIndex += 1
        
        return tickers

    def getTickerDetails(self, api, ticker, asOfDate=None, verbose=0):
        return self._executeRequestWrapper(
            api,
            lambda apih: apih.api.getTickerDetails(ticker, asOfDate=asOfDate, verbose=verbose),
            verbose=verbose
        )

def getPolygonSymbols():
    from utils import convertListToCSV

    apim = APIManager()
    tickers = apim.getTickers('polygon')
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'raw/symbol_dumps/polygon/reference_tickers.csv'), 'w', encoding='utf-8') as f:
        f.write(convertListToCSV(tickers, excludeColumns=['codes']))
    print('done with some data massaging requried (commas in company names, tickers with spaces, etc.)')


if __name__ == '__main__':
    apim = APIManager()
    # res = apim.query('alphavantage', exchange='NASDAQ', symbol='HOL', seriesType=SeriesType.DAILY_ADJUSTED)
    # print(res[-50:])
    # r = apim.getSimpleQuote('DAL', mock=True)
    r = apim.getTickers('polygon', verbose=2, active=True, market=MarketType.STOCKS)
    print(len(r))

# with open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'raw/symbol_dumps/polygon/reference_tickers.csv'), 'r', encoding='utf-8') as f:
#     f.readline()
#     symbolwithspaces = set()
#     marketset = set()
#     typeset = set()
#     exchangeset= set()
#     for line in f:
#         l = line.split(',')
#
#         if l[7]=='True': print(line,'\n',l)
#
#         if (' ' in l[0]): symbolwithspaces.add(l[0])
#         marketset.add(l[2])
#         typeset.add(l[4])
#         exchangeset.add(l[7])
#     print('symbosl with space',symbolwithspaces)
#     print('market set',marketset)
#     print('typeset',typeset)
#     print('exchangeset',exchangeset)

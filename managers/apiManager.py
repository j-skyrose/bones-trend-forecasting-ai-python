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
from constants.enums import Api, FinancialStatementType, LimitType, TimespanType
from managers.configManager import StaticConfigManager, SavedStateManager
from structures.api.alphavantage import Alphavantage
from structures.api.finra import FINRA
from structures.api.google import Google
from structures.api.nasdaq import Nasdaq
from structures.api.polygon import Polygon
from structures.api.fmp import FMP
from structures.api.neo import NEO
from structures.api.yahoo import Yahoo
from structures.scraper.marketWatch import MarketWatch
from utils.support import Singleton, asDate, recdotdict, recdotobj, shortc

class APIManager(Singleton):
    '''manages APIs, file requests, and web scrapers that are wrapped to function like APIs'''

    def __init__(self, currentDate=date.today()):
        atexit.register(self.saveConfig)

        self.currentDate = asDate(currentDate)
        self.config = StaticConfigManager()
        self.savedState = SavedStateManager()

        self.apis = {}
        self._initializeAPI(Api.ALPHAVANTAGE, Alphavantage)
        self._initializeAPI(Api.FMP, FMP)
        self._initializeAPI(Api.GOOGLE, Google, requiresAPIKey=False)
        self._initializeAPI(Api.MARKETWATCH, MarketWatch, requiresAPIKey=False)
        self._initializeAPI(Api.NASDAQ, Nasdaq, requiresAPIKey=False)
        self._initializeAPI(Api.NEO, NEO, requiresAPIKey=False)
        self._initializeAPI(Api.POLYGON, Polygon)
        self._initializeAPI(Api.YAHOO, Yahoo, requiresAPIKey=False)

        ## update 'remaining' counts
        for a in self.apis.keys():
            self._checkLimits(self.apis[a], updateOnly=True)

    @staticmethod
    def getEarningsCollectionAPIs():
        return [Api.MARKETWATCH, Api.NASDAQ, Api.YAHOO]

    def saveConfig(self):
        for api in self.apis.keys():
            apiName = api.name.lower()
            self.savedState.set(apiName, 'remaining', self.apis[api].remaining)
            self.savedState.set(apiName, 'updated', self.apis[api].updatedOn)
        self.savedState.save()
        self.config.save()
        print('saved config and state')

    def _initializeAPI(self, api:Api, apiClass, requiresAPIKey=True):
        apiName = api.name.lower()
        url = self.config.get(apiName, 'url', required=True)
        apiKey = self.config.get(apiName, 'apikey', required=requiresAPIKey)

        self.apis[api] = recdotdict({
            'api': apiClass(url, key=apiKey),
            'limit': self.config.get(apiName, 'limit'),
            'limitType': self.config.get(apiName, 'limittype'),
            'priority': self.config.get(apiName, 'priority'),
            'remaining': self.savedState.get(apiName, 'remaining', default=-1),
            'updatedOn': date.fromisoformat(self.savedState.get(apiName, 'updated', default='1970-01-01'))
        })

    def get(self, api:Api, handle=False):
        r = self.apis[api]
        return r if handle else r.api

    def getAPIList(self, sort=False):
        if sort:
            return sorted(self.apis.keys(), key=lambda a: self.apis[a]['priority'], reverse=True)
        return self.apis.keys()

    def _checkLimits(self, apih, seriesType=None, qdate=None, updateOnly=False):
        sameDate = False
        if apih.limitType == LimitType.NONE:
            if qdate: apih.updatedOn = date.fromisoformat(qdate)
            return 999
        elif apih.limitType == LimitType.DAILY:
            sameDate = self.currentDate == apih.updatedOn
        elif apih.limitType == LimitType.WEEKLY:
            ## todo, if API found for this type
            pass
        elif apih.limitType == LimitType.MONTHLY:
            sameDate = self.currentDate.month() == apih.updatedOn.month()

        if sameDate:
            if apih.remaining <= 0:
                if not updateOnly: raise APILimitReached
        else:
            if not updateOnly: apih.updatedOn = self.currentDate
            apih.remaining = apih.limit

        return apih.remaining

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

    def _executeRequestWrapper(self, api:Api, requestFunc, seriesType=None, queryDate=None, verbose=0):
        apiHandle = self.get(api, handle=True)
        self._checkLimits(apiHandle, seriesType, queryDate)

        return recdotobj(self.__executeAPIRequest(apiHandle, lambda: requestFunc(apiHandle), verbose))

    def query(self, api:Api, symbol=None, seriesType=None, qdate=None, exchange=None, fromDate=None, toDate=None, avCompact=False, verbose=0):
        if qdate:
            ## polygon
            if symbol: queryArgs = (symbol, qdate, verbose)
            else: queryArgs = (qdate, verbose)
        elif fromDate and toDate:
            ## neo
            queryArgs = (symbol, fromDate, toDate, verbose)
        else:
            ## alphavantage
            queryArgs = (seriesType, symbol, exchange, avCompact, verbose)
        
        requestFunc = lambda apih: apih.api.query(*queryArgs)
        if symbol and qdate:
            ## polygon non-market hours
            requestFunc = lambda apih: apih.api.getNonMarketHoursStockData(*queryArgs)

        return self._executeRequestWrapper(
            api,
            requestFunc,
            seriesType,
            qdate,
            verbose=verbose
        )
    
    def getSimpleQuote(self, symbol=None, api:Api=Api.FMP, verbose=0, mock=False):
        if api != Api.FMP: raise NotSupportedYet
        return self._executeRequestWrapper(
            api,
            (lambda apih: apih.api.getSimpleQuote(symbol)) if not mock else (lambda apih: {'test': 'test'}),
            verbose=verbose
        )

    def getAggregates(self, api:Api=Api.POLYGON, symbol=None, multipler=None, timespan=None, fromDate=None, toDate=None, limit=50000, verbose=0):
        return self._executeRequestWrapper(
            api,
            lambda apih: apih[api].getAggregates(symbol, shortc(multipler, 1), shortc(timespan, TimespanType.MINUTE), fromDate, toDate, limit, verbose),
            verbose=verbose
        )

    def getFinanicals(self, api:Api, symbol, ftype, stype):
        lmb = lambda apih: apih.api.getFinancials(symbol, ftype)
        if api in [Api.FMP, Api.ALPHAVANTAGE]:
            if stype == FinancialStatementType.INCOME:
                lmb = lambda apih: apih.api.getFinancials_income(symbol, ftype)
            elif stype == FinancialStatementType.BALANCE_SHEET:
                lmb = lambda apih: apih.api.getFinancials_balance(symbol, ftype)
            elif stype == FinancialStatementType.CASH_FLOW:
                lmb = lambda apih: apih.api.getFinancials_cashflow(symbol, ftype)

        return self._executeRequestWrapper(api, lmb)

    ## polygon only
    def getStockSplits(self, api:Api=Api.POLYGON, **kwargs):
        if api != Api.POLYGON: raise NotSupportedYet
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

    def getTickers(self, api:Api,  
                   onlyPage=None, limit=None, ## debugging/throttling
                   verbose=0, **kwargs):
        '''Query all ticker symbols which are supported by the given API'''

        if api not in [Api.POLYGON, Api.ALPHAVANTAGE, Api.YAHOO]: raise NotSupportedYet()

        apiHandle = self.apis[api]

        pageIndex = 1
        tickers = []
        resp = self.__executeAPIRequest(apiHandle, lambda: apiHandle.api.getTickers(verbose=verbose, **kwargs), verbose=verbose)

        if api == Api.ALPHAVANTAGE:
            return resp
        elif api == Api.POLYGON:
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

    def getTickerDetails(self, api:Api, ticker, verbose=0, **kwargs):
        '''additional kwargs: exchange, asOfDate'''
        return self._executeRequestWrapper(
            api,
            lambda apih: apih.api.getTickerDetails(ticker, verbose=verbose, **kwargs),
            verbose=verbose
        )

def getPolygonSymbols():
    from utils import convertListToCSV

    apim = APIManager()
    tickers = apim.getTickers(Api.POLYGON)
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

import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import requests
from requests.models import Response

from constants.exceptions import APIError, APITimeout
from constants.enums import FinancialReportType, MarketType, OperatorDict, TimespanType
from utils.support import asISOFormat, recdotdict, shortcdict

# import codecs
# w=codecs.getwriter("utf-8")(sys.stdout.buffer)

class Polygon:
    def __init__(self, url, key, **kwargs):
        self.url = url
        self.apiKey = key

    def getNextURL(self, url):
        '''get next page of results from an API call'''
        return self.__responseHandler(requests.get(url, params={
            'apiKey': self.apiKey
        }))

    #region getTickers object
    '''
    "active": true,
    "cik": "0001090872",
    "composite_figi": "BBG000BWQYZ5",
    "currency_name": "usd",
    "last_updated_utc": "2021-04-25T00:00:00Z",
    "locale": "us",
    "market": "stocks",
    "name": "Agilent Technologies Inc.",
    "primary_exchange": "XNYS",
    "share_class_figi": "BBG001SCTQY4",
    "ticker": "A",
    "type": "CS"
    '''
    #endregion
    def getTickers(self, ticker=None, market:MarketType=MarketType.STOCKS, cik=None, active=None, verbose=0):
        '''https://polygon.io/docs/stocks/get_v3_reference_tickers'''

        params = {
            'apiKey': self.apiKey,
            'sort': 'ticker',
            'limit': 1000
        }
        if ticker is not None: params['ticker'] = ticker
        if market is not None: params['market'] = market.value.lower()
        if cik is not None: params['cik'] = cik
        if active is not None: params['active'] = active

        return self.__responseHandler(
            requests.get(f'{self.url}/v3/reference/tickers', params=params),
            verbose=verbose
        )

    #region getTickerDetails object
    '''
    "ticker": "A",
    "name": "Agilent Technologies Inc.",
    "market": "stocks",
    "locale": "us",
    "primary_exchange": "XNYS",
    "type": "CS",
    "active": true,
    "currency_name": "usd",
    "cik": "0001090872",
    "composite_figi": "BBG000C2V3D6",
    "share_class_figi": "BBG001SCTQY4",
    "market_cap": 40967833541.64,
    "phone_number": "(408) 345-8886",
    "address": {
        "address1": "5301 STEVENS CREEK BLVD",
        "city": "SANTA CLARA",
        "state": "CA",
        "postal_code": "95051"
    },
    "description": "Originally spun out of Hewlett-Packard in 1999, Agilent has evolved into a leading life sciences and diagnostics firm. Today, Agilent's measurement technologies serve a broad base of customers with its three operating segments: life science and applied tools, cross lab (consisting of consumables and services related to life science and applied tools), and diagnostics and genomics. Over half of its sales are generated from the biopharmaceutical, chemical, and advanced materials end markets, but it also supports clinical lab, environmental, forensics, food, academic, and government-related organizations. The company is geographically diverse, with operations in the U.S. and China representing the largest country concentrations.",
    "sic_code": "3826",
    "sic_description": "LABORATORY ANALYTICAL INSTRUMENTS",
    "ticker_root": "A",
    "homepage_url": "https://www.agilent.com",
    "total_employees": 18100,
    "list_date": "1999-11-18",
    "branding": {
        "logo_url": "https://api.polygon.io/v1/reference/company-branding/YWdpbGVudC5jb20/images/2023-12-27_logo.svg",
        "icon_url": "https://api.polygon.io/v1/reference/company-branding/YWdpbGVudC5jb20/images/2023-12-27_icon.jpeg"
    },
    "share_class_shares_outstanding": 293000000,
    "weighted_shares_outstanding": 293004102,
    "round_lot": 100
    '''
    #endregion
    def getTickerDetails(self, ticker: str, asOfDate=None, verbose=0):
        '''https://polygon.io/docs/stocks/get_v3_reference_tickers__ticker'''

        params = { 'apiKey': self.apiKey }
        if asOfDate: params['date'] = asISOFormat(asOfDate)

        return self.__responseHandler(
            requests.get(f'{self.url}/v3/reference/tickers/{ticker}', params=params),
            verbose=verbose
        )['results']

# {
#    "T": "PSTG",
#    "v": 4622480,
#    "vw": 18.2159,
#    "o": 18.5,
#    "c": 18.22,
#    "h": 18.57,
#    "l": 17.89,
#    "t": 1602705600000,
#    "n": 31444

    def query(self, date, verbose=0):
        rjson = self.__responseHandler(
            requests.get(self.url + '/v2/aggs/grouped/locale/us/market/stocks/' + asISOFormat(date), params={
                'apikey': self.apiKey,
                'unadjusted': True
            }),
            verbose
        )

        data = rjson['results'] if rjson['resultsCount'] > 0 else []

        # if len(data) > 0 and data[0]['t']

        for d in range(len(data)):
            data[d] = {
                'ticker': data[d]['T'],
                'open': data[d]['o'],
                'high': data[d]['h'],
                'low': data[d]['l'],
                'close': data[d]['c'],
                'volume': data[d]['v'],
                'transactions': shortcdict(data[d], 'n', 0)
            }

        if verbose == 1: print(rjson['resultsCount'],'data points retrieved')
        return data

    def getNonMarketHoursStockData(self, ticker, dt, verbose=0):
        rjson = self.__responseHandler(
            requests.get(self.url + f'/v1/open-close/{ticker}/{asISOFormat(dt)}', params={
                'apikey': self.apiKey,
                'unadjusted': True
            }),
            verbose
        )
        return recdotdict(rjson)


    def getAggregates(self, symbol: str, multipler: int, timespan: TimespanType, fromDate, toDate, limit, verbose=0):
        rjson = self.__responseHandler(
            requests.get(
                # self.url + '/v2/aggs/ticker/' + symbol.upper() + '/range/' + multipler + '/' + timespan.value + '/' + fromDate + '/' + toDate
                '{url}/v2/aggs/ticker/{symbol}/range/{multipler}/{timespan}/{fromDate}/{toDate}'.format(
                    url=self.url, symbol=symbol.upper(), multipler=multipler, timespan=timespan.value.lower(), fromDate=fromDate, toDate=toDate
                ), params={
                'apikey': self.apiKey,
                'adjusted': False,
                'sort': 'asc',
                'limit': limit ## one day is ~900
            }),
            verbose
        )

        data = rjson['results'] if rjson['resultsCount'] > 0 else []

        for d in range(len(data)):
            tempvar = data[d]
            data[d] = {
                'open': data[d]['o'],
                'high': data[d]['h'],
                'low': data[d]['l'],
                'close': data[d]['c'],
                'volumeWeightedAverage': shortcdict(data[d], 'vw', 0, False),
                'volume': data[d]['v'],
                'transactions': shortcdict(data[d], 'n', 0, False),
                'unixTimePeriod': data[d]['t']
            }

        if verbose == 1: print(rjson['resultsCount'],'data points retrieved')
        if rjson['resultsCount'] == 50000: raise OverflowError ## API limit is 50000, we may have gotten partial or entirely missed days
        return data

    def __responseHandler(self, resp: Response, verbose=0):
        if verbose: print('made request', resp.url)

        if resp.ok:
            rjson = resp.json()

            ## some error in response, is either message or date out of allowed range
            if 'error' in rjson.keys():
                print('APIError', resp, rjson)
                raise APIError
            elif len(rjson.keys()) == 1:
                print('APIError', resp, rjson)
                raise APIError
                # raise APITimeout

            if verbose == 2: print('got response', rjson)
            return rjson

        elif resp.status_code == 429:
            raise APITimeout
        else:
            print('APIError' ,resp)
            raise APIError

    def getFinancials(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url + '/v2/reference/financials/' + symbol, params={
                'apikey': self.apiKey,
                'type': ftype.polygon
            })
        )

    def getStockSplits(self, symbol=None, endSymbol=None, symbolOperator:OperatorDict=None, endSymbolOperator:OperatorDict=None, date=None, endDate=None, dateOperator:OperatorDict=None, endDateOperator:OperatorDict=None):
        params = {
            'apikey': self.apiKey,
            'limit': 1000,
            'sort': 'execution_date'
        }
        if symbol:
            params['ticker{}'.format('' if not symbolOperator else '.'+symbolOperator.polygonsymbol)] = symbol
        if endSymbol:
            params['ticker{}'.format('' if not endSymbolOperator else '.'+endSymbolOperator.polygonsymbol)] = endSymbol
        if date:
            params['execution_date{}'.format('' if not dateOperator else '.'+dateOperator.polygonsymbol)] = date
        if endDate:
            params['execution_date{}'.format('' if not endDateOperator else '.'+endDateOperator.polygonsymbol)] = endDate

        return self.__responseHandler(
            requests.get(self.url + '/v3/reference/splits', params=params), 
            verbose=1
        )['results']
        '''
        [{
        "execution_date": "2022-09-14",
        "split_from": 1,
        "split_to": 3,
        "ticker": "PANW"
        }]
        '''
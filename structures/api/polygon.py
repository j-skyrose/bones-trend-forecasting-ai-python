from constants.enums import FinancialReportType
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

# import codecs
# w=codecs.getwriter("utf-8")(sys.stdout.buffer)

class Polygon:
    def __init__(self, url, key):
        self.url = url
        self.apiKey = key

    def getSupportedTickers(self, page=1):
        resp = requests.get(self.url + '/v2/reference/tickers', params={
            'sort': 'ticker',
            'page': page,
            'apiKey': self.apiKey,
            'active': 'true'
        })
        rjson = resp.json()

        if resp.ok:
            print('got response')
            try:
                print (resp, rjson)
            except Exception:
                print('error while printing')
            data = rjson['tickers']

            print(len(data),'symbols points retrieved')

            return data
        else:
            print('APIError' ,resp)
            raise APIError


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

    def query(self, date):
        rjson = self.__responseHandler(
            requests.get(self.url + '/v2/aggs/grouped/locale/us/market/stocks/' + date, params={
                'apikey': self.apiKey,
                'unadjusted': True
            })
        )

        data = rjson['results'] if rjson['resultsCount'] > 0 else []

        # if len(data) > 0 and data[0]['t']

        for d in range(len(data)):
            data[d] = {
                'symbol': data[d]['T'],
                'open': data[d]['o'],
                'high': data[d]['h'],
                'low': data[d]['l'],
                'close': data[d]['c'],
                'volume': data[d]['v']
            }

        print(rjson['resultsCount'],'data points retrieved')
        return data

    def __responseHandler(self, resp: Response):
        print('made request', resp.url)

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

            print('got response', rjson)
            return rjson

        elif resp.status_code == 429:
            raise APITimeout
        else:
            print('APIError' ,resp)
            raise APIError

    def getTickerDetails(self, symbol):
        return self.__responseHandler(
            requests.get(self.url + '/v1/meta/symbols/' + symbol + '/company', params={
                'apikey': self.apiKey
            })
        )

    def getFinancials(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url + '/v2/reference/financials/' + symbol, params={
                'apikey': self.apiKey,
                'type': ftype.polygon
            })
        )
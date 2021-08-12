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
from constants.exceptions import APIError, APILimitReached, APITimeout
import json

## financial modeling prep
class FMP:
    def __init__(self, url, key):
        self.url = url
        self.apiKey = key

    def __responseHandler(self, resp: Response):
        print('made request', resp.url)
        print(resp)
        print(resp.json())

        if resp.ok:
            try:
                rjson = resp.json()[0]
            except IndexError:
                raise APIError


            ## some error in response, is either message or date out of allowed range
            if 'error' in rjson.keys():
                print('APIError', resp, rjson)
                raise APIError
            elif len(rjson.keys()) == 1:
                print('APIError', resp, rjson)
                raise APIError
                # raise APITimeout

            print('got response', rjson.keys())
            return rjson

        elif resp.status_code == 403:
            raise APILimitReached
        else:
            print('APIError' ,resp)
            raise APIError

    def getTickerDetails(self, symbol):
        return self.__responseHandler(
            requests.get(self.url + '/profile/' + symbol, params={
                'apikey': self.apiKey
            })
        )

    def getFinancials_income(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url + '/income-statement/' + symbol, params={
                'apikey': self.apiKey,
                'period': ftype.fmp,
                'limit': 400
            })
        )

    def getFinancials_balance(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url + '/balance-sheet-statement/' + symbol, params={
                'apikey': self.apiKey,
                'period': ftype.fmp
            })
        )

    def getFinancials_cashflow(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url + '/cash-flow-statement/' + symbol, params={
                'apikey': self.apiKey,
                'period': ftype.fmp
            })
        )

    ## todo
    def query(self, type, symbol):
        print('making request', self.url, self.apiKey, type.function, symbol)
        resp = requests.get(self.url, params={
            'apikey': self.apiKey,
            'function': type.function,
            'outputsize': 'full',
            'symbol': symbol.replace('.','-')
        })
        try:
            rjson = resp.json()

            if resp.ok:
                ## some error in response, is either message or query limit reached so no data given
                if 'Error Message' in rjson.keys() or len(rjson.keys()) == 0:
                    print('APIError', resp, rjson)
                    raise APIError
                elif len(rjson.keys()) == 1: raise APITimeout


                print('got response', rjson.keys())
                data = rjson[type.description]
                for d in data.keys():
                    data[d] = {
                        'open': data[d]['1. open'],
                        'high': data[d]['2. high'],
                        'low': data[d]['3. low'],
                        'close': data[d]['4. close'],
                        'volume': data[d]['5. volume']
                    }

                print(len(data.keys()),'data points retrieved')

                return data
            else:
                print('APIError' ,resp)
                raise APIError
        except json.decoder.JSONDecodeError:

            raise APIError

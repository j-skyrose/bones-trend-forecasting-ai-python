from constants.enums import FinancialReportType, FinancialStatementType
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import requests
# from requests.json.decoder import JSONDecodeError
import json

from requests.models import Response
from constants.exceptions import APIError, APITimeout

class Alphavantage:
    def __init__(self, url, key):
        self.url = url
        self.apiKey = key

    def __formatSymbol(self, symbol):
        return symbol.replace('.','-')

    def __responseHandler(self, resp: Response):
        try:
            print('made request', resp.url)
            rjson = resp.json()

            if resp.ok:
                ## some error in response, is either message or query limit reached so no data given
                if 'Error Message' in rjson.keys() or len(rjson.keys()) == 0:
                    print('APIError', resp, rjson)
                    raise APIError
                elif len(rjson.keys()) == 1: raise APITimeout

                print('got response', rjson)

                return rjson
            else:
                print('APIError' ,resp)
                raise APIError

        # except json.decoder.JSONDecodeError:
        except APITimeout:
            raise APITimeout
        except:
            print(resp)
            print(resp.json())
            raise APIError

    def getTickerDetails(self, symbol):
        return self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': 'OVERVIEW',
                'symbol': self.__formatSymbol(symbol)
            })
        )

    def getFinancials_income(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': FinancialStatementType.INCOME.value,
                'symbol': self.__formatSymbol(symbol)
            })
        )

    def getFinancials_balance(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': FinancialStatementType.BALANCE_SHEET.value,
                'symbol': self.__formatSymbol(symbol)
            })
        )

    def getFinancials_cashflow(self, symbol, ftype: FinancialReportType):
        return self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': FinancialStatementType.CASH_FLOW.value,
                'symbol': self.__formatSymbol(symbol)
            })
        )


    def query(self, type, symbol):
        rjson = self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': type.function,
                'outputsize': 'full',
                'symbol': self.__formatSymbol(symbol)
            })
        )
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

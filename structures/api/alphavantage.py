import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import requests, csv
from datetime import date
from requests.models import Response

from constants.enums import FinancialReportType, FinancialStatementType
from constants.exceptions import APIError, APITimeout
from structures.api.apiBase import APIBase
from utils.support import Singleton, asISOFormat, recdotobj, shortc

class Alphavantage(APIBase, Singleton):

    def __buildExchangeSnippet(self, exchange):
        if not exchange or exchange in ['NYSE', 'NYSE ARCA', 'NASDAQ', 'NYSE MKT', 'BATS']:
            return ''
        return exchange + ':'

    def __formatSymbol(self, exchange, symbol):
        return self.__buildExchangeSnippet(exchange) + symbol.replace('.','-')

    def __responseHandler(self, resp: Response, responseType='json', verbose=0):
        try:
            if verbose: print('made request', resp.url)
            if resp.ok:
                if responseType == 'csv':
                    try: rjson = resp.json()
                    except:
                        ## dummy keys to not trigger error/timeout checking
                        rjson = {'csv': True, 'not a timeout': True}
                else:
                    rjson = resp.json()
                ## some error in response, is either message or query limit reached so no data given
                if 'Error Message' in rjson.keys() or len(rjson.keys()) == 0:
                    print('APIError', resp, rjson)
                    raise APIError
                elif len(rjson.keys()) == 1: raise APITimeout

                if responseType == 'csv':
                    if verbose: print('got csv response', str(resp.text[:200]), '...')
                    return recdotobj(list(csv.DictReader(resp.text.split('\r\n'))))
                else:
                    if verbose: print('got response', str(rjson)[:500], '...')
                    return rjson
            else:
                print('APIError' ,resp)
                raise APIError

        # except json.decoder.JSONDecodeError:
        except APITimeout:
            raise APITimeout
        except:
            print(resp)
            try:    print(resp.json())
            except: pass
            raise APIError

    def getTickers(self, active=True, dt=None, verbose=0, **kwargs):
        return self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': 'LISTING_STATUS',
                'state': 'active' if active else 'delisted',
                'date': asISOFormat(shortc(dt, date.today()))
            }),
            responseType='csv',
            verbose=verbose
        )

    def getTickerDetails(self, symbol, exchange=None, verbose=0, **kwargs):
        return self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': 'OVERVIEW',
                'symbol': self.__formatSymbol(exchange, symbol)
            }),
            verbose=verbose
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


    def query(self, type, symbol, exchange, compact=False, verbose=1):
        rjson = self.__responseHandler(
            requests.get(self.url, params={
                'apikey': self.apiKey,
                'function': type.function,
                'outputsize': 'compact' if compact else 'full', ## compact only returns latest 100 data points
                'symbol': self.__formatSymbol(exchange, symbol)
            }),
            verbose=verbose
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

        if verbose: print(len(data.keys()),'data points retrieved')
        return data

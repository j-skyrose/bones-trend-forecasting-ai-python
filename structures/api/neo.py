import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import requests, json
from requests.models import Response
from datetime import date, datetime

from constants.exceptions import APIError, APITimeout
from utils.support import recdotobj, shortcdict

class NEO:
    def __init__(self, url):
        self.url = url

    def __responseHandler(self, resp: Response, verbose=0):
        try:
            if verbose > 0: print('made request', resp.url)

            if resp.ok:
                rjson = resp.json()
                ## some error in response, is either message or query limit reached so no data given
                # if 'Error Message' in rjson.keys() or len(rjson.keys()) == 0:
                if shortcdict(rjson, 'errorMessage', False):
                    print('APIError', resp, rjson)
                    raise APIError
                elif len(rjson.keys()) == 1: raise APITimeout

                if verbose==1: print('got response', rjson)

                return rjson
            else:
                print('APIError' ,resp)
                raise APIError

        # except json.decoder.JSONDecodeError:
        except APITimeout:
            raise APITimeout
        except Exception as e:
            print('exception', e)
            print(resp)
            try: print(resp.json())
            except: pass
            raise APIError
        
    def getTickerDump(self):
        rjson = self.__responseHandler(
            requests.post(self.url + '/securities/search', json={
                "itemsPerPage": 5400,
                "listingMarket": "NEO"
            })
        )
        
        if rjson['totalItems'] > rjson['itemsPerPage']: raise OverflowError

        print(len(rjson['payload']['items']),'tickers retrieved')
        return recdotobj(rjson['payload']['items'])
            # {
            #     "symbol": "ZZZD",
            #     "securityName": "BMO TATICAL DIVIDEND ETF FUND",
            #     "listingMarket": "TSX",
            #     "securityType": "EQUITY",
            #     "status": "TRADING"
            # }

    def query(self, symbol, fromDate, toDate, verbose=0):
        rjson = self.__responseHandler(
            requests.get(self.url + '/historical_data/' + symbol, params={
                'startDate': fromDate,
                'endDate': toDate
            }),
            verbose
        )
        data = {}
        for d in rjson['payload']:
            data[datetime.utcfromtimestamp(d['date']/1000).date().isoformat()] = d

        if verbose > 0: print(len(data.keys()),'data points retrieved')
        return data

# {
#     "errorMessage": null,
#     "payload": [
#         {
#             "date": 1648785600000,
#             "open": 20.22,
#             "high": 20.34,
#             "low": 20.08,
#             "close": 20.29,
#             "volume": 18299,
#             "value": 370896.28,
#             "trades": 147
#         },
#         {
#             "date": 1649044800000,
#             "open": 20.31,
#             "high": 20.58,
#             "low": 20.15,
#             "close": 20.5,
#             "volume": 24246,
#             "value": 495898.83,
#             "trades": 172
#         },
#     ],
#     "totalItems": 0,
#     "itemsPerPage": 0,
#     "currentPage": 0,
#     "totalPages": 1
# }
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time, requests
from datetime import date, timedelta

from structures.api.apiBase import APIBase
from utils.support import Singleton, asDate

class Yahoo(APIBase, Singleton):
    crumb = '.q4CENIZwE0'
    cookieVal = 'tbla_id=dc872ff0-fa13-4bfa-ad64-58cdde23074d-tuct46e322a; gam_id=y-4JzSOCFE2uL7mC5RBvYGpMj7wFuX9yQ4~A; B=acmlpj5bp8geh&b=3&s=i3; A1=d=AQABBEelL14CEDgSd0gnSdFw7CcuPjJjlGUFEgEBCAF-f2SyZCUHb2UB_eMBAAcI0UGUV5m5WqY&S=AQAAAgjoVDd4LgrNte4LrI8-eac; A3=d=AQABBEelL14CEDgSd0gnSdFw7CcuPjJjlGUFEgEBCAF-f2SyZCUHb2UB_eMBAAcI0UGUV5m5WqY&S=AQAAAgjoVDd4LgrNte4LrI8-eac; GUC=AQEBCAFkf35kskIi-wTr; A1S=d=AQABBEelL14CEDgSd0gnSdFw7CcuPjJjlGUFEgEBCAF-f2SyZCUHb2UB_eMBAAcI0UGUV5m5WqY&S=AQAAAgjoVDd4LgrNte4LrI8-eac&j=WORLD; PRF=t%3DMODD%252BHYREQ%252BFLES%252BCUK%252BCCL%252BAUMBF%252BMSTR%252BSAIC%252BBBLG%252BGME%252BSPY%252BCHACU%26newChartbetateaser%3D1; cmp=t=1688440827&j=0&u=1---'
    pageSize = 100

    def _standardParamObj(self, withCrumb=True, lang='en-US', region='US', corsDomain='finance.yahoo.com'):
        return {
                'crumb': self.crumb,
                'lang': lang,
                'region': region,
                'corsDomain': corsDomain
            }
    
    def _standardHeadersObj(self):
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
        }

    def _request(self, reqLambda, verbose=0):
        for retryloop in range(3):
            resp = reqLambda()
            if resp.status_code == 404 or resp.status_code == 503: ## both seem to be a back-off response
                if verbose: print('sleeping', retryloop)
                time.sleep(60*(retryloop+1))
            else: break
        return resp

    def getSymbol(self, symbol, region='US', verbose=1):
        resp = self._request(lambda: requests.get(
            self.url + f'/v1/finance/quoteType/{symbol}',
            params=self._standardParamObj(withCrumb=False, region=region),
            headers=self._standardHeadersObj()
        ))
        rjson = resp.json()
        if resp.ok:
            result = rjson['quoteType']['result']
            if len(result) > 1: raise ValueError('too many results')
            elif len(result) == 0: return []
            else: return result[0]

    def getEarningsDates(self, dt=None, verbose=1, **kwargs):
        dt = asDate(dt)
        totalRows = None
        offset = 0
        retds = []
        pageSize = self.pageSize
        while totalRows is None or len(retds) < totalRows:
            for pageSizeReductionLoop in range(2):
                resp = self._request(lambda: self._requestEarningsDates(dt, offset), verbose)
                if not resp.ok and resp.status_code == 500:
                    # response data would be too large (>16GB)
                    pageSize = int(pageSize/2)
                    if verbose: print('Data too large, reducing page size')
                    continue
                rjson = resp.json()
                totalRows = rjson['finance']['result'][0]['total']
                docsObj = rjson['finance']['result'][0]['documents'][0]

                retds.extend(self._buildRowsObjs(docsObj['columns'], docsObj['rows']))
                offset += pageSize
                if verbose: print(f'Got {len(retds)}/{totalRows} rows')
                break

        for rd in retds:
            rd['date'] = dt.isoformat()

        return retds

    def _buildRowsObjs(self, cols, rows):
        keys = [c['id'] for c in cols]
        return [{ k: r[indx] for indx,k in enumerate(keys) } for r in rows]

    def _requestEarningsDates(self, dt: date, offset=0):
        reqObj = {
            "sortType": "ASC",
            "entityIdType": "earnings",
            "sortField": "companyshortname",
            "includeFields": [
                "ticker",
                "companyshortname",
                "eventname",
                "startdatetime",
                "startdatetimetype",
                "epsestimate",
                "epsactual",
                "epssurprisepct",
                "timeZoneShortName",
                "gmtOffsetMilliSeconds"
            ],
            "query": {
                "operator": "and",
                "operands": [
                    {
                        "operator": "gte",
                        "operands": [
                            "startdatetime",
                            dt.isoformat()
                        ]
                    },
                    {
                        "operator": "lt",
                        "operands": [
                            "startdatetime",
                            (dt + timedelta(days=1)).isoformat()
                        ]
                    },
                    {
                        "operator": "eq",
                        "operands": [
                            "region",
                            "us"
                        ]
                    }
                ]
            },
            "offset": offset,
            "size": self.pageSize
        }

        headers = self._standardHeadersObj()
        if self.cookieVal: headers['cookie'] = self.cookieVal

        resp = requests.post(self.url + '/v1/finance/visualization', params=self._standardParamObj(), json=reqObj, headers=headers)

        print(f'requested {dt.isoformat()}', resp.url)
        print(resp)

        return resp

if __name__ == '__main__':
    y = Yahoo()
    res = y.getEarningsDates(date(2020, 10, 29))
    print(res)

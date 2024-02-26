import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import requests
from datetime import date
from requests.models import Response

from constants.exceptions import APIError
from structures.api.apiBase import APIBase
from utils.support import Singleton, asDate, shortc

class Nasdaq(APIBase, Singleton):
    ## at least 'earnings' call will not work without a user-agent header
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    }

    def __responseHandler(self, resp: Response):
        print('made request', resp.url)
        print(resp)

        if resp.ok:
            try:
                rjson = resp.json()
                print('got response', str(rjson)[:600], '...')
            except IndexError:
                raise APIError

            if rjson['status']['rCode'] != 200:
                print('APIError', resp, rjson)
                raise APIError

            print('response keys', rjson.keys())
            return rjson

        else:
            print('APIError' ,resp)
            raise APIError

    
    def getEarningsDates(self, dt: date, **_):
        ## pre-date response
        # {'time': 'Time', 'symbol': 'Symbol', 'name': 'Company Name', 'marketCap': 'Market Cap', 'fiscalQuarterEnding': 'Fiscal Quarter Ending', 'epsForecast': 'Consensus EPS* Forecast', 'noOfEsts': '# of Ests', 'lastYearRptDt': "Last Year's Report Date", 'lastYearEPS': "Last year's EPS*"}
        # {'lastYearRptDt': '6/30/2022', 'lastYearEPS': '$2.66', 'time': 'time-pre-market', 'symbol': 'STZ', 'name': 'Constellation Brands Inc', 'marketCap': '$44,411,764,403', 'fiscalQuarterEnding': 'May/2023', 'epsForecast': '$2.82', 'noOfEsts': '9'}
        # {'lastYearRptDt': 'N/A', 'lastYearEPS': '$0.07', 'time': 'time-not-supplied', 'symbol': 'AAME', 'name': 'Atlantic American Corporation', 'marketCap': '$43,789,542', 'fiscalQuarterEnding': 'Mar/2023', 'epsForecast': '', 'noOfEsts': '11'}
        
        ## post-date response
        # {'time': 'Time', 'symbol': 'Symbol', 'name': 'Company Name', 'eps': 'EPS', 'surprise': '% Surprise', 'marketCap': 'Market Cap', 'fiscalQuarterEnding': 'Fiscal Quarter Ending', 'epsForecast': 'Consensus EPS* Forecast', 'noOfEsts': '# of Ests'}
        # {'eps': '$1.15', 'surprise': '8.49', 'time': 'time-not-supplied', 'symbol': 'CRM', 'name': 'Salesforce, Inc.', 'marketCap': '$204,627,660,000', 'fiscalQuarterEnding': 'Apr/2023', 'epsForecast': '$1.06', 'noOfEsts': '16'}

        resp = self.__responseHandler(
            requests.get(self.url + '/calendar/earnings', params={
                'date': dt.isoformat()
            }, headers=self.headers)
        )
        if resp['data']:
            ## rows can be null, typically for weekends
            return shortc(resp['data']['rows'], [])
        else: # no data/records, typically for future dates
            return []

if __name__ == '__main__':
    nd: Nasdaq = Nasdaq()
    res = nd.getEarningsDates(asDate('2023-07-02'))
    print(res)
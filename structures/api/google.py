import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time, json, re
import requests
from requests.models import Response
from datetime import date, datetime
from typing import Dict, List, Union

from constants.exceptions import APIError, APITimeout

DEBUG = False

## builds query string to exactly match how it appears from browser
## alone, did not help convince backend this was not a SCRAPER
def buildQueryString(params):
    q = '?'
    ps = []
    ps.append('hl=' + params['hl'])
    ps.append('tz=' + str(params['tz']))
    
    reqstring = json.dumps(params['req']).replace('"', '%22').replace('{', '%7B').replace('}', '%7D').replace('[', '%5B').replace(']', '%5D').replace('/', '%2F')
    reqstring = re.sub(r'([0-9]{4}-[0-9]{2}-[0-9]{2}) ', r'\1+', reqstring)
    ps.append('req=' + reqstring.replace(' ', ''))

    if 'token' in params.keys():
        ps.append('token=' + params['token'])

    ps.append('tz=' + str(params['tz']))
    return q + '&'.join(ps)

class Google:
    url = 'https://trends.google.com/trends/api'
    cookieVal = None
    hl = 'en-GB'
    ## utc offset in minutes
    timezone = int(time.timezone/60 - (60 * time.localtime().tm_isdst))

    def _request(self, url, reqObj, token=None, retry=True):
        params = {
            'hl': self.hl,
            'tz': self.timezone,
            'req': json.dumps(reqObj) ## OG
            # 'req' : reqObj ## alt
        }
        if token: params['token'] = token

        # headers = {
        #     'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
        # }
        headers = {}
        if self.cookieVal: headers['cookie'] = self.cookieVal

        resp = requests.get(url, params, headers=headers) ## OG
        # resp = requests.get(url + buildQueryString(params), headers=headers) ## alt

        print('requested', resp.url)
        print(resp)
        if DEBUG: print(resp.text)
        if resp.status_code == 429:
            if 'set-cookie' not in resp.headers.keys(): raise APITimeout
            ## Fix for the "too many requests" issue
            ## Look for the set-cookie header and re-request
            self.cookieVal = resp.headers['set-cookie'].split(';')[0]
            resp = self._request(url, reqObj)
        ## "Internal Server Error"
        elif resp.status_code == 500 and retry:
            resp = self._request(url, reqObj, retry=False)

        return resp

    def __responseHandler(self, resp: Response):
        trim_chars = 4 if 'explore' in resp.url else 5

        if resp.ok:
            try:
                rjson = json.loads(resp.text[trim_chars:])
            except IndexError:
                raise APIError

            if DEBUG: print(rjson)
            return rjson
        else:
            print('APIError', resp)
            raise APIError(resp.status_code)


    def _buildReqObj(self, keyword, start, end):
        return {
            'comparisonItem':[{
                'keyword':keyword,
                'geo':'',
                'time':f'{start.isoformat()} {end.isoformat()}'
            }],
            'category':0,
            'property':'',
        }

    def _enhanceReqObj(self, original, resultObj):
        newReq = resultObj['request']
        newReq['requestOptions']['category'] = original['category']
        newReq['requestOptions']['property'] = original['property']
        return newReq

    def getHistoricalInterests(self, keyword, start=date(2004,1,1), end=date.today()) -> List[Dict[str, Union[date,int]]]:
        '''Data is based on random sampling of searches, highly likely to be inconsistent between scraping and the actual webpage, especially for low search volumes'''
        
        ## rearrange dates if necessary
        if start > end:
            temp = end
            end = start
            start = temp

        ## get token and req object from explore API; setup cookie
        reqObj = self._buildReqObj(keyword, start, end)
        resp = self.__responseHandler(self._request(self.url + '/explore', reqObj))
        resultObj = list(filter(lambda a: a['id'] == 'TIMESERIES', resp['widgets']))[0]

        ## get actual historical interests data
        resp = self.__responseHandler(self._request(self.url + '/widgetdata/multiline', self._enhanceReqObj(reqObj, resultObj), resultObj['token']))

        ## massage data
        returndata = []
        for d in resp['default']['timelineData']:
            startdate = datetime.fromtimestamp(int(d['time']) + (self.timezone + 60) * 60).date().isoformat() ## offset +1h to account for DST, no need to have it land exactly at midnight
            try:
                enddate = datetime.strptime(d['formattedTime'].split('-')[1], '%d %b %Y').date()
            except IndexError:
                enddate = None
            
            value = d['value'][0]
            if value == 0 and d['hasData'][0]:
                value = 0.1
            
            # if startdate == '2021-11-07':
            #     print(d)

            returndata.append({
                'startDate': startdate,
                'endDate': enddate,
                'relative_interest': d['value'][0]
            })
        print(f'Got {len(returndata)} data points')

        return returndata
            


if __name__ == '__main__':
    g = Google()
    print(g.getHistoricalInterests('/g/11b7jf24rq', date(2022,1,1)))


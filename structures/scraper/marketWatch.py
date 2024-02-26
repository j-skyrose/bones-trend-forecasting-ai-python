import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time, requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta

from structures.api.apiBase import APIBase
from utils.support import Singleton, asDate, recdotdict, recdotobj, shortc, toUSAFormat

DEBUG = False

class MarketWatch(APIBase, Singleton):
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    ## utc offset in minutes
    timezone = int(time.timezone/60 - (60 * time.localtime().tm_isdst))

    def _standardHeadersObj(self, userAgent=None):
        return {
            'User-Agent': shortc(userAgent, self.userAgent)
        }

    def _earningsDatesRequest(self, dt, partial=True, mockDataDebugging=False, verbose=1, **_):
        if not mockDataDebugging:
            dt = asDate(dt)
            requestedDate = datetime(dt.year, dt.month, dt.day, 4)
            params = {
                'requestedDate': requestedDate.isoformat(),
                'partial': partial
            }

            resp = requests.get(f'{self.url}/earnings-calendar', params, headers=self._standardHeadersObj())
            if verbose:
                print('requested', resp.url)
                print(resp)
            return resp
        else:
            dt = date(2023, 6, 26)
            with open(os.path.join(path, 'miscellaneous', 'market-watch-earnings-html-example.html'), 'rb') as f:
                return recdotdict({
                    'url': self.url + 'DEBUG',
                    'content': f.read()
                })

    def _parseEarningsDatesResponse(self, resp, week=False):
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        startDate = datetime.strptime(soup.find('input', id='requested-Date')['value'], '%m/%d/%Y %X').date()

        data = []
        for d in range(7 if week else 1): ## will always get week data, but optionally only extract the requested day's data
            tabdt = startDate + timedelta(days=d)
            curdtelement = soup.find('div', attrs={'data-tab-pane': toUSAFormat(tabdt, separator='/')})
            if not curdtelement: continue ## date element not present
            curdtdata = curdtelement.find('tbody')
            if not curdtdata: continue ## "Sorry, this date currently does not have any earnings announcements scheduled"
            for r in curdtdata.find_all('tr'):
                cols = r.find_all('div', class_='cell__content')
                colvals = [c.text.strip() for c in cols]
                ## company name (fixed--cell), company name, symbol, fiscal quarter, eps forecast, eps actual, surprise
                data.append({
                    'date': tabdt,
                    'name': colvals[1],
                    'symbol': colvals[2],
                    'fiscal quarter': colvals[3],
                    'epsForecast': colvals[4],
                    'eps': colvals[5],
                    'surprise_percentage': colvals[6]
                })

        return recdotobj(data)

    def getEarningsDates(self, dt=None, week=False, verbose=1, **kwargs):
        response = self._earningsDatesRequest(dt, verbose=verbose, **kwargs)
        parsedData = self._parseEarningsDatesResponse(response, week=week)

        return parsedData

if __name__ == '__main__':
    mw = MarketWatch()
    # mw._request(date(2023, 7, 10))
    # mw.getEarningsDates(mockDataDebugging=True)
    # mw.getEarningsDates('2023-07-19')
    # print(res)

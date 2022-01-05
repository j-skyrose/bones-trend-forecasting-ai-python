import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import calendar
from typing import List
from datetime import date, datetime, timedelta

from globalConfig import config as gconfig
from utils.support import Singleton

class MarketDayManager(Singleton):
    marketHoliays: dict = {}
    marketHalfDays: dict = {}
    marketDays: dict = {}

    @classmethod
    def getMarketHolidays(cls, yr):
        self = cls()
        yr = str(yr)
        if yr not in self.marketHoliays:
            self.marketHoliays[yr] = self._getMarketHolidays(yr)
        return self.marketHoliays[yr]

    @classmethod
    def getMarketHalfdays(cls, yr):
        self = cls()
        yr = str(yr)
        if yr not in self.marketHalfDays:
            self.marketHalfDays[yr] = self._getMarketHalfDays(yr)
        return self.marketHalfDays[yr]

    @classmethod
    def getLastMarketDay(cls, d: date=date.today()) -> date:
        if d.weekday() > 4:
            d = d - timedelta(days=(d.weekday() % 4))
        holidays = cls().getMarketHolidays(d.year)
        while d in holidays:
            d = d - timedelta(days=1)
        return d

    @classmethod
    def getPreviousMarketDay(cls, d: date=date.today() - timedelta(days=1)) -> date:
        return cls().getLastMarketDay(d)

    @classmethod
    def getMarketDays(cls, year=None, startingYear=None, startingFrom: datetime=None) -> List[date]:
        if gconfig.testing.enabled:
            # print('year:', year, 'startingYear:', startingYear, 'startingFrom:', startingFrom)
            pass
        self = cls()
        if year:
            days = self._getMarketDaysForYear(year)
        elif startingYear:
            days = self._getMarketDaysStartingFromYear(year)
        elif startingFrom:
            # return [d for d in self._getMarketDaysStartingFromYear(startingFrom.year) if d >= startingFrom]
            days = self._getMarketDaysStartingFromYear(startingFrom.year)

        return [d.date() for d in days if (True if not startingFrom else d >= startingFrom)]

    def _getMarketDaysForYear(self, year):
        if year not in self.marketDays:
            days = [datetime(year, 1, 1, 23, 59, 59) + timedelta(days=d) for d in range(366 if calendar.isleap(year) else 365)]
            for d in days[:]:
                if d.weekday() > 4 or d in self.getMarketHolidays(year):
                    days.remove(d)
            self.marketDays[str(year)] = days
        return self.marketDays[str(year)]

    def _getMarketDaysStartingFromYear(self, year):
        year = int(year)
        days = []
        for y in range(datetime.now().year - year):
            days.extend(self._getMarketDaysForYear(year + y))
        return days

    def _getMarketHolidays(self, yr):
        holidays = []
        yr = int(yr)

        # new years day
        dt = date(yr, 1, 1)
        if dt.weekday() == 6: dt = dt + timedelta(days=1)
        holidays.append(dt)

        # martin luther king jr day (third monday of jan)
        if yr > 1997:
            mondaycounter = 0
            dt = date(yr-1, 12, 31)
            while mondaycounter < 3:
                dt = dt + timedelta(days=1)
                if dt.weekday() == 0: mondaycounter += 1
            holidays.append(dt)

        # presidents day (third monday of feb)
        mondaycounter = 0
        dt = date(yr, 1, 31)
        while mondaycounter < 3:
            dt = dt + timedelta(days=1)
            if dt.weekday() == 0: mondaycounter += 1
        holidays.append(dt)

        # good Friday
        a = yr % 19
        b = yr // 100
        c = yr % 100
        d = (19 * a + b - b // 4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
        e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
        f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
        month = f // 31
        day = f % 31 + 1
        holidays.append(date(yr, month, day) - timedelta(days=2))

        # memorial day us (last monday of may)
        lastmonday = date(yr, 5, 20)
        dt = lastmonday
        while dt.month == 5:
            if dt.weekday() == 0: lastmonday = dt
            dt = dt + timedelta(days=1)
        holidays.append(lastmonday)

        # independence day (july 4)
        dt = date(yr, 7, 4)
        if dt.weekday() == 5: dt = dt - timedelta(days=1)
        if dt.weekday() == 6: dt = dt + timedelta(days=1)
        holidays.append(dt)

        # labor day (first monday in sept)
        dt = date(yr, 9, 1)
        for i in range(8):
            if dt.weekday() == 0: break
            dt = dt + timedelta(days=1)
        holidays.append(dt)

        holidays.append(self._getThanksgivingDay(yr))
        holidays.append(self._getChristmasDay(yr))

        return holidays

    @staticmethod
    def _getThanksgivingDay(yr):
        # thanksgiving day (us - fourth thursday of nov)
        dt = date(yr, 10, 31)
        thursdaycounter = 0
        while thursdaycounter < 4:
            dt = dt + timedelta(days=1)
            if dt.weekday() == 3: thursdaycounter += 1
        return dt

    @staticmethod
    def _getChristmasDay(yr):
        # christmas day
        dt = date(yr, 12, 25)
        if dt.weekday() == 5: dt = dt - timedelta(days=1)
        if dt.weekday() == 6: dt = dt + timedelta(days=1)
        return dt

    def _getMarketHalfDays(self, yr):
        holidays = []
        yr = int(yr)

        holidays.append(self._getThanksgivingDay(yr) + timedelta(days=1))
        holidays.append(self._getChristmasDay(yr) - timedelta(days=1))

        return holidays



if __name__ == '__main__':
    # print(MarketDayManager.getMarketHolidays(2021))
    # print(MarketDayManager.getMarketHolidays(2021))
    # print(MarketDayManager.getMarketHolidays(2020))
    print(MarketDayManager.getMarketDays(startingFrom=datetime(2019, 12, 2, 8, 0)))
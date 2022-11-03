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
from constants.enums import MarketType
from utils.support import Singleton
from utils.other import getMarketType

class MarketDayManager(Singleton):
    marketHolidays: dict = {MarketType.CANADA_US_SHARED: {}}
    marketHalfDays: dict = {}
    marketDays: dict = {}

    @classmethod
    def getMarketHolidays(cls, yr, exchange='NYSE'):
        self = cls()
        yr = str(yr)

        market = getMarketType(exchange)
        if market not in self.marketHolidays:
            self.marketHolidays[market] = {}

        if yr not in self.marketHolidays[market]:
            self.marketHolidays[market][yr] = self._getMarketHolidays(yr, market)

        if market == MarketType.CANADA or market == MarketType.US:
            if yr not in self.marketHolidays[MarketType.CANADA_US_SHARED]:
                self.marketHolidays[MarketType.CANADA_US_SHARED][yr] = self._getMarketHolidays(yr, MarketType.CANADA_US_SHARED)
            return self.marketHolidays[MarketType.CANADA_US_SHARED][yr] + self.marketHolidays[market][yr]

        return self.marketHolidays[market][yr]

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
        while d in holidays or d.weekday() > 4:
            d = d - timedelta(days=1)
        return d

    @classmethod
    def getPreviousMarketDay(cls, d: date=date.today()) -> date:
        d = d - timedelta(days=1)
        return cls().getLastMarketDay(d)

    @classmethod
    def getMarketDayDiff(cls, fromDate: date, toDate: date) -> int:
        holidays1 = cls().getMarketHolidays(fromDate.year)
        holidays2 = cls().getMarketHolidays(toDate.year)
        if fromDate.weekday() > 4 or toDate.weekday() > 4 or fromDate in holidays1 or toDate in holidays2:
            raise ValueError('One of the dates is not a market day')
        if fromDate == toDate:
            return 0
        
        marketdays = cls().getMarketDays(startingYear=min(fromDate.year, toDate.year))
        return marketdays.index(toDate) - marketdays.index(fromDate)

    @classmethod
    def getMarketDays(cls, year=None, startingYear: int=None, startingFrom: datetime=None) -> List[date]:
        if gconfig.testing.enabled:
            # print('year:', year, 'startingYear:', startingYear, 'startingFrom:', startingFrom)
            pass
        self = cls()
        if year:
            days = self._getMarketDaysForYear(year)
        elif startingYear:
            days = self._getMarketDaysStartingFromYear(startingYear)
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
        for y in range(datetime.now().year - year + 1):
            days.extend(self._getMarketDaysForYear(year + y))
        return days

    def _getMarketHolidays(self, yr, market:MarketType):
        holidays = []
        yr = int(yr)

        # new years day
        if market != MarketType.CANADA_US_SHARED:
            dt = date(yr, 1, 1)
            if market == MarketType.CANADA and dt.weekday() == 5: dt = dt + timedelta(days=2)
            elif dt.weekday() == 6: dt = dt + timedelta(days=1)
            holidays.append(dt)

        # martin luther king jr day (third monday of jan)
        if market == MarketType.US:
            if yr > 1997:
                mondaycounter = 0
                dt = date(yr-1, 12, 31)
                while mondaycounter < 3:
                    dt = dt + timedelta(days=1)
                    if dt.weekday() == 0: mondaycounter += 1
                holidays.append(dt)

        # family day for Canadian markets
        # presidents day (third monday of feb) for US markets
        familydaystartyear = 2008
        if (market == MarketType.CANADA_US_SHARED and yr >= familydaystartyear) or (market == MarketType.US and yr <= familydaystartyear):
            mondaycounter = 0
            dt = date(yr, 1, 31)
            while mondaycounter < 3:
                dt = dt + timedelta(days=1)
                if dt.weekday() == 0: mondaycounter += 1
            holidays.append(dt)

        # good Friday
        if market == MarketType.CANADA_US_SHARED:
            a = yr % 19
            b = yr // 100
            c = yr % 100
            d = (19 * a + b - b // 4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
            e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
            f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
            month = f // 31
            day = f % 31 + 1
            holidays.append(date(yr, month, day) - timedelta(days=2))

        # victoria day canada (second last monday of may)
        # memorial day us (last monday of may)
        if market == MarketType.CANADA or market == MarketType.US:
            lastmonday = date(yr, 5, 20)
            dt = lastmonday
            while dt.month == 5:
                if dt.weekday() == 0: lastmonday = dt
                dt = dt + timedelta(days=1)

            if market == MarketType.CANADA:
                holidays.append(lastmonday - timedelta(days=7))
            else:
                holidays.append(lastmonday)

        # juneteenth day US
        if market == MarketType.US:
            if yr >= 2022:
                dt = date(yr, 6, 19)
                if dt.weekday() == 5: dt = dt - timedelta(days=1)
                elif dt.weekday() == 6: dt = dt + timedelta(days=1)
                holidays.append(dt)

        # canada day (july 1)
        if market == MarketType.CANADA:
            dt = date(yr, 7, 1)
            if dt.weekday() == 5: dt = dt + timedelta(days=2)
            elif dt.weekday() == 6: dt = dt + timedelta(days=1)
            holidays.append(dt)

        # independence day (july 4)
        if market == MarketType.US:
            dt = date(yr, 7, 4)
            if dt.weekday() == 5: dt = dt - timedelta(days=1)
            elif dt.weekday() == 6: dt = dt + timedelta(days=1)
            holidays.append(dt)

        # civic holiday (first monday in august)
        if market == MarketType.CANADA:
            dt = date(yr, 8, 1)
            for i in range(8):
                if dt.weekday() == 0: break
                dt = dt + timedelta(days=1)
            holidays.append(dt)

        # labor day (first monday in sept)
        if market == MarketType.CANADA_US_SHARED:
            dt = date(yr, 9, 1)
            for i in range(8):
                if dt.weekday() == 0: break
                dt = dt + timedelta(days=1)
            holidays.append(dt)

        # national day for trust/reconcil (last day of sept)
        if market == MarketType.CANADA:
            if yr > 2022:
                dt = date(yr, 9, 30)
                if dt.weekday() == 5: dt = dt + timedelta(days=2)
                elif dt.weekday() == 6: dt = dt + timedelta(days=1)
                holidays.append(dt)

        if market != MarketType.CANADA_US_SHARED:
            holidays.append(self._getThanksgivingDay(yr, market))

        if market != MarketType.CANADA_US_SHARED:
            xmasdt = self._getChristmasDay(yr, market)
            holidays.append(xmasdt)

        # boxing day
        if market == MarketType.CANADA:
            dt = date(yr, 12, 26)
            if dt.weekday() == 5 or dt.weekday() == 6: dt += timedelta(days=2)
            elif dt.weekday() == 0: dt += timedelta(days=1) ## xmas day already pushed forward from sunday
            holidays.append(dt)

        return holidays

    @staticmethod
    def _getThanksgivingDay(yr, market:MarketType=MarketType.US):
        # canada - second monday of oct
        if market == MarketType.CANADA:
            mondaycounter = 0
            dt = date(yr, 10, 1) - timedelta(days=1)
            while mondaycounter < 2:
                dt = dt + timedelta(days=1)
                if dt.weekday() == 0: mondaycounter += 1
            return dt
        # us - fourth thursday of nov
        if market == MarketType.US:
            dt = date(yr, 10, 31)
            thursdaycounter = 0
            while thursdaycounter < 4:
                dt = dt + timedelta(days=1)
                if dt.weekday() == 3: thursdaycounter += 1
            return dt

    @staticmethod
    def _getChristmasDay(yr, market:MarketType=MarketType.US):
        dt = date(yr, 12, 25)
        if market == MarketType.CANADA and dt.weekday() == 5:   dt = dt + timedelta(days=2)
        elif market == MarketType.US and dt.weekday() == 5:       dt = dt - timedelta(days=1)
        elif dt.weekday() == 6: dt = dt + timedelta(days=1)
        return dt

    def _getMarketHalfDays(self, yr):
        holidays = []
        yr = int(yr)

        holidays.append(self._getThanksgivingDay(yr) + timedelta(days=1))
        holidays.append(self._getChristmasDay(yr) - timedelta(days=1))

        return holidays



if __name__ == '__main__':
    # print(MarketDayManager.getMarketHolidays(2021))
    print(MarketDayManager.getMarketHolidays(2020, exchange='TSX'))
    # print(MarketDayManager.getMarketHolidays(2020))
    # print(MarketDayManager.getMarketDays(startingFrom=datetime(2019, 12, 2, 8, 0)))
    # print(MarketDayManager.getMarketDayDiff(date(2022, 1, 14), date(2021, 12, 28)))
    # print(MarketDayManager.getMarketDayDiff(date(2021, 1, 25), date(2000, 1, 25)))
    # print(MarketDayManager.getPreviousMarketDay(date(2000, 2, 22)))
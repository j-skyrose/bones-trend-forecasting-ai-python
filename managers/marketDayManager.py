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
from constants.enums import MarketRegion
from constants.exceptions import ArgumentError
from utils.support import Singleton, asDate, asDatetime, getIndex
from utils.other import getMarketRegion

# http://www.market-holidays.com/2022
# https://www.workingdays.ca/workingdays_holidays_2010_Toronto%20Stock%20Exchange.htm#

class MarketDayManager(Singleton):
    marketHolidays: dict = {MarketRegion.CANADA_US_SHARED: {}}
    marketHalfDays: dict = {}
    marketDays: dict = {}

    @classmethod
    def getMarketHolidays(cls, yr, exchange='NYSE', **kwargs):
        yr = str(yr)

        region = getMarketRegion(exchange)
        if region not in cls.marketHolidays:
            cls.marketHolidays[region] = {}

        if yr not in cls.marketHolidays[region]:
            cls.marketHolidays[region][yr] = cls._getMarketHolidays(yr, region)

        if region == MarketRegion.CANADA or region == MarketRegion.US:
            if yr not in cls.marketHolidays[MarketRegion.CANADA_US_SHARED]:
                cls.marketHolidays[MarketRegion.CANADA_US_SHARED][yr] = cls._getMarketHolidays(yr, MarketRegion.CANADA_US_SHARED)
            return cls.marketHolidays[MarketRegion.CANADA_US_SHARED][yr] + cls.marketHolidays[region][yr]

        return cls.marketHolidays[region][yr]
    
    @classmethod
    def isHoliday(cls, dt, **kwargs):
        dt = asDate(dt)
        return dt in cls.getMarketHolidays(dt.year, **kwargs)

    @classmethod
    def getMarketHalfdays(cls, yr):
        yr = str(yr)
        if yr not in cls.marketHalfDays:
            cls.marketHalfDays[yr] = cls._getMarketHalfDays(yr)
        return cls.marketHalfDays[yr]

    @classmethod
    def getLastMarketDay(cls, d: date=date.today()) -> date:
        if d.weekday() > 4:
            d = d - timedelta(days=(d.weekday() % 4))
        holidays = cls.getMarketHolidays(d.year)
        while d in holidays or d.weekday() > 4:
            d = d - timedelta(days=1)
        return d

    @classmethod
    def getPreviousMarketDay(cls, d: date=date.today()) -> date:
        d = d - timedelta(days=1)
        return cls.getLastMarketDay(d)

    @classmethod
    def getMarketDayDiff(cls, fromDate: date, toDate: date) -> int:
        holidays1 = cls.getMarketHolidays(fromDate.year)
        holidays2 = cls.getMarketHolidays(toDate.year)
        if fromDate.weekday() > 4 or toDate.weekday() > 4 or fromDate in holidays1 or toDate in holidays2:
            raise ValueError('One of the dates is not a market day')
        if fromDate == toDate:
            return 0
        
        marketdays = cls.getMarketDays(startingYear=min(fromDate.year, toDate.year))
        return marketdays.index(toDate) - marketdays.index(fromDate)

    @classmethod
    def getMarketDays(cls, year=None, month: int=None, startingYear: int=None, startingFrom: datetime=None, ending: datetime=None, **kwargs) -> List[date]:
        if year:
            if month is not None:
                days = cls._getMarketDaysForMonth(year, month, **kwargs)
            else:
                days = cls._getMarketDaysForYear(year, **kwargs)
        elif startingYear:
            days = cls._getMarketDaysStartingFromYear(startingYear, **kwargs)
        elif startingFrom:
            startingFrom = asDatetime(startingFrom)
            days = cls._getMarketDaysStartingFromYear(startingFrom.year, **kwargs)
        else:
            raise ArgumentError
        
        lowerLimit = datetime.min if not startingFrom else startingFrom
        upperLimit = datetime.max if not ending else asDatetime(ending)
            
        return [d.date() for d in days if lowerLimit <= d and d <= upperLimit]

    @classmethod
    def advance(cls, startDate: date=date.today(), amount: int=1) -> date:
        ## assume ~265 market days per year

        cdate = startDate
        marketdays = cls.getMarketDays(year=cdate.year)
        ind = getIndex(marketdays, lambda d: d==cdate)
        if ind is None: raise ValueError('Start date is not a market day')

        for i in range(50):
            if ind + amount > len(marketdays) - 1:
                amount = amount - (len(marketdays) - ind)
                marketdays = cls.getMarketDays(year=cdate.year+1)
                cdate = marketdays[0]
                ind = 0
            elif ind + amount < 0:
                amount = amount + ind + 1
                marketdays = cls.getMarketDays(year=cdate.year-1)
                cdate = marketdays[-1]
                ind = len(marketdays) - 1
            else:
                return marketdays[ind + amount]
            
        raise IndexError('Unable to determine vanced date')

    @classmethod
    def _getMarketDaysForYear(cls, year, **kwargs) -> List[date]:
        if year not in cls.marketDays:
            days = [datetime(year, 1, 1, 23, 59, 59) + timedelta(days=d) for d in range(366 if calendar.isleap(year) else 365)]
            ## remove weekends and holidays
            days[:] = [d for d in days if d.weekday() < 5 and d.date() not in cls.getMarketHolidays(year, **kwargs)]
            cls.marketDays[str(year)] = days
        return cls.marketDays[str(year)]

    @classmethod
    def _getMarketDaysForMonth(cls, year, month, **kwargs):
        days = cls._getMarketDaysForYear(year, **kwargs)
        ## keep only given month
        days[:] = [d for d in days if d.month == month]
        return days

    @classmethod
    def _getMarketDaysStartingFromYear(cls, year, **kwargs) -> List[date]:
        year = int(year)
        days = []
        for y in range(datetime.now().year - year + 1):
            days.extend(cls._getMarketDaysForYear(year + y, **kwargs))
        return days

    @classmethod
    def _getMarketHolidays(cls, yr, region:MarketRegion):
        holidays = []
        yr = int(yr)

        # new years day
        if region != MarketRegion.CANADA_US_SHARED:
            dt = date(yr, 1, 1)
            if region == MarketRegion.CANADA and dt.weekday() == 5: dt = dt + timedelta(days=2)
            elif dt.weekday() == 6: dt = dt + timedelta(days=1)
            holidays.append(dt)

        # martin luther king jr day (third monday of jan)
        if region == MarketRegion.US:
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
        if (region == MarketRegion.CANADA_US_SHARED and yr >= familydaystartyear) or (region == MarketRegion.US and yr <= familydaystartyear):
            mondaycounter = 0
            dt = date(yr, 1, 31)
            while mondaycounter < 3:
                dt = dt + timedelta(days=1)
                if dt.weekday() == 0: mondaycounter += 1
            holidays.append(dt)

        # good Friday
        if region == MarketRegion.CANADA_US_SHARED:
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
        if region == MarketRegion.CANADA or region == MarketRegion.US:
            lastmonday = date(yr, 5, 20)
            dt = lastmonday
            while dt.month == 5:
                if dt.weekday() == 0: lastmonday = dt
                dt = dt + timedelta(days=1)

            if region == MarketRegion.CANADA:
                holidays.append(lastmonday - timedelta(days=7))
            else:
                holidays.append(lastmonday)

        # juneteenth day US
        if region == MarketRegion.US:
            if yr >= 2022:
                dt = date(yr, 6, 19)
                if dt.weekday() == 5: dt = dt - timedelta(days=1)
                elif dt.weekday() == 6: dt = dt + timedelta(days=1)
                holidays.append(dt)

        # canada day (july 1)
        if region == MarketRegion.CANADA:
            dt = date(yr, 7, 1)
            if dt.weekday() == 5: dt = dt + timedelta(days=2)
            elif dt.weekday() == 6: dt = dt + timedelta(days=1)
            holidays.append(dt)

        # independence day (july 4)
        if region == MarketRegion.US:
            dt = date(yr, 7, 4)
            if dt.weekday() == 5: dt = dt - timedelta(days=1)
            elif dt.weekday() == 6: dt = dt + timedelta(days=1)
            holidays.append(dt)

        # civic holiday (first monday in august)
        if region == MarketRegion.CANADA:
            dt = date(yr, 8, 1)
            for i in range(8):
                if dt.weekday() == 0: break
                dt = dt + timedelta(days=1)
            holidays.append(dt)

        # labor day (first monday in sept)
        if region == MarketRegion.CANADA_US_SHARED:
            dt = date(yr, 9, 1)
            for i in range(8):
                if dt.weekday() == 0: break
                dt = dt + timedelta(days=1)
            holidays.append(dt)

        # national day for trust/reconcil (last day of sept)
        if region == MarketRegion.CANADA:
            if yr > 2022:
                dt = date(yr, 9, 30)
                if dt.weekday() == 5: dt = dt + timedelta(days=2)
                elif dt.weekday() == 6: dt = dt + timedelta(days=1)
                holidays.append(dt)

        if region != MarketRegion.CANADA_US_SHARED:
            holidays.append(cls._getThanksgivingDay(yr, region))

        if region != MarketRegion.CANADA_US_SHARED:
            xmasdt = cls._getChristmasDay(yr, region)
            holidays.append(xmasdt)

        # boxing day
        if region == MarketRegion.CANADA:
            dt = date(yr, 12, 26)
            if dt.weekday() == 5 or dt.weekday() == 6: dt += timedelta(days=2)
            elif dt.weekday() == 0: dt += timedelta(days=1) ## xmas day already pushed forward from sunday
            holidays.append(dt)

        return holidays

    @staticmethod
    def _getThanksgivingDay(yr, region:MarketRegion=MarketRegion.US):
        # canada - second monday of oct
        if region == MarketRegion.CANADA:
            mondaycounter = 0
            dt = date(yr, 10, 1) - timedelta(days=1)
            while mondaycounter < 2:
                dt = dt + timedelta(days=1)
                if dt.weekday() == 0: mondaycounter += 1
            return dt
        # us - fourth thursday of nov
        if region == MarketRegion.US:
            dt = date(yr, 10, 31)
            thursdaycounter = 0
            while thursdaycounter < 4:
                dt = dt + timedelta(days=1)
                if dt.weekday() == 3: thursdaycounter += 1
            return dt

    @staticmethod
    def _getChristmasDay(yr, region:MarketRegion=MarketRegion.US):
        dt = date(yr, 12, 25)
        if region == MarketRegion.CANADA and dt.weekday() == 5:   dt = dt + timedelta(days=2)
        elif region == MarketRegion.US and dt.weekday() == 5:       dt = dt - timedelta(days=1)
        elif dt.weekday() == 6: dt = dt + timedelta(days=1)
        return dt

    @classmethod
    def _getMarketHalfDays(cls, yr):
        holidays = []
        yr = int(yr)

        holidays.append(cls._getThanksgivingDay(yr) + timedelta(days=1))
        holidays.append(cls._getChristmasDay(yr) - timedelta(days=1))

        return holidays



if __name__ == '__main__':
    print(MarketDayManager.getMarketHolidays(2021))
    print(MarketDayManager.getMarketHolidays(2020, exchange='TSX'))
    # print(MarketDayManager.getMarketHolidays(2020))
    print(MarketDayManager.getMarketDays(startingFrom=datetime(2019, 12, 2, 8, 0)))
    # print(MarketDayManager.getMarketDayDiff(date(2022, 1, 14), date(2021, 12, 28)))
    print(MarketDayManager.getMarketDayDiff(date(2021, 1, 25), date(2000, 1, 25)))
    print(MarketDayManager.getPreviousMarketDay(date(2000, 2, 22)))
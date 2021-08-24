import os, sys, json
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"


import numpy, re
from datetime import date, datetime, timedelta
from multiprocessing import Pool, cpu_count

from constants.values import months, foundedSynonyms

class DotDict(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            print('keyerror',item)
            raise AttributeError(item)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class recdotdict(dict):
    """
    A dictionary supporting dot notation.
    """
    # __getattr__ = dict.__getitem__
    
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, dct):
            for key, value in dct.items():
                if hasattr(value, 'keys'):
                    value = recdotdict(value)
                self[key] = value

    # def __init__(self, *args, **kwargs):
    #     print(args, kwargs)
    #     super().__init__(*args, **kwargs)
    #     for k, v in self.items():
    #         if isinstance(v, dict):
    #             self[k] = recdotdict(v)

    def lookup(self, dotkey):
        """
        Lookup value in a nested structure with a single key, e.g. "a.b.c"
        """
        path = list(reversed(dotkey.split(".")))
        v = self
        while path:
            key = path.pop()
            if isinstance(v, dict):
                v = v[key]
            elif isinstance(v, list):
                v = v[int(key)]
            else:
                raise KeyError(key)
        return v

def recdotlist(list):
    return [recdotdict(l) for l in list]

def recdot(obj):
    return recdotlist(obj) if type(obj) is list else recdotdict(obj)

class Singleton(object):
    def __new__(cls, *args, **kwds):
        it = cls.__dict__.get("__it__")
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        it.init(*args, **kwds)
        return it
    def init(self, *args, **kwds):
        pass

def shortc(val, e):
    ## and (type(val) is not list or (type(val) is list and len(val) > 0))
    # try:
    return val if val != '' and val != None else e
    # except:

def flatten(li: list):
    return list(_flattenGen(li))

def _flattenGen(li: list):
    # return [item for sublist in t for item in sublist]
    """Flatten lists or tuples into their individual items. If those items are
    again lists or tuples, flatten those."""

    if isinstance(li, (list, tuple)):
        for item in li:
            yield from flatten(item)
    else:
        yield li

def _isoformatd(d) -> date:
    return date.fromisoformat(d.date)

def _edgarformatd(d) -> date:
    return date(int(d[:4]), int(d[4:6]), int(d[6:]))


def getMarketHolidays(yr):
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

    # thanksgiving day (us - fourth thursday of nov)
    dt = date(yr, 10, 31)
    thursdaycounter = 0
    while thursdaycounter < 4:
        dt = dt + timedelta(days=1)
        if dt.weekday() == 3: thursdaycounter += 1
    holidays.append(dt)

    # christmas day
    dt = date(yr, 12, 25)
    if dt.weekday() == 5: dt = dt - timedelta(days=1)
    if dt.weekday() == 6: dt = dt + timedelta(days=1)
    holidays.append(dt)

    return holidays



## attempt to parse a date out of a description string, otherwise return the description for later analysis, or 'e' if its empty
## expects a date in the format: december 12, 2000
def extractDateFromDesc(desc):
    DEBUG = False
    averagemissingdatedata = False
    if desc is None or len(desc) == 0: return 'e'

    desc = desc.lower()
    year = None
    month = None
    day = None
    
    monthregex = re.compile('(' + '|'.join(months) + ')')
    exactdateregex = re.compile(monthregex.pattern + '\ \d+,\ *\d\d\d\d')
    foundedregex = re.compile('was (' + '|'.join(foundedSynonyms) + ')\ ')

    exactdateres = re.search(re.compile(foundedregex.pattern + exactdateregex.pattern), desc)
    if DEBUG: print(exactdateres)
    if exactdateres:
        d = re.search(exactdateregex, exactdateres[0])[0]
        monthres = re.search(monthregex, d)
        dayyear = d[monthres.end():].split(',')
        year = dayyear[1]
        month = monthres[0]
        day = dayyear[0]
    else:
        monthyeardateres = re.search(re.compile(foundedregex.pattern + 'in\ ' + monthregex.pattern + '\ \d\d\d\d'), desc)
        if DEBUG: print(monthyeardateres)
        if monthyeardateres:
            monthres = re.search(monthregex, monthyeardateres[0])
            year = monthyeardateres[0][monthres.end():]
            month = monthres[0]
            day = 15
            if not averagemissingdatedata: return '' + str(int(year)) + '-' + str(int(months.index(month)) + 1)
        else:
            yeardateres = re.search(re.compile(foundedregex.pattern + 'in\ \d\d\d\d'), desc)
            if DEBUG: print(yeardateres)
            if yeardateres:
                year = re.search(r'\d\d\d\d', yeardateres[0])[0]
                month = months[6]
                day = 15
                if not averagemissingdatedata: return str(int(year))
            else:
                return None

    return date(int(year), int(months.index(month)) + 1, int(day)).isoformat()

def processRawValueToInsertValue(v):
    if type(v) == int:
        return str(v)
    elif type(v) == bool:
        return '1' if v else '0'
    elif type(v) == list:
        return '\'' + json.dumps(v) + '\''
    elif v is None:
        return 'NULL'
    else:
        return '\'' + v + '\''

def processDBQuartersToDicts(qlist):
    createQuarterObj = lambda rw: { 'period': rw.period, 'quarter': rw.quarter, 'filed': rw.filed, 'nums': { rw.tag: rw.value }}
    ret = []
    curquarter = createQuarterObj(qlist[0])
    for r in qlist[1:]:
        if curquarter['period'] != r.period:
            ret.append(curquarter)
            curquarter = createQuarterObj(r)
        else:
            curquarter['nums'][r.tag] = r.value
    ret.append(curquarter)

    return recdotlist(ret)

def multicore_poolIMap(func, iter, chuckSize=1):
    pool = Pool()
    ret = pool.imap(func, iter, chuckSize)
    pool.close()
    pool.join()
    return ret

if __name__ == '__main__':
    # print(getMarketHolidays(2021))
    # print(processRawValueToInsertValue(44))
    # print(processRawValueToInsertValue('dave'))
    # print(processRawValueToInsertValue(None))
    # print(processRawValueToInsertValue(['4', 4, None]))
    # print(processRawValueToInsertValue(True))
    print(flatten([1,[3,'dave',[6,[0,6,0],6],2],3,{'key':'value'}]))

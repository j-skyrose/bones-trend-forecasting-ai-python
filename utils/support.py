import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"


import numpy, re, math, calendar, json
from datetime import date, datetime, timedelta
from multiprocessing import Pool, cpu_count
from typing import Union

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

def shortcdict(dict, key, e, shortcValue=True):
    try:
        if shortcValue: return shortc(dict[key], e)
        else: return dict[key]
    except KeyError:
        return e

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

def unixToDatetime(u): 
    if u > 9999999999: u /= 1000
    return datetime.utcfromtimestamp(u)
def datetimeToUnix(d): return calendar.timegm(d.timetuple()) 

def asISOFormat(dt: Union[date, datetime, str]):
    if type(dt) == date:
        return dt.isoformat()
    elif type(dt) == datetime:
        return dt.date().isoformat()
    elif type(dt) == str:
        return datetime.fromisoformat(dt).date().isoformat()
    
    raise ValueError('Unrecognized type')

def asDate(dt: Union[date, datetime, str]):
    if type(dt) == date:
        return dt
    elif type(dt) == datetime:
        return dt.date()
    elif type(dt) == str:
        return date.fromisoformat(dt)
    
    raise ValueError('Unrecognized type')

def asDatetime(dt: Union[date, datetime, str]):
    if type(dt) == date:
        return datetime(dt.year, dt.month, dt.day)
    elif type(dt) == datetime:
        return dt
    elif type(dt) == str:
        return datetime.fromisoformat(dt)
    
    raise ValueError('Unrecognized type')

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

def getAdjustedSlidingWindowSize(total, desired):
    DEBUG = False

    numofsets = total / desired
    remainder = (total/desired) % 1

    if DEBUG: print(numofsets)
    if DEBUG: print(remainder)

    increasesetsize = False
    if numofsets > 2 and remainder < 0.5:
        increasesetsize = True
    
    if DEBUG: print(increasesetsize)

    adjust = 0
    for x in range(desired):
        if increasesetsize:
            if DEBUG: print(x, (total / (desired + x)))
            if (total / (desired + x)) < math.floor(numofsets):
                adjust = x
                break
        else:
            if DEBUG: print(x, (total / (desired - x)))
            if (total / (desired - x)) > math.ceil(numofsets):
                adjust = -1 * (x - 1)
                break
    
    return (desired + adjust) / total

def containsAllKeys(dict, *args, throwSomeError=None, throwAllError=None):
    cont = 0
    out = 0
    for k in args:
        if k not in dict.keys():
            out += 1
        else:
            cont += 1
    
    if throwSomeError and out > 0 and cont > 0: raise throwSomeError
    if cont != len(args): 
        if throwAllError: raise throwAllError
        else: return False

    return True

if __name__ == '__main__':
    # print(processRawValueToInsertValue(44))
    # print(processRawValueToInsertValue('dave'))
    # print(processRawValueToInsertValue(None))
    # print(processRawValueToInsertValue(['4', 4, None]))
    # print(processRawValueToInsertValue(True))
    # print(flatten([1,[3,'dave',[6,[0,6,0],6],2],3,{'key':'value'}]))
    # print(getAdjustedSlidingWindowSize(5000, 600))
    pass

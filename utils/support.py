import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, re, math, calendar, json, pickle, tqdm, zlib, hashlib, base64
from tqdm.contrib.concurrent import process_map
from datetime import date, datetime, timedelta
from multiprocessing import Pool, cpu_count
from typing import Callable, Dict, Union
from enum import Enum

from constants.values import months, foundedSynonyms, indicatorsKey, normalizationColumnPrefix

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

    def __init__(self, dct={}):
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

def recdotobj(obj):
    if type(obj) is list:
        return [recdotobj(i) for i in obj]
    return recdotdict(obj)

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

class GetMemoryUsage(object):
    ## adds function to recursively and fuzzily determine memory usage of the instantiated class object
    def _getMemorySize(cls) -> int:
        sz = 0
        for a in dir(cls):
            if not a.startswith('_'):
                sz += sys.getsizeof(cls.__getattribute__(a))
        return sz + sys.getsizeof(cls)

def shortc(val, e):
    ## and (type(val) is not list or (type(val) is list and len(val) > 0))
    # try:
    listCond = len(val) > 0 if type(val) is list else True
    return val if val != '' and val != None and listCond else e
    # except:

def shortcdict(dict, key, e=None, shortcValue=True):
    try:
        if shortcValue: return shortc(dict[key], e)
        else: return dict[key]
    except (KeyError, TypeError):
        return e

## for SQLite connect.row_factory
def recdotdict_factory(cursor, row):
    retdict = {}
    for idx, col in enumerate(cursor.description):
        if col[0] == 'timestamp' and re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}', shortc(row[idx], '')):
            retdict[col[0]] = datetime.strptime(row[idx], '%Y-%m-%d %X')
        elif col[0].startswith('pickled'):
            retdict[col[0]] = pickle.loads(row[idx])
        else: retdict[col[0]] = row[idx]
    return recdotdict(retdict)

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

## used on rows from historical_data table
def _isoformatd(d) -> date:
    return date.fromisoformat(d.period_date)

def _edgarformatd(d) -> date:
    return date(int(d[:4]), int(d[4:6]), int(d[6:]))

def unixToDatetime(u): 
    if u > 9999999999: u /= 1000
    return datetime.utcfromtimestamp(u)
def datetimeToUnix(d): return calendar.timegm(d.timetuple()) 

def toUSAFormat(dt, separator='-'):
    dt = asDate(dt)
    return f'{str(dt.month).zfill(2)}{separator}{str(dt.day).zfill(2)}{separator}{dt.year}'

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

def asList(val):
    if val is None: return []
    return val if type(val) is list else [val]

def asBytes(val):
    return val if type(val) == bytes else val.encode()

## basically a date that is the first day of the month it represents (including year)
def asMonthKey(dt: Union[date, datetime, str]):
    dt = date.fromisoformat(asISOFormat(dt))
    return date(dt.year, dt.month, 1)

def isSameYear(dt1: Union[date, datetime, str], dt2: Union[date, datetime, str]):
    return asDate(dt1).year == asDate(dt2).year

## implicitly isSameYear too
def isSameMonth(dt1: Union[date, datetime, str], dt2: Union[date, datetime, str]):
    if not isSameYear(dt1, dt2): return False
    return asDate(dt1).month == asDate(dt2).month

## turns '003,4.50,2' into (3, 4.5, 2)
def parseCSVFloatsIntoTuple(x: str):
    return tuple([float(n) for n in x.split(',')])

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

def getAdjustedSlidingWindowPercentage(total, desired):
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



## search/find/get/lambda-based method of generic retrieval from list of objects
class ReturnType(Enum):
    INDEX = 'INDEX'
    VALUE = 'VALUE'

def getIndex(iterable, matchArg: Callable[[Dict], bool]):
    return _getFromListWithCustomMatchFunction(iterable, matchArg, ReturnType.INDEX)

def getItem(iterable, matchArg: Callable[[Dict], bool]):
    return _getFromListWithCustomMatchFunction(iterable, matchArg, ReturnType.VALUE)

def _getFromListWithCustomMatchFunction(iterable, matchArg, returnType: ReturnType):
    matchFunction = (lambda x: x == matchArg) if type(matchArg) != Callable else matchArg
    for i, val in enumerate(iterable):
        if matchFunction(val):
            if returnType == ReturnType.INDEX: return i
            elif returnType == ReturnType.VALUE: return val

## TQDM progress bar, with verbose optionality
def tqdmLoopHandleWrapper(iterable, verbose=0, **kwargs):
    return tqdm.tqdm(iterable, leave=verbose>=1, **kwargs) if verbose > 0 else iterable

## multicore TQDM progress bar, with verbose optionality
def tqdmProcessMapHandlerWrapper(fn, iterable, verbose=0, chunksize=1, sequentialOverride=False, **kwargs):
    if sequentialOverride: ## primarily for debugging issues in 'fn'
        retlist = []
        for i in tqdmLoopHandleWrapper(iterable, verbose, **kwargs):
            retlist.append(fn(i))
        return retlist
    return process_map(fn, iterable, leave=verbose>=1, chunksize=chunksize, **kwargs) if verbose > 0 else list(map(fn, iterable))

## generates all fib values up to and including the given arg, e.g []
def generateFibonacciSequence(limit):
    ## base case
    retseq = [0,1]
    
    ## loop until limit passed
    while retseq[-1] < limit:
        retseq.append(retseq[-1] + retseq[-2])

    return retseq

## checks if any indicators in the config are enabled
def someIndicatorEnabled(cf):
    for v in cf.feature[indicatorsKey].values():
        if v.enabled: return True
    return False

def convertToCamelCase(string, firstCapital=False):
    ret = ''
    capitalizeCurrent = False
    for char in string:
        if capitalizeCurrent: ret += str(char).capitalize()
        elif char != '_': ret += char

        capitalizeCurrent = char == '_'
    if firstCapital: ret = str(ret[0]).capitalize() + ret[1:]
    return ret

def convertToSnakeCase(string):
    ret = ''
    char: str
    for idx,char in enumerate(string):
        if idx != 0 and char.isupper(): ret += '_'
        ret += char.lower()
    return ret

def isNormalizationColumn(c):
    return str(c).startswith(normalizationColumnPrefix)

## for SQL queries
def generateCommaSeparatedQuestionMarkString(val):
    if hasattr(val, '__len__'): val = len(val)
    if type(val) != int: raise ValueError('Must be an integer')
    return ','.join(('?',) * val)

## replaces '?'s with the actual argument values
def combineSQLStatementAndArguments(stmt, args=[]):
    if args:
        for a in args:
            stmt = stmt.replace('?', a, 1)
    return stmt

## adds item to container at given key if it exists, otherwise adds a container with the item at that key
def addItemToContainerAtDictKey(dct, key, item, pushFunctionName='append', containerType=list):
    try: getattr(dct[key], pushFunctionName)(item)
    except KeyError:
        dct[key] = containerType([item])

## filter iterable into multiple lists based on some condition(s); separate, split
def partition(iterable, predicates, verbose=0):
    predicates = asList(predicates)
    output = [[] for _ in range(len(predicates)+1)]
    
    for item in tqdmLoopHandleWrapper(iterable, verbose=verbose, desc='Partitioning'):
        metSomePredicate = False
        for indx, predicate in enumerate(predicates):
            if predicate(item):
                output[indx].append(item)
                metSomePredicate = True
                break
        if not metSomePredicate:
            output[-1].append(item)
            
    return output

## generates hash that can be safely used, particularly in file names
def urlSafeHash(string):
    return base64.urlsafe_b64encode(hashlib.md5(string.encode()).digest()).decode('utf-8').replace('=','')

## compresses an object to bytes
def compressObj(obj):
    return zlib.compress((obj if type(obj) == str else json.dumps(obj)).encode())

if __name__ == '__main__':
    # print(processRawValueToInsertValue(44))
    # print(processRawValueToInsertValue('dave'))
    # print(processRawValueToInsertValue(None))
    # print(processRawValueToInsertValue(['4', 4, None]))
    # print(processRawValueToInsertValue(True))
    # print(flatten([1,[3,'dave',[6,[0,6,0],6],2],3,{'key':'value'}]))
    # print(getAdjustedSlidingWindowPercentage(5000, 600))
    print(convertToCamelCase('test', True))
    print(convertToCamelCase('test_not_camel', False))
    print(shortcdict(None, 't', 2))
    pass

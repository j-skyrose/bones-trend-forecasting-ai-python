import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import operator
from enum import Enum
from utils.support import shortc

class SeriesType(Enum):
    def __init__(self, a, b):
        self.function = a
        self.description = b

    INTRADAY =          'TIME_SERIES_INTRADAY', 'Time Series (?)'
    DAILY =             'TIME_SERIES_DAILY', 'Time Series (Daily)'
    DAILY_ADJUSTED =    'TIME_SERIES_DAILY_ADJUSTED', 'Time Series (Daily)'
    WEEKLY =            'TIME_SERIES_WEEKLY', 'Weekly Time Series'
    WEEKLY_ADJUSTED =   'TIME_SERIES_WEEKLY_ADJUSTED', 'Weekly Time Series'
    MONTHLY =           'TIME_SERIES_MONTHLY', 'Monthly Time Series'
    MONTHLY_ADJUSTED =  'TIME_SERIES_MONTHLY_ADJUSTED', 'Monthly Time Series'
    MINUTE =            'TIME_SERIES_MINUTE', '' ## polygon only

class InterestType(Enum):
    DAILY = 'DAILY'
    WEEKLY = 'WEEKLY'
    MONTHLY = 'MONTHLY'

class APIState(Enum):
    INVALID = -1
    UNKNOWN = 0
    WORKING = 1

class Direction(Enum):
    ASCENDING = 'ASC'
    DESCENDING = 'DESC'

class AccuracyType(Enum):
    def __init__(self, a, b):
        self.statsName = b

    @classmethod
    def getOpposite(cls, a):
        if a == cls.POSITIVE: return cls.NEGATIVE
        if a == cls.NEGATIVE: return cls.POSITIVE
        return a

    POSITIVE = 'POSITIVE', 'positiveAccuracy'
    NEGATIVE = 'NEGATIVE', 'negativeAccuracy'
    OVERALL = 'OVERALL', 'overallAccuracy'

class SetType(Enum):
    TRAINING = 'TRAINING'
    VALIDATION = 'VALIDATION'
    TESTING = 'TESTING'

class FeatureExtraType(Enum):
    SINGLE = 'SINGLE'
    OF = 'OF'
    KEY = 'KEY'
    VIXKEY = 'VIXKEY'
    FINANCIALS = 'FINANCIALS'
    INTEREST = 'INTEREST'

class FinancialReportType(Enum):
    def __init__(self, alphavantage, fmp, polygon):
        self.alphavantage = alphavantage
        self.fmp = fmp
        self.polygon = polygon

    @classmethod
    def getNameFor(cls, val):
        for v in cls:
            for a in v.value:
                if a == val: return v.name
        
    YEAR =  '', 'year', 'Y'
    # YEAR_ANNUALIZED = '', '', 'YA'
    QUARTER = '', 'quarter', 'Q'
    # QUARTER_ANNUALIZED = '', '', 'QA'
    # TRAILING_TWELVE_MONTH = '', '', 'T'
    # TRAILING_TWELVE_MONTH_ANNUALIZED = '', '', 'TA'

class FinancialStatementType(Enum):
    INCOME = 'INCOME_STATEMENT'
    BALANCE_SHEET = 'BALANCE_SHEET'
    CASH_FLOW = 'CASH_FLOW'

class LossAccuracy(Enum):
    LOSS = 'LOSS'
    ACCURACY = 'ACCURACY'

class CorrBool(Enum):
    CORRECT = 'CORRECT'
    INCORRECT = 'INCORRECT'

class DataFormType(Enum):
    VECTOR = 'VECTOR'
    INTEGER = 'INTEGER'
    NATURAL = 'NATURAL' ##(number)
    BINARY = 'BINARY'
    CATEGORICAL = 'CATEGORICAL'

class InputVectorDataType(Enum):
    STATIC = 'STATIC'
    SEMISERIES = 'SEMISERIES'
    SERIES = 'SERIES'

class OutputClass(Enum):
    POSITIVE = 'POSITIVE'
    NEGATIVE = 'NEGATIVE'

class TimespanType(Enum):
    MINUTE = 'MINUTE'
    HOUR = 'HOUR'
    DAY = 'DAY'
    WEEK = 'WEEK'
    MONTH = 'MONTH'
    QUARTER = 'QUARTER'
    YEAR = 'YEAR'

class AccuracyAnalysisTypes(Enum):
    STOCK = 'STOCK'
    PRECEDING_RANGE = 'PRECEDING_RANGE'

class PrecedingRangeType(Enum):
    INCREASING = 'INCREASING'
    DECREASING = 'DECREASING'
    INCREASINGWITHBETTERHIGH = 'INCREASINGWITHBETTERHIGH'
    DECREASINGWITHBETTERHIGH = 'DECREASINGWITHBETTERHIGH'
    INCREASINGWITHWORSELOW = 'INCREASINGWITHWORSELOW'
    DECREASINGWITHWORSELOW = 'DECREASINGWITHWORSELOW'
    INCREASINGWITHBETTERHIGHANDWORSELOW = 'INCREASINGWITHBETTERHIGHANDWORSELOW'
    DECREASINGWITHBETTERHIGHANDWORSELOW = 'DECREASINGWITHBETTERHIGHANDWORSELOW'

class SQLHelpers(Enum):
    UNKNOWN = 'UNKNOWN'
    NULL = 'NULL'
    NOTNULL = 'NOT NULL'

class OperatorDict(Enum):
    def __init__(self, a, b, c=None, d=None):
        self.function = a
        self.symbol = b
        self.sqlsymbol = shortc(c, b)
        self.polygonsymbol = d

    LESSTHAN =          operator.lt, '>', None, 'lt'
    LESSTHANOREQUAL =   operator.le, '>=', None, 'lte'
    EQUAL =             operator.eq, '='
    NOTEQUAL =          operator.ne, '!=', '<>'
    GREATERTHANOREQUAL= operator.ge, '<=', None, 'gte'
    GREATERTHAN =       operator.gt, '<', None, 'gt'

class MarketType(Enum):
    CANADA = 'CANADA'
    US = 'US'
    CANADA_US_SHARED = 'CANADA_US_SHARED'

class DataManagerType(Enum):
    ANALYSIS = 'ANALYSIS'
    PREDICTION = 'PREDICTION'
    STATS = 'STATS'
    DEFAULT = 'DEFAULT'

if __name__ == '__main__':
    print(AccuracyType.OVERALL.name, AccuracyType.OVERALL.value, AccuracyType.OVERALL.statsName)
    print(FinancialReportType.YEAR.name, FinancialReportType.YEAR.value)
    print(FinancialReportType.getNameFor('Q'))

    print(AccuracyType.getOpposite(AccuracyType.POSITIVE))

    print([e.value for e in AccuracyType].index(AccuracyType.NEGATIVE.value))
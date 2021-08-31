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

class AccuracyType(Enum):
    def __init__(self, a, b):
        self.statsName = b

    @classmethod
    def getOpposite(cls, a):
        if a == cls.POSITIVE: return cls.NEGATIVE
        if a == cls.NEGATIVE: return cls.POSITIVE
        return a

    OVERALL = 'OVERALL', 'overallAccuracy'
    POSITIVE = 'POSITIVE', 'positiveAccuracy'
    NEGATIVE = 'NEGATIVE', 'negativeAccuracy'
    COMBINED = 'COMBINED', 'combinedAccuracy'

class SetType(Enum):
    TRAINING = 'TRAINING'
    VALIDATION = 'VALIDATION'
    TESTING = 'TESTING'

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

class DataFormType(Enum):
    VECTOR = 'VECTOR'
    INTEGER = 'INTEGER'
    NATURAL = 'NATURAL' ##(number)

class OperatorDict(Enum):
    def __init__(self, a, b, c=None):
        self.function = a
        self.symbol = b
        self.sqlsymbol = shortc(c, b)

    LESSTHAN =          operator.lt, '>'
    LESSTHANOREQUAL =   operator.le, '>='
    EQUAL =             operator.eq, '='
    NOTEQUAL =          operator.ne, '!=', '<>'
    GREATERTHANOREQUAL= operator.ge, '<='
    GREATERTHAN =       operator.gt, '<'

if __name__ == '__main__':
    print(AccuracyType.OVERALL.name, AccuracyType.OVERALL.value, AccuracyType.OVERALL.statsName)
    print(FinancialReportType.YEAR.name, FinancialReportType.YEAR.value)
    print(FinancialReportType.getNameFor('Q'))

    print(AccuracyType.getOpposite(AccuracyType.POSITIVE))
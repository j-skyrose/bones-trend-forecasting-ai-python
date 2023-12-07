import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import operator, numpy
from enum import Enum, auto
from constants.values import indicatorsKey
from utils.support import parseCSVFloatsIntoTuple, shortc

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

class LimitType(Enum):
    NONE = 'NONE'
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
    MULTIPLE = 'MULTIPLE'
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

## for numba
InputVectorDataTypeSimplified = Enum('InputVectorDataTypeSimplified', [k.name for k in InputVectorDataType])    

class OutputClass(Enum):
    POSITIVE = 'POSITIVE'
    NEGATIVE = 'NEGATIVE'

class SetClassificationType(Enum):
    def __init__(self, _, index=None, outputClass: OutputClass=None):
        self.index = index
        self.outputClass = outputClass

    @classmethod
    def excludingAll(cls):
        return [e for e in cls if e != cls.ALL]
    ALL = 'ALL'
    ## should be kept in sync with OutputClass enum
    CLASS1 = 'CLASS1', 0, OutputClass.POSITIVE
    CLASS2 = 'CLASS2', 1, OutputClass.NEGATIVE

# SetClassificationType = SetClassificationTypeBase('SetClassificationType', [
#     ('ALL', (auto(),)), 
#     *[( f'CLASS{indx+1}', (auto(), indx, oupcls) ) for indx, oupcls in enumerate(OutputClass)]
# ])

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

class SQLInsertHelpers(Enum):
    NONE = ''
    ABORT = ' OR ABORT '
    FAIL = ' OR FAIL '
    IGNORE = ' OR IGNORE '
    REPLACE = ' OR REPLACE '
    ROLLBACK = ' OR ROLLBACK '

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

class IndicatorType(Enum):
    def __init__(self, a, b, c, d=None):
        self.key = a
        self.longForm = b
        self.compositeKey = '_'.join([indicatorsKey, self.longForm])
        self.featureExtraType = c
        self.emaPeriod = d

        if self.key == 'ST':
            self.sqlParser = lambda x: (float(x.split(',')[0]), SuperTrendDirection[x.split(',')[1]])
        else:
            self.sqlParser = parseCSVFloatsIntoTuple if self.featureExtraType != FeatureExtraType.SINGLE else lambda x: float(x)

    @classmethod
    def getByProp(cls, val, prop='longForm'):
        for v in cls:
            if val == v.__getattribute__(prop): return v

    @classmethod
    def getEMAs(cls):
        return [e for e in cls if e.emaPeriod]
    
    @classmethod
    def getActuals(cls):
        ## remove 'indicators' that are more for typing than actual values
        nonActuals = [IndicatorType.EMA] 
        return [e for e in cls if e not in nonActuals]
    
    def isEMA(self):
        return 'EMA' in self.key    

    RSI = 'RSI', 'relativeStrengthIndex', FeatureExtraType.SINGLE
    CCI = 'CCI', 'commodityChannelIndex', FeatureExtraType.SINGLE
    ATR = 'ATR', 'averageTrueRange', FeatureExtraType.SINGLE
    DIS = 'DIS', 'directionalIndicators', FeatureExtraType.MULTIPLE
    ADX = 'ADX', 'averageDirectionalIndex', FeatureExtraType.SINGLE
    EMA200 = 'EMA200', 'exponentialMovingAverage200', FeatureExtraType.SINGLE, 200
    EMA100 = 'EMA100', 'exponentialMovingAverage100', FeatureExtraType.SINGLE, 100
    EMA50 = 'EMA50', 'exponentialMovingAverage50', FeatureExtraType.SINGLE, 50
    EMA26 = 'EMA26', 'exponentialMovingAverage26', FeatureExtraType.SINGLE, 26
    EMA20 = 'EMA20', 'exponentialMovingAverage20', FeatureExtraType.SINGLE, 20
    EMA12 = 'EMA12', 'exponentialMovingAverage12', FeatureExtraType.SINGLE, 12
    EMA10 = 'EMA10', 'exponentialMovingAverage10', FeatureExtraType.SINGLE, 10
    EMA5 = 'EMA5', 'exponentialMovingAverage5', FeatureExtraType.SINGLE, 5
    EMA = 'EMA', 'exponentialMovingAverage', FeatureExtraType.SINGLE
    MACD = 'MACD', 'movingAverageConvergenceDivergence', FeatureExtraType.SINGLE
    BB = 'BB', 'bollingerBands', FeatureExtraType.MULTIPLE
    ST = 'ST', 'superTrend', FeatureExtraType.MULTIPLE
    RGVB = 'RGVB', 'redGreenVolumeBars', FeatureExtraType.SINGLE

## for numba
IndicatorTypeSimplified = Enum('IndicatorTypeSimplified', [k.name for k in IndicatorType])

class CalculationMethod(Enum):
    SMA = 'SMA'
    EMA = 'EMA'
    WILDERSMOOTHING = 'WILDERSMOOTHING'

class DataRequiredType(Enum):
    ALL = 'ALL'
    HIGH = 'HIGH'
    LOW = 'LOW'
    CLOSE = 'CLOSE'
    OPEN = 'OPEN'
    VOLUME = 'VOLUME'
    CUSTOM = 'CUSTOM'

class SuperTrendDirection(Enum):
    UP = 'UP'
    DOWN = 'DOWN'
    NONE = 'NONE'

SuperTrendDirectionList = numpy.array([_ for _ in SuperTrendDirection])

# print(SuperTrendDirection.__members__.values())
# print([k for k in SuperTrendDirection])

class ReductionMethod(Enum):
    NONE = 'NONE'
    FIBONACCI = 'FIBONACCI'
    RANDOM = 'RANDOM'
    ALL = 'ALL'

class NormalizationGroupings(Enum):
    def __init__(self, a):
        self.tableName = a
    HISTORICAL = 'historical_data'
    STOCK = 'symbols'
    FINANCIAL = 'vwtb_edgar_financial_nums'

class ChangeType(Enum):
    PERCENTAGE = 'PERCENTAGE'
    ABSOLUTE = 'ABSOLUTE'

class EarningsCollectionAPI(Enum):
    NASDAQ = 'NASDAQ'
    MARKETWATCH = 'MARKETWATCH'
    YAHOO = 'YAHOO'

if __name__ == '__main__':
    print(AccuracyType.OVERALL.name, AccuracyType.OVERALL.value, AccuracyType.OVERALL.statsName)
    print(FinancialReportType.YEAR.name, FinancialReportType.YEAR.value)
    print(FinancialReportType.getNameFor('Q'))

    print(AccuracyType.getOpposite(AccuracyType.POSITIVE))

    print([e.value for e in AccuracyType].index(AccuracyType.NEGATIVE.value))
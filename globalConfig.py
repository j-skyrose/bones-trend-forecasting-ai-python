import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.values import indicatorsKey
from constants.enums import ChangeType, DataFormType, Direction, FeatureExtraType, IndicatorType, NormalizationMethod, OutputClass, ReductionMethod, SeriesType
from utils.support import recdotdict

# TESTING = True
# REDUCED_SYMBOL_SCOPE = 10
# TESTING_PREDICTOR = True
# GET_SYMBOLS_LIMIT = 115

useGPU = True
useMainGPU = True

try:    TESTING
except: TESTING = False
try:    REDUCED_SYMBOL_SCOPE
except: REDUCED_SYMBOL_SCOPE = None
try:    TESTING_PREDICTOR
except: TESTING_PREDICTOR = False
try:    SEED_RANDOM
except: SEED_RANDOM = False
try:    GET_SYMBOLS_LIMIT
except: GET_SYMBOLS_LIMIT = 0

try: useGPU
except NameError: useGPU = False
try: useMainGPU
except NameError: useMainGPU = False

def resetSeeds():
    import numpy, tensorflow, random
    numpy.random.seed(SEED_RANDOM)
    random.seed(SEED_RANDOM)
    tensorflow.random.set_seed(SEED_RANDOM)

if TESTING and SEED_RANDOM:
    useGPU = False ## gpu operations are not guarenteed to be deterministic, even with identical seeds

    # os.environ['PYTHONHASHSEED'] = str(SEED_RANDOM)
    # does not work, variable must be set before python runs > PYTHONHASHSEED=0 python3 myPython.py
    # currently explicitly set in Windows environment variables to 420
    
    resetSeeds()

## default
trainingConfig = {
    ## general
    'seriesType': SeriesType.DAILY,
    'changeType': ChangeType.ANY_DAY_ABSOLUTE,
    'focusedMetric': 'tfpr_metric',
    'setSplitTuple': (2/3,1/3),
    ## more specific, likely to be overridden locally e.g. trainer.py
    'precedingRange': 60,
    'followingRange': 20,
    'changeValue': 10
}

def genFeatureObj(enabled, extype:FeatureExtraType, dataRequired=True):
    return { 'enabled': enabled, 'extraType': extype, 'dataRequired': dataRequired }

config = recdotdict({
    'useGPU': useGPU,
    'useMainGPU': useMainGPU,
    'multicore': not ('VSCODE_GIT_IPC_HANDLE' in os.environ),
    'similarityCalculation': {
        'enabled': False, # should only be enabled programmatically by calculation function(s)
        'earningsDate': {
            'maxDayDifference': 180,
            # for scalar representation (which is default for similarity calculation) which should better capture the perceived difference between the number of days from vector to vector
            # 0 <- postDateThreshold: days before known earnings
            # postDateThreshold -> 1: days after known earnings (up to maxPostDays)
            # 1: days until next earnings unknown
            'postDateThreshold': 0.7,
            'maxPostDays': 7
        }
    },
    'dataForm': {
        'dayOfWeek': DataFormType.VECTOR,
        'dayOfMonth': DataFormType.VECTOR,
        'monthOfYear': DataFormType.VECTOR,
        # 'dayOfWeek': DataFormType.INTEGER,
        # 'dayOfMonth': DataFormType.INTEGER,
        # 'monthOfYear': DataFormType.INTEGER,

        'outputVector': DataFormType.BINARY,
        # 'outputVector': DataFormType.CATEGORICAL

        'superTrend': DataFormType.VECTOR,
        # 'superTrend': DataFormType.INTEGER,

        'earningsDate': {
            'vectorSize2': True # else size 4
        }
    },
    'data': {
        'normalize': False,
        ## not necessarily exhaustive set of normalization columns
        'normalizationMethod': {
            'default': { ## applies to all columns unless they are explicitly specified
                'type': NormalizationMethod.STANDARD_DEVIATION,
                'value': 2.5
            },
            # 'high': {}
            # 'volume': {
            #     'type': NormalizationMethod.REAL_MAX
            # },
            'earningsDate': { ## not optional
                'type': NormalizationMethod.REAL_MAX,
                'value': 700
            }
        },
    },
    'sets': {
        'positiveSplitRatio': 1/6, # default 0.5,
        'minimumClassSplitRatio': 0.13 if not TESTING else 0.01,
        'instanceReduction': {
            'enabled': True,
            'top': 0.5,
            'bottom': 0.03,
            'method': ReductionMethod.FIBONACCI,
            'additionalParameter': Direction.DESCENDING,
            # 'method': ReductionMethod.RANDOM,
            # 'additionalParameter': 0.05,
            # 'method': ReductionMethod.ALL,
            'classType': OutputClass.NEGATIVE
        }
    },
    'predictor': {
        'ifBinaryUseRaw': True,
        'timeWeightedStockAccuracy': False
    },
    'network': {
        'recurrent': True
    },
    'trainer': {
    },
    'feature': {
        'exchange': genFeatureObj(True, FeatureExtraType.SINGLE),
        'sector': genFeatureObj(False, FeatureExtraType.SINGLE, True), ## polygon API changed to v3, this info in DB may be outdated/incorrect due to de/re-listing of symbols by different companys
        'companyAge': genFeatureObj(False, FeatureExtraType.SINGLE, True), ## polygon API changed to v3, this info in DB may be outdated/incorrect due to de/re-listing of symbols by different companys
        'ipoAge': genFeatureObj(False, FeatureExtraType.SINGLE),
        'etf': genFeatureObj(True, FeatureExtraType.SINGLE, True),

        'dayOfWeek': genFeatureObj(True, FeatureExtraType.OF),
        'dayOfMonth': genFeatureObj(True, FeatureExtraType.OF),
        'monthOfYear': genFeatureObj(True, FeatureExtraType.OF),
        'stockSplits': genFeatureObj(True, FeatureExtraType.OF),
        'earningsDate': genFeatureObj(True, FeatureExtraType.OF),
        'stock': {
            'open': genFeatureObj(True, FeatureExtraType.KEY),
            'high': genFeatureObj(True, FeatureExtraType.KEY),
            'low': genFeatureObj(True, FeatureExtraType.KEY),
            'close': genFeatureObj(True, FeatureExtraType.KEY),
            'volume': genFeatureObj(True, FeatureExtraType.KEY)
        },
        'vix': {
            'open': genFeatureObj(True, FeatureExtraType.VIXKEY),
            'high': genFeatureObj(True, FeatureExtraType.VIXKEY),
            'low': genFeatureObj(True, FeatureExtraType.VIXKEY),
            'close': genFeatureObj(True, FeatureExtraType.VIXKEY)
        },
        'financials': {**genFeatureObj(False, FeatureExtraType.FINANCIALS), **{
            'includeDates': True,
            'maxTierIndex': 1,
            'tierTags': [
                ['Assets', 'Liabilities', 'StockholdersEquity']
            ],
        }},
        'googleInterests': genFeatureObj(True, FeatureExtraType.INTEREST),
        indicatorsKey: {
            IndicatorType.RSI: genFeatureObj(True, IndicatorType.RSI.featureExtraType),
            IndicatorType.CCI: genFeatureObj(True, IndicatorType.CCI.featureExtraType),
            IndicatorType.ATR: genFeatureObj(True, IndicatorType.ATR.featureExtraType),
            IndicatorType.DIS: genFeatureObj(True, IndicatorType.DIS.featureExtraType),
            IndicatorType.ADX: genFeatureObj(True, IndicatorType.ADX.featureExtraType),
            IndicatorType.EMA200: genFeatureObj(True, IndicatorType.EMA200.featureExtraType),
            IndicatorType.EMA100: genFeatureObj(True, IndicatorType.EMA100.featureExtraType),
            IndicatorType.EMA50: genFeatureObj(True, IndicatorType.EMA50.featureExtraType),
            IndicatorType.EMA26: genFeatureObj(True, IndicatorType.EMA26.featureExtraType),
            IndicatorType.EMA20: genFeatureObj(True, IndicatorType.EMA20.featureExtraType),
            IndicatorType.EMA12: genFeatureObj(True, IndicatorType.EMA12.featureExtraType),
            IndicatorType.EMA10: genFeatureObj(True, IndicatorType.EMA10.featureExtraType),
            IndicatorType.EMA5: genFeatureObj(True, IndicatorType.EMA5.featureExtraType),
            IndicatorType.MACD: genFeatureObj(True, IndicatorType.MACD.featureExtraType),
            IndicatorType.BB: genFeatureObj(True, IndicatorType.BB.featureExtraType),
            IndicatorType.ST: genFeatureObj(True, IndicatorType.ST.featureExtraType),
            IndicatorType.RGVB: genFeatureObj(True, IndicatorType.RGVB.featureExtraType),
        },

    },

    'cache': {
        'indicators': [
            IndicatorType.DIS,
            IndicatorType.ADX, ## ADX can rely on DIS data, so there are overrides to prevent its cached data from being generated. If DIS is not listed here as a cached indicator but ADX is, then ADX will still attempt to use cached DIS data
            IndicatorType.BB,
            IndicatorType.ST,
            ## CCI, MACD need modification to allow for resumable generation updates in dbm/updateCalculatedTechnicalIndicatorData
        ]
    },

    'defaultIndicatorFormulaConfig': {
        'periods': {
            IndicatorType.RSI: 14,
            IndicatorType.CCI: 20,
            IndicatorType.ATR: 14,
            IndicatorType.ADX: 14,
            IndicatorType.BB: 20,
            IndicatorType.ST: 7
        },
        'modifiers': {
            IndicatorType.EMA: {
                'smoothing': 2
            },
            IndicatorType.BB: {
                'multiplier': 2
            },
            IndicatorType.ST: {
                'multiplier': 3
            }
        }
    },

    'testing': {
        'enabled': TESTING,
        'REDUCED_SYMBOL_SCOPE': REDUCED_SYMBOL_SCOPE,
        'predictor': TESTING_PREDICTOR,
        'exchange': 'NYSE',
        'GET_SYMBOLS_LIMIT': GET_SYMBOLS_LIMIT,
        'predictorStockQueryLimit': 1000
    },

    'training': trainingConfig
})
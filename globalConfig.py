import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.enums import DataFormType, FeatureExtraType, SeriesType
from utils.support import recdotdict

# TESTING = True
# REDUCED_SYMBOL_SCOPE = 10
# TESTING_PREDICTOR = True
# SEED_RANDOM = 420

useGPU = True
useMainGPU = True

try:    TESTING
except: TESTING = False
try:    REDUCED_SYMBOL_SCOPE
except: REDUCED_SYMBOL_SCOPE = -1
try:    TESTING_PREDICTOR
except: TESTING_PREDICTOR = False
try:    SEED_RANDOM
except: SEED_RANDOM = False

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

trainingConfig = {
    ## master
    'setCount': 500,
    'precedingRange': 60,
    'followingRange': 20,
    'threshold': 0.1,
    'setSplitTuple': (5/7,2/7,0/7),
    'seriesType': SeriesType.DAILY,

    'epochs': 10,
    'batchSize': 64,
    'iterations': 5,

} if TESTING else {
    ## master
    'setCount': 125000,
    # 'precedingRange': 126, ## ~0.5 year
    # 'precedingRange': 252, ## ~1 year
    'precedingRange': 200,
    'followingRange': 20, ## ~1 month
    'threshold': 0.4,
    'setSplitTuple': (5/7,2/7,0/7),
    'seriesType': SeriesType.DAILY,

    'epochs': 25,
    'batchSize': 64,
    'iterations': 13,

}

def genFeatureObj(enabled, extype:FeatureExtraType, dataRequired=True):
    return { 'enabled': enabled, 'extraType': extype, 'dataRequired': dataRequired }

config = recdotdict({
    'useGPU': useGPU,
    'useMainGPU': useMainGPU,
    'multicore': not ('VSCODE_GIT_IPC_HANDLE' in os.environ),
    'dataForm': {
        'dayOfWeek': DataFormType.VECTOR,
        'dayOfMonth': DataFormType.VECTOR,
        'monthOfYear': DataFormType.VECTOR,
        # 'dayOfWeek': DataFormType.INTEGER,
        # 'dayOfMonth': DataFormType.INTEGER,
        # 'monthOfYear': DataFormType.INTEGER,

        'outputVector': DataFormType.BINARY,
        # 'outputVector': DataFormType.CATEGORICAL
    },
    'sets': {
        'positiveSplitRatio': 1/6, # default 0.5,
        'minimumClassSplitRatio': 0.13 if not TESTING else 0.01
    },
    'predictor': {
        'ifBinaryUseRaw': True,
        'timeWeightedStockAccuracy': False
    },
    'network': {
        'recurrent': True
    },
    'trainer': {
        'customValidationClassValueRatio': 0.15, ## positive : negative

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
        'googleInterests': genFeatureObj(True, FeatureExtraType.INTEREST)
    },

    'testing': {
        'enabled': TESTING,
        'REDUCED_SYMBOL_SCOPE': REDUCED_SYMBOL_SCOPE,
        'predictor': TESTING_PREDICTOR,
        'exchange': 'NYSE',
        'stockQueryLimit': 50,
        'predictorStockQueryLimit': 100
    },

    'training': trainingConfig
})
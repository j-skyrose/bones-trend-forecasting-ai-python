import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.enums import DataFormType, SeriesType
from utils.support import recdotdict

# TESTING = True
try:
    if TESTING: pass
except:
    TESTING = False

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

def genFeatureObj(enabled, extype, dataRequired=True):
    return { 'enabled': enabled, 'extype': extype, 'dataRequired': dataRequired }

config = recdotdict({
    'multicore': True,
    'dataForm': {
        'dayOfWeek': DataFormType.VECTOR,
        'dayOfMonth': DataFormType.VECTOR,
        'monthOfYear': DataFormType.VECTOR,
        # 'dayOfWeek': DataFormType.INTEGER,
        # 'dayOfMonth': DataFormType.INTEGER,
        # 'monthOfYear': DataFormType.INTEGER
        'outputVector': DataFormType.BINARY,
        # 'outputVector': DataFormType.CATEGORICAL
    },
    'sets': {
        'positiveSplitRatio': 1/6, # default 0.5,
        'minimumClassSplitRatio': 0.15 if not TESTING else 0.01
    },
    'feature': {
        'exchange': genFeatureObj(False, 'single'),
        'sector': genFeatureObj(True, 'single', True),
        'companyAge': genFeatureObj(True, 'single', True),
        'ipoAge': genFeatureObj(False, 'single'),

        'dayOfWeek': genFeatureObj(True, 'of'),
        'dayOfMonth': genFeatureObj(True, 'of'),
        'monthOfYear': genFeatureObj(True, 'of'),
        'stock': {
            'open': genFeatureObj(True, 'key'),
            'high': genFeatureObj(True, 'key'),
            'low': genFeatureObj(True, 'key'),
            'close': genFeatureObj(True, 'key'),
            'volume': genFeatureObj(True, 'key')
        },
        'vix': {
            'open': genFeatureObj(True, 'vixkey'),
            'high': genFeatureObj(True, 'vixkey'),
            'low': genFeatureObj(True, 'vixkey'),
            'close': genFeatureObj(True, 'vixkey')
        },
        'financials': {
            'enabled': False,
            'extype': 'financials',
            'dataRequired': True,
            
            'includeDates': True,
            'maxTierIndex': 1,
            'tierTags': [
                ['Assets', 'Liabilities', 'StockholdersEquity']
            ],
        },
        'googleInterests': genFeatureObj(False, 'interest')
    },

    'testing': {
        'enabled': TESTING,
        'exchange': 'NYSE',
        'stockQueryLimit': 50
    },

    'training': trainingConfig
})
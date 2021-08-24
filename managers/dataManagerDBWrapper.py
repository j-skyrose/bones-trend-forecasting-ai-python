import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import random, math, numpy, tqdm, time, pickle
from tensorflow import keras
from timeit import default_timer as timer
from datetime import date
from typing import List

from globalConfig import config as gconfig
from constants.enums import SeriesType, SetType
from utils.support import Singleton, flatten, recdotdict, recdotlist, shortc, multicore_poolIMap, processDBQuartersToDicts
from constants.values import testingSymbols, unusableSymbols
# from managers.stockDataManager import StockDataManager
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.vixManager import VIXManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.financialDataHandler import FinancialDataHandler
from structures.stockDataHandler import StockDataHandler
from structures.dataPointInstance import DataPointInstance, numOutputClasses, positiveClass, negativeClass
from structures.api.googleTrends.request import GoogleAPI



from tensorflow.keras.optimizers import Adam
from managers.neuralNetworkManager import NeuralNetworkManager
nnm: NeuralNetworkManager = NeuralNetworkManager()

DEBUG = True
dbm: DatabaseManager = DatabaseManager()

class DataManagerDBWrapper():
    vixm: VIXManager = VIXManager()
    dm: DataManager = None

    def __init__(self, **kwargs):
        self.dm = DataManager(dbm, self.vixm.data, **kwargs)
        # self.dm = DataManager(None, self.vixm.data, **kwargs)
        # self.dm = DataManager(None, [], **kwargs)

    @classmethod
    def forTraining(cls, seriesType=SeriesType.DAILY, **kwargs):
        normalizationColumns, normalizationMaxes, symbolList = dbm.getNormalizationData(seriesType)
        
        normalizationInfo = {}
        for c in range(len(normalizationColumns)):
            normalizationInfo[normalizationColumns[c]] = normalizationMaxes[c]
        
        return cls(
            seriesType=seriesType,
            normalizationInfo=normalizationInfo, symbolList=symbolList, 
            **kwargs
        )

    @classmethod
    def forAnalysis(cls, nn: NeuralNetworkInstance, **kwargs):
        normalizationInfo = nn.stats.getNormalizationInfo()
        _, _, symbolList = dbm.getNormalizationData(nn.stats.seriesType, normalizationInfo=normalizationInfo, **kwargs) #exchanges=exchanges, excludeExchanges=excludeExchanges, sectors=sectors, excludeSectors=excludeSectors)

        return cls(
            precedingRange=nn.stats.precedingRange, followingRange=nn.stats.followingRange, seriesType=nn.stats.seriesType, threshold=nn.stats.changeThreshold, inputVectorFactory=nn.inputVectorFactory,
            normalizationInfo=normalizationInfo, symbolList=symbolList,
            analysis=True,
            **kwargs
        )

    def setupSetsFromSave(self, id, setid=1):
        self.dm.setupSetsFromSave(dbm, id, setid)

    def save(self, networkId, setId=None):
        self.dm.save(dbm, networkId, setId)


if __name__ == '__main__':
    precrange = 202
    folrange = 20
    threshold = 0.05
    setSplitTuple = (0.80,0.20)

    if gconfig.testing.enabled:
        ## testing
        setCount = 250
        minimumSetsPerSymbol = 0
    else:
        ## real
        setCount = 150000
        minimumSetsPerSymbol = 10

    ## network
    inputSize = InputVectorFactory().getInputSize(precrange)
    optimizer = Adam(amsgrad=True)
    layers = [
        { 'units': math.floor(inputSize / 1.5), 'dropout': False, 'dropoutRate': 0.001 },
    ]

    s = DataManagerDBWrapper.forTraining(
        network=nnm.createNetworkInstance(
            optimizer, layers, inputSize
        ),
        precedingRange=precrange, 
        followingRange=folrange,
        threshold=threshold,
        setCount=setCount,
        setSplitTuple=setSplitTuple,
        minimumSetsPerSymbol=minimumSetsPerSymbol
    )
    
    pickle.dumps(s.dm)

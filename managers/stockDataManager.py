
import os, sys
from structures.financialDataHandler import FinancialDataHandler
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
from multiprocessing import Pool, cpu_count
from datetime import date
from typing import Dict, List

from globalConfig import config as gconfig
from constants.enums import OutputClass, SeriesType, SetType
from utils.support import Singleton, recdotdict, shortc
from constants.values import testingSymbols, unusableSymbols
from managers.databaseManager import DatabaseManager
from managers.vixManager import VIXManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.stockDataHandler import StockDataHandler
from structures.dataPointInstance import DataPointInstance
from structures.api.googleTrends.request import GoogleAPI

DEBUG = True
MULTITHREAD = False

dbm: DatabaseManager = DatabaseManager()

def setupHandlerWorker(
    processid, 
    symbolList: List[dict], 
    seriesType: SeriesType, 
    normalizationInfo: dict, 
    precedingRange: int, 
    followingRange: int
):
    # try:
        normalizationMaxes = [x for x in normalizationInfo.values()]
        handlers = {}
        for s in tqdm.tqdm(symbolList, desc='Creating handlers') if processid == 0 else symbolList:   
            if (s.exchange, s.symbol) in testingSymbols + unusableSymbols: continue
            data = dbm.getStockData(s.exchange, s.symbol, seriesType)
            if len(data) >= precedingRange + followingRange + 1:
                handlers[(s.exchange, s.symbol)] = StockDataHandler(
                    s,
                    seriesType,
                    data,
                    *normalizationMaxes,
                    precedingRange,
                    followingRange
                )
        return handlers
    # except:
    #     print("Unexpected error:", sys.exc_info()[0])

class StockDataManager(Singleton):
    handlers = {}
    normalizationInfo = {}
    precedingRange = 0
    followingRange = 0
    seriesType = None
    instances = {}
    inputVectorFactory: InputVectorFactory = None
    threshold = 0
    vixManager: VIXManager = VIXManager()

    def __init__(self, normalizationInfo, symbolList, precedingRange, followingRange, seriesType, inputVectorFactory, threshold) -> None:
        super().__init__()
        self.normalizationInfo = normalizationInfo
        self.precedingRange = precedingRange
        self.followingRange = followingRange
        self.seriesType = seriesType
        self.inputVectorFactory = inputVectorFactory
        self.threshold = threshold

        ## initialize handlers
        if MULTITHREAD:
            ### multi-process setup of handlers, appears to get stuck once all processes are complete and starts chugging CPU, taking same or more time as sequential. Does not run
            ## also needs to be modified to add to handlers as a dict
            # s = timer()
            # with Pool() as pool:
            #     self.handlers = pool.starmap(setupHandlerWorker, [
            #             (
            #                 i,
            #                 self.symbolList[i::cpu_count()],
            #                 self.seriesType,
            #                 normalizationMaxes,
            #                 self.precedingRange,
            #                 self.followingRange,
            #                 # 3
            #             ) for i in range(cpu_count())
            #         ])
            # self.handlers = [i for sublist in self.handlers for i in sublist]    # flatten back into a single list
            # e = timer()
            # if DEBUG: print(len(self.handlers), f'handlers setup in {e-s} seconds')
            pass
        else:
            self.handlers = setupHandlerWorker(0, symbolList, self.seriesType, self.normalizationInfo, self.precedingRange, self.followingRange)

        if DEBUG: print(len(self.handlers), 'handlers setup')

        ## initialize instances
        self.__extendInstances(self.getAll())

    def __extendInstances(self, handlers):
        for h in tqdm.tqdm(handlers, desc='Initializing instances'):
            self.__initializeInstances(h)

    def __initializeInstances(self, h: StockDataHandler, f: FinancialDataHandler):
        for s in h.getAvailableSelections():
            self.instances[(h.symbolData.exchange, h.symbolData.symbol, h.data[s].date)] = self.__buildInstance(h, s, f)

    def __buildInstance(self, stockDataHandler, stockDataIndex, financialDataHandler):
        d = stockDataHandler.data
        try:
            change = (d[stockDataIndex + self.followingRange].low / d[stockDataIndex - 1].high) - 1
        except ZeroDivisionError:
            change = 0

        return DataPointInstance(shortc(self.inputVectorFactory, InputVectorFactory()), stockDataHandler, stockDataIndex, self.vixManager, financialDataHandler,
            OutputClass.POSITIVE if change >= self.threshold else OutputClass.NEGATIVE
        )


    def get(self, exchange, symbol) -> StockDataHandler:
        try:
            return self.handlers[(exchange, symbol)]
        except KeyError:
            self.extend(exchange=exchange, symbol=symbol)
            return self.handlers[(exchange, symbol)]
    
    def getAll(self):
        return self.handlers.values()

    def extend(self, symbolList=[], exchange=None, symbol=None):
        newHandlers = setupHandlerWorker(0, symbolList if symbolList else [{ exchange: exchange, symbol: symbol }], self.seriesType, self.normalizationInfo, self.precedingRange, self.followingRange)
        self.handlers = {**newHandlers, **self.handlers}
        self.__extendInstances(newHandlers)

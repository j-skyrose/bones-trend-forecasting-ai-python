import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.enums import OutputClass
from structures.stockDataHandler import StockDataHandler
from utils.other import denormalizeValue
from utils.support import GetMemoryUsage

class DataPointInstance(GetMemoryUsage):
    ## index is the anchor point, between preceding and following, so total length will always be +1
    def __init__(self, buildInputVectorFunc, stockDataHandler, index, outputClass):
        self.buildInputVectorFunc = buildInputVectorFunc
        self.stockDataHandler: StockDataHandler = stockDataHandler
        self.index = index
        self.outputClass = outputClass

    def getAnchorDay(self):
        '''returns the full dict for the anchor day (i.e. stockDataHandler[index])'''
        return self.stockDataHandler.data[self.index]

    def getInputVector(self):
        return self.buildInputVectorFunc(self.stockDataHandler, self.index)

    def getOutputVector(self):
        return 0 if self.outputClass == OutputClass.NEGATIVE else 1
    
    def print(self):
        fromValue = self.stockDataHandler.data[self.index].close
        toValue = self.stockDataHandler.data[self.index + self.stockDataHandler.followingRange].low
        if self.stockDataHandler.normalized:
            fromValue = denormalizeValue(fromValue, self.stockDataHandler.stockPriceNormalizationMax, self.stockDataHandler.dataOffset)
            toValue = denormalizeValue(toValue, self.stockDataHandler.stockPriceNormalizationMax, self.stockDataHandler.dataOffset)
        print(f'{self.outputClass.name} class, price will change from {fromValue:.2f} to {toValue:.2f}')
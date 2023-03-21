import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.enums import OutputClass
from utils.support import GetMemoryUsage
from structures.stockDataHandler import StockDataHandler

class DataPointInstance(GetMemoryUsage):
    ## index is the anchor point, between preceding and following, so total length will always be +1
    def __init__(self, buildInputVectorFunc, stockDataHandler, index, outputClass):
        self.buildInputVectorFunc = buildInputVectorFunc
        self.stockDataHandler: StockDataHandler = stockDataHandler
        self.index = index
        self.outputClass = outputClass

    def getInputVector(self):
        # if self.handler.symbolData.asset_type != 'ETF' and self.handler.symbolData.asset_type != 'ETP':
        #     print('f')
        #     pass
        #     pass
        return self.buildInputVectorFunc(self.stockDataHandler, self.index, self.stockDataHandler.symbolData)

    def getOutputVector(self):
        return 0 if self.outputClass == OutputClass.NEGATIVE else 1
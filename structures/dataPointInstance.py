import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from structures.stockDataHandler import StockDataHandler
from constants.values import interestColumn
from utils.support import shortc


numOutputClasses = 2
positiveClass = 'positiveClass'
negativeClass = 'negativeClass'


class DataPointInstance:
    ## index is the anchor point, between preceding and following, so total length will always be +1
    def __init__(self, buildInputVectorFunc, stockDataHandler, index, outputClass):
        self.buildInputVectorFunc = buildInputVectorFunc
        self.stockDataHandler: StockDataHandler = stockDataHandler
        self.index = index
        self.outputClass = outputClass
        self.googleInterestData = {}

    def getInputVector(self):
        # if self.handler.symbolData.asset_type != 'ETF' and self.handler.symbolData.asset_type != 'ETP':
        #     print('f')
        #     pass
        #     pass
        return self.buildInputVectorFunc(self.stockDataHandler, self.index, self.googleInterestData, self.stockDataHandler.symbolData)

    def getOutputVector(self):
        return 0 if self.outputClass == negativeClass else 1

    def setGoogleInterestData(self, data):
        gdataKeys = [r.strftime('%Y-%m-%d') for r in list(data.to_dict()[interestColumn].keys())]

        ## normalize
        offset = 0.5
        for k in gdataKeys:
            data.at[k, interestColumn] = (data.at[k, interestColumn] / 100) - offset

        self.googleInterestData = data
    
    def getGoogleInterestAt(self, dt):
        return self.googleInterestData.at[dt, interestColumn]
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import copy
from utils.other import normalizeStockData

'''
maintains the time series data from the DB, in normalized and raw forms
also maintains possible selections, and the selected sets as single data points (ie index of the anchor date)
any set builds will need to reference these to get the actual full vectors

data should be in date ascending order, where each item is one row from DB table
'''
class StockDataHandler:
    normalized = False

    def __init__(self, symbolData, seriesType, data, 
    # outputVector, ## todo
    highMax=None, volumeMax=None, precedingRange=None, followingRange=None):
        self.symbolData = symbolData
        self.seriesType = seriesType
        self.data = data
        # self.outputVector = outputVector
        self.selections = []
        self.selected = 0
        self.precedingRange = precedingRange
        self.followingRange = followingRange

        if highMax and volumeMax:
            self.normalize(highMax, volumeMax)
        if precedingRange and followingRange:
            self.determineSelections(precedingRange, followingRange)

    def determineSelections(self, precedingRange, followingRange):
        self.selections = [x for x in range(len(self.data)) if precedingRange <= x and x < len(self.data) - followingRange]
        return self.selections

    def normalize(self, highMax, volumeMax):
        if not self.normalized:
            self.data = normalizeStockData(self.data, highMax, volumeMax)
            self.normalized = True

    def setData(self, data, highMax=None, volumeMax=None, precedingRange=None, followingRange=None):
        self.data = data
        if highMax and volumeMax:
            self.normalize(highMax, volumeMax)
        else:
            self.normalizedData = None
        if precedingRange and followingRange:
            self.determineSelections(precedingRange, followingRange)
        else:
            self.selections = []
        self.selected = set()

    # def select(self, index):
    #     self.selected.add(index)

    def selectOne(self):
        self.selected += 1

    def getSelected(self):
        return self.selected

    def clearSelections(self):
        # self.selected.clear()
        self.selected = 0

    def getAvailableSelections(self):
        # return [x for x in self.selections if x not in list(self.selected)]
        return self.selections

    def getPrecedingSet(self, index):
        return self.data[index-self.precedingRange:index]

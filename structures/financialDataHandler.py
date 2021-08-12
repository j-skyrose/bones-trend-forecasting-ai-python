import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from datetime import timedelta
from utils.other import maxQuarters, normalizeFinancials

class FinancialDataHandler:
    normalized = False

    def __init__(self, symbolData, financialData, generalMax=None):
        self.symbolData = symbolData
        self.data = financialData

        if generalMax:
            self.normalize(generalMax)

    def normalize(self, generalMax):
        if not self.normalized:
            self.data = normalizeFinancials(self.data, generalMax)
            self.normalized = True

    def getPrecedingReports(self, indexDate, precedingRange):
        firstDay = indexDate - timedelta(days=precedingRange+1)
        # ret = []
        # gethering = False
        # for i in reversed(range(len(self.data))):
        #     if not gathering and self.data[i-1]
        firstIndex = 0
        lastIndex = 0
        for i in range(len(self.data)):
            if self.data[i].filed < firstDay: 
                firstIndex = i
            if self.data[i].filed > indexDate: 
                lastIndex = i-1
                break

        if lastIndex - firstIndex > maxQuarters(precedingRange): raise ValueError

        return self.data[firstIndex:lastIndex]

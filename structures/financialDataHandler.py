import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from datetime import timedelta, date
from utils.other import maxQuarters, normalizeFinancials
from utils.support import _edgarformatd

class FinancialDataHandler:
    normalized = False

    def __init__(self, symbolData, financialData, generalMax=1000000):
        self.symbolData = symbolData
        self.data = financialData

        if generalMax:
            self.normalize(generalMax)

    def normalize(self, generalMax):
        if not self.normalized:
            self.data = normalizeFinancials(self.data, generalMax)
            self.normalized = True

    def getPrecedingReports(self, indexDate, precedingRange):
        if indexDate < _edgarformatd(self.data[0].filed): return []

        firstDay = indexDate - timedelta(days=precedingRange+1)
        firstIndex = 0
        lastIndex = 0
        for i in range(len(self.data)):
            if _edgarformatd(self.data[i].filed) < firstDay: 
                firstIndex = i
            if _edgarformatd(self.data[i].filed) > indexDate: 
                lastIndex = i-1
                break

        # if lastIndex - firstIndex > maxQuarters(precedingRange): raise ValueError
        while lastIndex - firstIndex > maxQuarters(precedingRange):
            firstIndex += 1

        return self.data[firstIndex:lastIndex]

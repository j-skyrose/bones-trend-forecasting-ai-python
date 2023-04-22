import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from datetime import date

from globalConfig import config as gconfig
from structures.dailyDataHandler import DailyDataHandler
from utils.support import asMonthKey

## helper for googleInterestsHandler: parses and organizes the raw data into a more accessible form for the purposes of calculating the overall relative interest for each day
class MonthlyGIDataHandler:

    def __init__(self, monthlygdata, ddh: DailyDataHandler) -> None:
        self.data = {}

        ## if no overall data, generate based on stream 0
        if gconfig.testing.enabled and not monthlygdata:
            maxweeksum = 0
            dailyblocks = ddh.getStream(0).blocks
            for wkbl in dailyblocks:
                if wkbl.sum() > maxweeksum: maxweeksum = wkbl.sum()
            for wkbl in dailyblocks:
                for d in wkbl.data.keys():
                    self.setMonthValue(d, wkbl.sum() / maxweeksum * 100)
        else:
            for d in monthlygdata:
                self.setMonthValue(d.date, d.relative_interest)
    
    def hasMonthKey(self, key: date):
        return asMonthKey(key) in self.data.keys()

    def setMonthValue(self, key: date, value):
        self.data[asMonthKey(key)] = value

    def getMonthValue(self, key: date):
        return self.data[asMonthKey(key)]

import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from utils.support import Singleton
from utils.other import normalizeStockData
from constants.values import vixOffset
from managers.databaseManager import DatabaseManager

class VIXManager(Singleton):
    normalized = False
    shouldNormalize = False

    def __init__(self, normalize=False, dataOffset=vixOffset):
        self.shouldNormalize = normalize
        dbm: DatabaseManager = DatabaseManager()
        
        data = dbm.getVIXData()
        self.max = dbm.getVIXMax()
        self.dataOffset = dataOffset

        if self.shouldNormalize:
            data = normalizeStockData(data, self.max, offset=self.dataOffset)
            self.normalized = True

        self.data = {r.date: r for r in data}

    def getData(self) -> dict:
        return self.data

    def getMax(self):
        return self.max
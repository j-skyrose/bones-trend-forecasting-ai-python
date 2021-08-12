import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import List

from utils.support import Singleton, recdotdict
from constants.values import testingSymbols, unusableSymbols, vixOffset
from managers.databaseManager import DatabaseManager

class VIXManager(Singleton):
    def __init__(self):
        dbm: DatabaseManager = DatabaseManager()
        
        data = dbm.getVIXData()

        ## normalize
        self.max = dbm.getVIXMax()
        for d in data:
            d.open = (d.open / self.max) - vixOffset
            d.high = (d.high / self.max) - vixOffset
            d.low = (d.low / self.max) - vixOffset
            d.close = (d.close / self.max) - vixOffset

        self.data = {r.date: r for r in data}

    def getData(self) -> dict:
        return self.data

    def getMax(self):
        return self.max
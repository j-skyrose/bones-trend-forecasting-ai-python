import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import pickle
from utils.support import Singleton
from structures.dbCacheInstance import DBCacheInstance

class DBCacheManager(Singleton):
    def __init__(self, cachePath=os.path.join(path, 'caches\\db')):
        self.cachePath = cachePath
        self.caches = []

        for root, dirs, files in os.walk(self.cachePath):
            for file in files:
                with open(os.path.join(self.cachePath, file), 'rb') as f:
                    self.caches.append(pickle.load(f))

    def addInstance(self, filetag, queryStatement, validationObj, returnValue):
        dc = DBCacheInstance(filetag, queryStatement, validationObj, returnValue)
        self.caches.append(dc)
        with open(os.path.join(self.cachePath, dc.filetag + '=' + dc.getQueryHash() + '.pkl'), 'wb') as f:
            pickle.dump(dc, f, protocol=4)

    def getCache(self, query, validation):
        for c in self.caches:
            if c.test(query, validation):
                return c.returnValue
        return None

        
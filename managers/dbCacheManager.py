import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import pickle
from typing import Dict

from managers.base.cacheManagerBase import CacheManagerBase
from structures.dbCacheInstance import DBCacheInstance
from utils.support import combineSQLStatementAndArguments

class DBCacheManager(CacheManagerBase):
    def __init__(self, folder='db', **kwargs):
        super().__init__(folder=folder, readMode='rb', readFunction=lambda x: pickle.load(x), **kwargs)
        self.caches: Dict[str, DBCacheInstance]

    def add(self, fileTag: str, queryStatement: str, cacheStamp, value, queryArgs=[]):
        '''
            fileTag: str
                prefix string to help classify each cache object file when written to disk
            queryStatement: str
                SQL query string, with or without in-line arguments; used to distinguish queries from each other
            cacheStamp: str, int, date
                used to identify if cache is out of date; should be string-ish comparable
            value: any
                return object
        '''

        ci = DBCacheInstance(fileTag, combineSQLStatementAndArguments(queryStatement, queryArgs), cacheStamp, value)
        fdestpath = os.path.join(self.cachePath, ci.filetag + '=' + ci.getUniqueHash() + '.pkl')
        self._add(fdestpath, ci)
        with open(fdestpath, 'wb') as f:
            pickle.dump(ci, f, protocol=4)

    def get(self, queryStatement, stamp, queryArgs=[]):
        for c in self.caches.values():
            if c.test(combineSQLStatementAndArguments(queryStatement, queryArgs), stamp):
                return c.value
        return None

        
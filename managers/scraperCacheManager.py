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
from structures.webPageCacheInstance import WebPageCacheInstance

class ScraperCacheManager(CacheManagerBase):
    def __init__(self, folder='scraper', **kwargs):
        super().__init__(folder=folder, readMode='rb', readFunction=lambda x: pickle.load(x), **kwargs)
        self.caches: Dict[str, WebPageCacheInstance]

    def add(self, url, content, cacheStamp, params={}, postData=None, headers={}):
        ci = WebPageCacheInstance(url, content, cacheStamp, params=params, postData=postData, headers=headers)
        fdestpath = os.path.join(self.cachePath, f'{ci.fileTag}={ci.getUniqueHash()}.pkl')
        self._add(fdestpath, ci)
        with open(fdestpath, 'wb') as f:
            pickle.dump(ci, f, protocol=4)

    def get(self, url, cacheStamp, **kwargs):
        for c in self.caches.values():
            if c.test(url, cacheStamp=cacheStamp, **kwargs):
                return c.value
        return None

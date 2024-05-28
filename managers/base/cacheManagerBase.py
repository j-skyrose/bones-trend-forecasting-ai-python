import os, sys
from typing import Union
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import pickle
from io import BufferedReader

from utils.support import Singleton, shortc

class CacheManagerBase(Singleton):
    def __init__(self, cachePath=os.path.join(path, 'caches'), folder='', readMode='r', keyFunction=None, readFunction=None):
        self.__key = shortc(keyFunction, self.__key, eCanBeenCalledForValue=False)
        self.__read = shortc(readFunction, self.__read, eCanBeenCalledForValue=False)
        self.cachePath = os.path.join(cachePath, folder)
        self.caches = {}

        for root, dirs, files in os.walk(self.cachePath):
            for file in files:
                with open(os.path.join(self.cachePath, file), readMode) as f:
                    self.caches[self.__key(f)] = self.__read(f)

    def __key(self, f: Union[str, BufferedReader]):
        if type(f) is BufferedReader: f = f.name
        ## essentially gets full file name, minus extension and preceding path
        return '.'.join(f.split('\\')[-1].split('.')[:-1])
    
    def __read(self, f: BufferedReader):
        return f
    
    def _add(self, key, val):
        self.caches[self.__key(key)] = val

    def add(self, *args, **kwargs):
        raise NotImplementedError()
    
    def get(self, *args, **kwargs):
        raise NotImplementedError()

if __name__ == '__main__':
    print(os.path.join(path, ''))
    print(path)
    cm: CacheManagerBase = CacheManagerBase(folder='db', readMode='rb', readFunction=lambda x: pickle.load(x))
    print(len(cm.caches))
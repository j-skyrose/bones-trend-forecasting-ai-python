import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from utils.support import Singleton

class StatsManager(Singleton):
    ## makes the object subscriptable
    def __getitem__(self, key):
        return getattr(self, key)

    def __getattr__(self, item):
        try:
            return self.__dict__[item]
        except KeyError:
            # print('keyerror',item)
            # raise AttributeError(item)
            setattr(self, item, 0)
            return 0

    def __init__(self):
        pass

    def printAll(self):
        for a in dir(self):
            if a.startswith('__'): continue
            print(a, self[a])
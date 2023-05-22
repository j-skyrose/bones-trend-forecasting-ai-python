import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import Any
import types
from utils.support import recdotdict
from constants.enums import SeriesType, AccuracyType


class NetworkStats:
    id = None
    changeThreshold = None
    precedingRange = None
    followingRange = None
    seriesType: SeriesType = None
    accuracyType: AccuracyType = None

    highMax = None
    volumeMax = None

    overallAccuracy = 0
    negativeAccuracy = 0
    positiveAccuracy = 0
    epochs = 0

    def __init__(self, id, threshold=None, precedingRange=None, followingRange=None, seriesType: SeriesType=None, accuracyType=None):
        self.id = id
        self.changeThreshold = threshold
        self.precedingRange = precedingRange
        self.followingRange = followingRange
        self.seriesType = seriesType
        self.accuracyType = accuracyType

        # self.overallAccuracy = 0
        # self.negativeAccuracy = 0
        # self.positiveAccuracy = 0
        # self.epochs = 0
        # self.stats = {}

    @classmethod
    def importFrom(cls, statsObj):
        c = cls(statsObj.id)
        for k,v in statsObj.items():
            # if 'Max' in k:
            #     # c.setMax(k, v))
            #     setattr(c, k, v)
            if hasattr(c, k):
                setattr(c, k, v)
        return c

    def setMax(self, label: str, value):
        # if 'Max' in label:
        #     label = label.replace('Max', '')
        setattr(self, label + 'Max', value)

    ## makes the object subscriptable
    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == 'seriesType':
            super(NetworkStats, self).__setattr__(name, SeriesType[value] if type(value) is str else value)
        elif name == 'accuracyType':
            super(NetworkStats, self).__setattr__(name, AccuracyType[value] if type(value) is str else value)
        else:
            super(NetworkStats, self).__setattr__(name, value)

    def getNormalizationInfo(self):
        ret = {}
        for k in dir(self):
            if 'Max' in k:
                val = getattr(self, k)
                if not isinstance(val, types.MethodType):
                    ret[k] = val
        return recdotdict(ret)

if __name__ == '__main__':
    ## testing
    n = NetworkStats(2, 2, seriesType=SeriesType.DAILY)
    print(n.id, n.seriesType)
    n.setMax('test', 3)
    print(n.testMax)
    n.accuracyType = 'COMBINED'
    print(n.accuracyType)

    print(n.getNormalizationInfo())

    n = NetworkStats.importFrom(recdotdict({'id': 2, 'overallAccuracy': 5}))
    print(n.overallAccuracy, n.accuracyType)
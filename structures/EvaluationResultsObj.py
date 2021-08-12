import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tensorflow as tf
from structures.evaluateObj import EvaluateObj
from constants.enums import AccuracyType, LossAccuracy
from utils.support import recdotdict

class EvaluationResultsObj:
    # AccuracyType.OVERALL = None
    # AccuracyType.POSITIVE = None
    # AccuracyType.NEGATIVE = None
    # AccuracyType.COMBINED = None

    def __getitem__(self, key: AccuracyType) -> EvaluateObj:
        try:
            return getattr(self, key.name)
        except KeyError:
            raise AttributeError(key)

    def __setitem__(self, key, value):
        setattr(self, key.name, value)
        try:
            setattr(self, AccuracyType.COMBINED.name, EvaluateObj(
                self[AccuracyType.POSITIVE][LossAccuracy.LOSS] + self[AccuracyType.NEGATIVE][LossAccuracy.LOSS],
                self[AccuracyType.POSITIVE][LossAccuracy.ACCURACY] + self[AccuracyType.NEGATIVE][LossAccuracy.ACCURACY]
            ))
        except:
            pass    

    def availableAccuracyTypes(self):
        return [x for x in self.keys() if self[x]]

    def accuracyTypesCount(self):
        return len(self.availableAccuracyTypes())

if __name__ == '__main__':
    ## testing
    v = EvaluationResultsObj()
    v[AccuracyType.POSITIVE] = EvaluateObj(1, 2)
    v[AccuracyType.NEGATIVE] = EvaluateObj(2, 3)
    print(v[AccuracyType.COMBINED][LossAccuracy.LOSS])
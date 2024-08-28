import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tensorflow as tf
from tensorflow import keras
from keras import Model
from typing import Dict

from constants.enums import AccuracyType
from utils.support import getMetricsNames

class EvaluationDataHandler:

    def __init__(self, overallValidationSet=None, positiveValidationSet=None, negativeValidationSet=None):
        self.internal = {}
        if overallValidationSet:
            self.internal[AccuracyType.OVERALL] = overallValidationSet
        if positiveValidationSet:
            self.internal[AccuracyType.POSITIVE] = positiveValidationSet
        if negativeValidationSet:
            self.internal[AccuracyType.NEGATIVE] = negativeValidationSet

    def __getitem__(self, key):
        try:
            return self.internal[key]
        except KeyError:
            raise AttributeError(key)

    def __setitem__(self, key, value):
        if value:
            self.internal[key] = value

    def _getSets(self, index):
        return [x[index] for x in self.internal.values()]

    def availableAccuracyTypes(self):
        return self.internal.keys()
    
    def getInputSets(self):
        return self._getSets(0)

    def getOutputSets(self):
        return self._getSets(1)

    def accuracyTypesCount(self):
        return len(self.internal.keys())

    def getAccuracyType(self, index):
        return self.internal.keys()[index]

    def getTuple(self, key):
        return (self.internal[key][0], self.internal[key][1])

    def _getXYSets(self, accuracyType):
        xset, yset = self.internal[accuracyType]
        if len(xset) == 1:
            xset = xset[0]
        elif len(xset[0]) == 1:
            xset = xset[0][0]
        return xset, yset

    def evaluateAll(self, model: Model, timeWeighted=False, **kwargs) -> Dict:
        xset, yset = self._getXYSets(AccuracyType.OVERALL)
        evaluateResults = model.evaluate(xset, yset, **kwargs)
        returnMetrics = {
            k: v for k,v in zip(getMetricsNames(model), evaluateResults)
        }
        for accuracyType in [AccuracyType.POSITIVE, AccuracyType.NEGATIVE]:
            if accuracyType in self.availableAccuracyTypes():
                xset, yset = self._getXYSets(accuracyType)
                accEvaluateResults = model.evaluate(xset, yset, **kwargs)
                returnMetrics[accuracyType.statsName] = accEvaluateResults[1]

        return returnMetrics

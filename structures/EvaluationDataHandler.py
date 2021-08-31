import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from utils.support import recdotdict
import tensorflow as tf
from constants.enums import AccuracyType, LossAccuracy
from structures.EvaluationResultsObj import EvaluationResultsObj
from structures.evaluateObj import EvaluateObj

class EvaluationDataHandler:
    internal = {}

    def __init__(self, validationSet, negativeValidationSet=None, positiveValidationSet=None):
        if positiveValidationSet:
            self.internal[AccuracyType.POSITIVE] = positiveValidationSet
        if negativeValidationSet:
            self.internal[AccuracyType.NEGATIVE] = negativeValidationSet
        self.internal[AccuracyType.OVERALL] = validationSet

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

    def evaluateAll(self, model: tf.keras.Model, **kwargs) -> EvaluationResultsObj:
        # for s in range(len(inputVectorSets)):
        #     if len(inputVectorSets[s]) > 0:
        #         l, a = self.model.evaluate(inputVectorSets[s], outputVectorSets[s], **kwargs)
        #         losses.append(l)
        #         accuracies.append(a)

        res = EvaluationResultsObj()
        for act in self.availableAccuracyTypes():
            vset = self.internal[act]
            if len(vset) > 0:
                # l, a = model.evaluate(vset[0], vset[1], **kwargs)
                # ret[act] = {
                #     LossAccuracy.LOSS: l,
                #     LossAccuracy.ACCURACY: a
                # }
                res[act] = EvaluateObj(*model.evaluate(vset[0], vset[1], **kwargs))
        
        # ret[AccuracyType.COMBINED] = {
        #     LossAccuracy.LOSS: ret[AccuracyType.POSITIVE][LossAccuracy.LOSS] + ret[AccuracyType.NEGATIVE][LossAccuracy.LOSS],
        #     LossAccuracy.ACCURACY: ret[AccuracyType.POSITIVE][LossAccuracy.ACCURACY] + ret[AccuracyType.NEGATIVE][LossAccuracy.ACCURACY]
        # }

        return res
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

    def __init__(self, overallValidationSet=None, positiveValidationSet=None, negativeValidationSet=None):
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

    def evaluateAll(self, model: tf.keras.Model, timeWeighted=False, **kwargs) -> EvaluationResultsObj:
        DEBUG = False
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
                if not timeWeighted:
                    res[act] = EvaluateObj(*model.evaluate(vset[0], vset[1], **kwargs))
                    # nottimeweighted = EvaluateObj(*model.evaluate(vset[0], vset[1], **kwargs))
                else:
                    runningLoss = 0
                    runningAccuracy = 0
                    runningDenominator = 0

                    scce_pred = model.predict(vset[0])
                    if DEBUG: print(scce_pred)
                    scce = tf.keras.losses.binary_crossentropy(vset[1], scce_pred)
                    scca = tf.keras.metrics.sparse_categorical_accuracy(vset[1], scce_pred)
                    if DEBUG: print(scce)
                    if DEBUG: print(scca)
                    loss = tf.reduce_mean(scce)
                    accuracy = tf.reduce_mean(scca)
                    if DEBUG: print(loss)
                    if DEBUG: print(accuracy)
                    for x in range(len(vset[0])):
                        weight = 1 / len(vset[0]) * (x+1)
                        runningLoss += scce[x] * weight
                        runningAccuracy += scca[x] * weight
                        runningDenominator += weight

                    res[act] = EvaluateObj(float(runningLoss / runningDenominator), float(runningAccuracy / runningDenominator))
                    # timeweighted = EvaluateObj(runningLoss / runningDenominator, runningAccuracy / runningDenominator)

                    # print(act)
                    # print('timewighted', timeweighted)
                    # print('unweighted', nottimeweighted)

        
        # ret[AccuracyType.COMBINED] = {
        #     LossAccuracy.LOSS: ret[AccuracyType.POSITIVE][LossAccuracy.LOSS] + ret[AccuracyType.NEGATIVE][LossAccuracy.LOSS],
        #     LossAccuracy.ACCURACY: ret[AccuracyType.POSITIVE][LossAccuracy.ACCURACY] + ret[AccuracyType.NEGATIVE][LossAccuracy.ACCURACY]
        # }

        return res
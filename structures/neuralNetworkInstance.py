import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, importlib
# from keras import backend as K
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Activation, AlphaDropout
from tensorflow.keras.optimizers import SGD, Nadam, Adam
from typing import Dict

from structures.networkStats import NetworkStats
from structures.EvaluationResultsObj import EvaluationResultsObj
from constants.exceptions import LocationNotSpecificed
from constants.enums import AccuracyType, LossAccuracy, SeriesType
from utils.support import recdotdict, shortc
from managers.inputVectorFactory import InputVectorFactory
from structures.EvaluationDataHandler import EvaluationDataHandler
from globalConfig import config as gconfig

useMainGPU = True
try: useMainGPU
except NameError: useMainGPU = False

# -1 - integrated
# 0 - 960
# 1 - 750 Ti
os.environ["CUDA_VISIBLE_DEVICES"]= "0" if useMainGPU else "1"

# 5 allows for 750 Ti; default 8
os.environ["TF_MIN_GPU_MULTIPROCESSOR_COUNT"]= "8" if useMainGPU else "5"

# print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
# from tensorflow.python.client import device_lib
# print(device_lib.list_local_devices())
# print(sys.version)
# print(tf.__version__)
# tf.test.gpu_device_name()
# sess = tf.Session(config=tf.ConfigProto(log_device_placement=True))


class NeuralNetworkInstance:
    model: tf.keras.Model = None
    updated = False
    defaultInputVectorFactory = True
    inputVectorFactory: InputVectorFactory = None
    filepath = None
    stats: NetworkStats = None
    id = None

    def __init__(self, model: tf.keras.Model, inputVectorFactory, filepath, stats):
        self.model = model
        if inputVectorFactory:
            self.inputVectorFactory = inputVectorFactory
            self.defaultInputVectorFactory = False
        else:
            self.inputVectorFactory = InputVectorFactory()
        self.filepath = filepath
        self.stats = stats
        self.id = stats.id

    @classmethod
    def new(
        cls, id, optimizer, layers, inputSize,
        threshold=0, precedingRange=1, followingRange=1, seriesType=SeriesType.DAILY, highMax=0, volumeMax=0, accuracyType=AccuracyType.OVERALL
    ):
        model = Sequential()

        model.add(Dense(int(layers[0]['units']),
                # activation=layers[0]['activation'],
                activation='selu',
                input_dim=inputSize,
                kernel_initializer='lecun_normal'))
        for l in layers[1:]:
            model.add(Dense(int(l['units']),
                            # activation=l['activation']),
                            activation='selu',
                            kernel_initializer='lecun_normal'))
            if l['dropout']:
                # model.add(Dropout(l['dropoutRate']))
                model.add(AlphaDropout(l['dropoutRate']))
        model.add(Dense(2, activation='softmax'))

        model.compile(loss='categorical_crossentropy',
                    # optimizer=SGD(optimizer['learningRate'], optimizer['momentum'], optimizer['decay'], optimizer['nesterov']),
                    optimizer=optimizer, ## Adam(amsgrad=True)
                    metrics=['accuracy'])

        ## initialize stats
        stats = NetworkStats(id, threshold, precedingRange, followingRange, seriesType, accuracyType)
        stats.setMax('high', highMax)
        stats.setMax('volume', volumeMax)
        # stats = {'id': id}        
        # stats['changeThreshold'] = threshold
        # stats['precedingRange'] = precedingRange
        # stats['followingRange'] = followingRange
        # stats['seriesType'] = SeriesType[seriesType] if type(seriesType) is str else seriesType
        # stats['highMax']= highMax
        # stats['volumeMax'] = volumeMax
        # stats['accuracyType'] = AccuracyType[accuracyType] if type(accuracyType) is str else accuracyType

        # ## base
        # stats['overallAccuracy'] = 0
        # stats['negativeAccuracy'] = 0
        # stats['positiveAccuracy'] = 0
        # stats['combinedAccuracy'] = 0
        # stats['epochs'] = 0
        # stats = recdotdict(stats)

        return cls(model, None, None, stats)

    @classmethod
    def fromSave(cls, factoryFile, factoryConfig, modelpath, stats):
        folder = '_dynamicallyLoadedFactories'
        id = str(stats.id)
        with open(os.path.join(path, 'managers', folder, id) + '.py', 'wb') as f:
            f.write(factoryFile)
        factory = importlib.import_module('managers.' + folder + '.' + id).InputVectorFactory

        return cls(keras.models.load_model(modelpath), factory(factoryConfig), modelpath, NetworkStats.importFrom(stats))

    def updateStats(self, threshold=0, precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, highMax=0, volumeMax=0, accuracyType=AccuracyType.OVERALL, normalizationInfo=None, **kwargs):
        if threshold:       self.stats.changeThreshold = threshold
        if precedingRange:  self.stats.precedingRange = precedingRange
        if followingRange:  self.stats.followingRange = followingRange
        if seriesType:      self.stats.seriesType = seriesType
        if accuracyType:    self.stats.accuracyType = accuracyType

        print('updating norm stats')
        print(normalizationInfo)
        if normalizationInfo:
            print(normalizationInfo.items())
            for k, v in normalizationInfo.items():
                print(k, v)
                self.stats.setMax(k, v)
        else:
            if highMax: self.stats.highMax= highMax
            if volumeMax: self.stats.volumeMax = volumeMax            

    def save(self, path=None):
        if not self.filepath and not path:
            raise LocationNotSpecificed
        if path:
            self.model.save(path)
            self.filepath = path
        else:
            self.model.save(self.filepath)

    def reload(self):
        self.model = keras.models.load_model(self.filepath)

    def fit(self, inputVectors, outputVectors, **kwargs):
        # self.model.fit(inputVectors, outputVectors, **kwargs)
        # print(len(inputVectors), inputVectors[0])
        # print(len(outputVectors), outputVectors[0])
        self.model.fit(inputVectors, outputVectors, **kwargs)
        if kwargs['epochs']:
            self.stats.epochs += kwargs['epochs']
    
    def evaluate(self, evaluationDataHandler: EvaluationDataHandler, **kwargs) -> EvaluationResultsObj:
        # if len(inputVectorSets) != 3: raise IndexError
        print('Evaluating...')
        # losses = []
        # accuracies = []
        # for s in range(len(inputVectorSets)):
        #     if len(inputVectorSets[s]) > 0:
        #         l, a = self.model.evaluate(inputVectorSets[s], outputVectorSets[s], **kwargs)
        #         losses.append(l)
        #         accuracies.append(a)
        
        results = evaluationDataHandler.evaluateAll(self.model, **kwargs)

        if evaluationDataHandler.accuracyTypesCount() == 3:
            ## update stats
            # if (
            #     (self.stats.accuracyType == AccuracyType.OVERALL and accuracies[0] > self.stats.overallAccuracy) or
            #     (self.stats.accuracyType == AccuracyType.POSITIVE and accuracies[1] > self.stats.positiveAccuracy) or
            #     (self.stats.accuracyType == AccuracyType.NEGATIVE and accuracies[2] > self.stats.negativeAccuracy) or
            #     (self.stats.accuracyType == AccuracyType.COMBINED and accuracies[1] + accuracies[2] > self.stats.combinedAccuracy)
            # ):
            #     self.stats.overallAccuracy = accuracies[0]
            #     self.stats.positiveAccuracy = accuracies[1]
            #     self.stats.negativeAccuracy = accuracies[2]
            #     self.stats.combinedAccuracy = accuracies[1] + accuracies[2]

            if results[self.stats.accuracyType][LossAccuracy.ACCURACY] > self.stats[self.stats.accuracyType.statsName]:
                self.stats.overallAccuracy = results[AccuracyType.OVERALL][LossAccuracy.ACCURACY]
                self.stats.positiveAccuracy = results[AccuracyType.POSITIVE][LossAccuracy.ACCURACY]
                self.stats.negativeAccuracy = results[AccuracyType.NEGATIVE][LossAccuracy.ACCURACY]
                self.stats.combinedAccuracy = results[AccuracyType.COMBINED][LossAccuracy.ACCURACY]

                self.printAccuracyStats()
        
        self.updated = True

        return results

    def predict(self, inputData, **kwargs):
        inputData = inputData.reshape(-1, inputData.size)
        return numpy.argmax(self.model.predict(inputData, **kwargs), axis=None, out=None)

    def printAccuracyStats(self):
        print('Positive accuracy: {}\nNegative accuracy: {}\nOverall accuracy: {}\n'.format(
            self.stats.positiveAccuracy, self.stats.negativeAccuracy, self.stats.overallAccuracy
        ))

if __name__ == '__main__':
    inp = numpy.array([[0,1],[1,0]])
    oup = keras.utils.to_categorical([0,1], num_classes=2)
    n = NeuralNetworkInstance.new(
        '1',
        Adam(amsgrad=True),
        [
            { 'units': 100, 'dropout': False, 'dropoutRate':0.001 },
            # { 'units': 250, 'dropout': True, 'dropoutRate':0.005 },
            # { 'units': 200, 'dropout': True, 'dropoutRate':0.0025 },
            # { 'units': 100, 'dropout': False, 'dropoutRate':0.0025 }
        ],
        2
    )

    n.fit(inp, oup, epochs=5, batch_size=1, verbose=1)
    # n.evaluate([inp, inp, inp], [oup, oup, oup], batch_size=1, verbose=1)
    print(numpy.argmax(n.predict(inp[0]), axis=None, out=None))
    print(n.predict(inp[0]))
    print(numpy.argmax(n.predict(inp[1]), axis=None, out=None))
    print(n.predict(inp[1]))
    n.printAccuracyStats()
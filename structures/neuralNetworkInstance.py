import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, importlib, gc, time
# from keras import backend as K
import tensorflow as tf
from keras import backend as K
from tensorflow.keras import utils as kutils, Model
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, Activation, AlphaDropout, GRU, Input, Flatten, Concatenate
from tensorflow.keras.optimizers import SGD, Nadam, Adam
from typing import Dict

from structures.networkStats import NetworkStats
from structures.EvaluationResultsObj import EvaluationResultsObj
from constants.exceptions import LocationNotSpecificed
from constants.enums import AccuracyType, DataFormType, LossAccuracy, SeriesType
from utils.support import recdotdict, shortc
from utils.other import maxQuarters
from managers.inputVectorFactory import InputVectorFactory
from structures.EvaluationDataHandler import EvaluationDataHandler
from globalConfig import config as gconfig


# -1 - integrated
# 0 - 960
# 1 - 750 Ti
os.environ["CUDA_VISIBLE_DEVICES"]= ("0" if gconfig.useMainGPU else "1") if gconfig.useGPU else "-1"

# 5 allows for 750 Ti; default 8
os.environ["TF_MIN_GPU_MULTIPROCESSOR_COUNT"]= "8" if gconfig.useMainGPU else "5"

# might help with memory fragmentation apparently --program fails to run if set
# os.environ["TF_GPU_ALLOCATOR"]= "cuda_malloc_async"

# print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
# from tensorflow.python.client import device_lib
# print(device_lib.list_local_devices())
# print(sys.version)
# print(tf.__version__)
# tf.test.gpu_device_name()
# sess = tf.Session(config=tf.ConfigProto(log_device_placement=True))

## allow keras to use more of the GPU memory, to avoid OOM crashes
gpu_options = tf.compat.v1.GPUOptions(allow_growth=True)
sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(gpu_options=gpu_options))
tf.compat.v1.keras.backend.set_session(sess)


class NeuralNetworkInstance:
    model: Model = None
    updated = False
    defaultInputVectorFactory = True
    inputVectorFactory: InputVectorFactory = None
    filepath = None
    stats: NetworkStats = None
    id = None
    useAllSets = False
    useAllSetsAccumulator = None

    def __init__(self, model: tf.keras.Model=None, inputVectorFactory=None, factoryConfig=gconfig, filepath=None, stats=None, useAllSets=False):
        self.model = model
        if inputVectorFactory:
            self.inputVectorFactory = inputVectorFactory(factoryConfig)
            self.defaultInputVectorFactory = False
        else:
            self.inputVectorFactory = InputVectorFactory()
        self.config = factoryConfig
        self.filepath = filepath
        self.stats = stats
        if stats:
            self.id = stats.id
        self.useAllSets = useAllSets

        self._initializeAccumulatorIfRequired()

    @classmethod
    def new(
        cls, id, optimizer, layers, inputSize,
        threshold=0, precedingRange=1, followingRange=1, seriesType=SeriesType.DAILY, highMax=0, volumeMax=0, accuracyType=AccuracyType.OVERALL, useAllSets=False
    ):

        if gconfig.network.recurrent:
            static_features, semiseries_features, series_features = InputVectorFactory().getInputSize()

            static_input = Input(shape=(static_features,))
            ## todo: add input layer to GRU layer for this, update inputvectorfactory to conform to timeseries and static components, function to determine how many time steps vs features should be given as shape, etc.
            semiseries_input = Input(shape=(maxQuarters(precedingRange), semiseries_features)) 
            series_input = Input(shape=(precedingRange, series_features))

            print('series input', series_input)

            static_x = Dense(
                    int(layers[0][0]['units']),
                    # activation=layers[0]['activation'],
                    activation='selu',
                    # input_dim=inputSize,
                    kernel_initializer='lecun_normal'
            )(static_input)
            semiseries_x = GRU(
                int(layers[1][0]['units']),
                # activation='selu',
                kernel_initializer='lecun_normal'
            )(semiseries_input)
            semiseries_x = Activation('selu')(semiseries_x)
            series_x = GRU(
                int(layers[2][0]['units']),
                # input_shape=inputSize,  ## (time_steps, features) ...i.e. (days, datapoints per day)
                # activation='selu',
                kernel_initializer='lecun_normal'
            )(series_input)
            series_x = Activation('selu')(series_x)

            x_combined = Concatenate()([
                static_x, 
                *([semiseries_x] if gconfig.feature.financials.enabled else []),
                series_x
            ])
            if gconfig.dataForm.outputVector == DataFormType.CATEGORICAL:
                xc_units = 2
                xc_activation = 'softmax'
            else:
                xc_units = 1
                xc_activation = 'sigmoid'

            x_combined = Dense(
                xc_units,
                activation=xc_activation
            )(x_combined)

            model = Model([
                static_input,
                *([semiseries_input] if gconfig.feature.financials.enabled else []),
                series_input
            ], x_combined)

        else:
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

            model.add(
                Dense(2, activation='softmax')
                if gconfig.dataForm.outputVector == DataFormType.CATEGORICAL else
                Dense(1, activation='sigmoid')
            )

        model.compile(
            loss='categorical_crossentropy' if gconfig.dataForm.outputVector == DataFormType.CATEGORICAL else 'binary_crossentropy',
                    # optimizer=SGD(optimizer['learningRate'], optimizer['momentum'], optimizer['decay'], optimizer['nesterov']),
                    optimizer=optimizer, ## Adam(amsgrad=True)
                    metrics=['accuracy'])

        print('Input size:', inputSize)
        model.summary()

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
        # stats['epochs'] = 0
        # stats = recdotdict(stats)

        return cls(model=model, stats=stats, useAllSets=useAllSets)

    @classmethod
    def fromSave(cls, factoryFile, factoryConfig, modelpath, stats, useAllSets=False):
        folder = '_dynamicallyLoadedFactories'
        id = str(stats.id)
        with open(os.path.join(path, 'managers', folder, id) + '.py', 'wb') as f:
            f.write(factoryFile)
        # factory = importlib.import_module('managers.' + folder + '.' + id).InputVectorFactory
        factoryModule = importlib.import_module('managers.' + folder + '.' + id)
        factory = None
        for x in range(6):
            try:
                factory = factoryModule.InputVectorFactory
                break
            except AttributeError:
                time.sleep(1)
        if not factory: factory = factoryModule.InputVectorFactory

        return cls(inputVectorFactory=factory, factoryConfig=factoryConfig, filepath=modelpath, stats=NetworkStats.importFrom(stats), useAllSets=useAllSets)

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

    def load(self):
        K.clear_session()
        gc.collect()
        self.model = load_model(self.filepath)

    def unload(self, save=False):
        if save:
            self.save()
        self.model = None
        K.clear_session()
        gc.collect()

    def _initializeAccumulatorIfRequired(self):
        if not self.useAllSetsAccumulator:
            self.useAllSetsAccumulator = {
                actype: [] for actype in AccuracyType
            }

    def fit(self, inputVectors, outputVectors, **kwargs):
        if not self.model: raise BufferError('Model not loaded')
        
        # self.model.fit(inputVectors, outputVectors, **kwargs)
        # print(len(inputVectors), inputVectors[0])
        # print(len(outputVectors), outputVectors[0])
        hist = self.model.fit(inputVectors, outputVectors, **kwargs)
        if kwargs['epochs']:
            # self.stats.epochs += kwargs['epochs']
            self.stats.epochs += len(hist.epoch)
    
    def evaluate(self, evaluationDataHandler: EvaluationDataHandler, **kwargs) -> EvaluationResultsObj:
        if not self.model: raise BufferError('Model not loaded')

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
            #     (self.stats.accuracyType == AccuracyType.NEGATIVE and accuracies[2] > self.stats.negativeAccuracy)
            # ):
            #     self.stats.overallAccuracy = accuracies[0]
            #     self.stats.positiveAccuracy = accuracies[1]
            #     self.stats.negativeAccuracy = accuracies[2]

            if self.useAllSets:
                self._initializeAccumulatorIfRequired()
                iterationCount = len(self.useAllSetsAccumulator[AccuracyType.OVERALL]) + 1

                for actype in AccuracyType:
                    self.useAllSetsAccumulator[actype].append(results[actype][LossAccuracy.ACCURACY])
                    self.stats.__setattr__(actype.statsName, sum(self.useAllSetsAccumulator[actype]) / iterationCount)

                ## print accumulated accuracy stats
                # print('Iterations: {}\nOverall positive accuracy: {}\nOverall negative accuracy: {}\nOverall overall accuracy: {}\n'.format(
                #     totlength, sum(self.useAllSetsAccumulator[AccuracyType.POSITIVE])/totlength, sum(self.useAllSetsAccumulator[AccuracyType.NEGATIVE])/totlength, sum(self.useAllSetsAccumulator[AccuracyType.OVERALL])/totlength
                # ))
                print('Iterations:', iterationCount)
                

            elif results[self.stats.accuracyType][LossAccuracy.ACCURACY] > self.stats[self.stats.accuracyType.statsName]:
                self.stats.overallAccuracy = results[AccuracyType.OVERALL][LossAccuracy.ACCURACY]
                self.stats.positiveAccuracy = results[AccuracyType.POSITIVE][LossAccuracy.ACCURACY]
                self.stats.negativeAccuracy = results[AccuracyType.NEGATIVE][LossAccuracy.ACCURACY]


            self.printAccuracyStats()
        
        self.updated = True

        return results

    def predict(self, inputData, raw=False, batchInput=False, **kwargs):
        if not self.model: raise BufferError('Model not loaded')

        if not batchInput:
            if gconfig.network.recurrent:
                inputData = numpy.array([inputData])
            else:
                inputData = inputData.reshape(-1, inputData.size)
        
        p = self.model.predict(inputData, **kwargs)
        if batchInput:
            return p
        if self.config.dataForm.outputVector == DataFormType.BINARY:
            r = p if raw else numpy.round(p)
            return r[0][0]
        elif self.config.dataForm.outputVector == DataFormType.CATEGORICAL:
            return numpy.argmax(p, axis=None, out=None)

    def printAccuracyStats(self):
        print('Positive accuracy: {}\nNegative accuracy: {}\nOverall accuracy: {}\n'.format(
            self.stats.positiveAccuracy, self.stats.negativeAccuracy, self.stats.overallAccuracy
        ))

if __name__ == '__main__':
    ## standard neural network
    # inp = numpy.array([[0,1],[1,0]])
    # oup = kutils.to_categorical([0,1], num_classes=2)
    # n = NeuralNetworkInstance.new(
    #     '1',
    #     Adam(amsgrad=True),
    #     [
    #         { 'units': 100, 'dropout': False, 'dropoutRate':0.001 },
    #         # { 'units': 250, 'dropout': True, 'dropoutRate':0.005 },
    #         # { 'units': 200, 'dropout': True, 'dropoutRate':0.0025 },
    #         # { 'units': 100, 'dropout': False, 'dropoutRate':0.0025 }
    #     ],
    #     2
    # )

    # n.fit(inp, oup, epochs=5, batch_size=1, verbose=1)
    # # n.evaluate([inp, inp, inp], [oup, oup, oup], batch_size=1, verbose=1)
    # print(numpy.argmax(n.predict(inp[0]), axis=None, out=None))
    # print(n.predict(inp[0]))
    # print(numpy.argmax(n.predict(inp[1]), axis=None, out=None))
    # print(n.predict(inp[1]))
    # n.printAccuracyStats()

    ## recurrent neural network
    # time_steps = 
    inp = numpy.array([
        [0,1,2,4],[1,0,0,3]
    ])
    ## convert to rnn format
    # yind = np.arange()
    print(inp)
    inp = numpy.reshape(inp, (2, 2, 2)) ## rows, time_steps, features
    print(inp)
    print(inp.shape)
    # oup = kutils.to_categorical([0,1], num_classes=2)
    oup = numpy.array([0,1])
    n = NeuralNetworkInstance.new(
        '1',
        Adam(amsgrad=True),
        [
            { 'units': 100, 'dropout': False, 'dropoutRate':0.001 },
            # { 'units': 250, 'dropout': True, 'dropoutRate':0.005 },
            # { 'units': 200, 'dropout': True, 'dropoutRate':0.0025 },
            # { 'units': 100, 'dropout': False, 'dropoutRate':0.0025 }
        ],
        (2, 2) ## teimsteps, features, 
        # inp.shape
    )

    n.fit(inp, oup, epochs=5, batch_size=1, verbose=1)

    print(inp[0])
    print(inp[0].shape)
    # n.evaluate([inp, inp, inp], [oup, oup, oup], batch_size=1, verbose=1)
    print(numpy.argmax(n.predict(inp[0]), axis=None, out=None))
    # print(n.predict(inp))
    # print(numpy.argmax(n.predict(inp), axis=None, out=None))
    # print(n.predict(inp))
    # n.printAccuracyStats()
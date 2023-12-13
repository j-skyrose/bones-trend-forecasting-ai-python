import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, importlib, gc, time, copy
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
from constants.enums import AccuracyType, ChangeType, DataFormType, LossAccuracy, SeriesType
from utils.support import asBytes, recdotdict, shortc, shortcdict
from utils.other import getCustomAccuracy, maxQuarters
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

## allow keras to use more of the GPU memory, to avoid OOM crashes in theory
# gpu_options = tf.compat.v1.GPUOptions(allow_growth=True)
# sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(gpu_options=gpu_options))
# tf.compat.v1.keras.backend.set_session(sess)


class NeuralNetworkInstance:

    def __init__(self, id=None, model: tf.keras.Model=None, inputVectorFactory: InputVectorFactory=None, factoryConfig=gconfig, filepath=None, stats: NetworkStats=None):
        self.model = model
        if inputVectorFactory:
            self.inputVectorFactory = inputVectorFactory(factoryConfig)
            self.defaultInputVectorFactory = False
        else:
            self.inputVectorFactory = InputVectorFactory()
            self.defaultInputVectorFactory = True
        self.config = factoryConfig
        self.filepath = filepath
        if stats:
            self.id = stats.id
            self.stats = stats
        else:
            self.id = id
            if self.config.network.recurrent: 
                precedingRange = model.input_shape[-1][1] ## last input layer is series one, e.g. [(None, 9), (None, 60, 34)]
            else: ## sequential
                precedingRange = model.input_shape[-1]
            self.stats = NetworkStats(id, precedingRange=precedingRange) 
        self.useAllSets = None
        self.useAllSetsAccumulator = None
        self.reEvaluating = False

        self._initializeAccumulatorIfRequired()

    @classmethod
    def new(
        cls, id, optimizer, layers, precedingRange=1, activation='selu', verbose=1,
        ## sequential only
        inputSize=None
    ):

        def _getActivationString(layer):
            return shortcdict(layer, 'activation', activation)

        if gconfig.network.recurrent:
            static_features, semiseries_features, series_features = InputVectorFactory().getInputSize()

            static_input = Input(shape=(static_features,))
            ## todo: add input layer to GRU layer for this, update inputvectorfactory to conform to timeseries and static components, function to determine how many time steps vs features should be given as shape, etc.
            semiseries_input = Input(shape=(maxQuarters(precedingRange), semiseries_features)) 
            series_input = Input(shape=(precedingRange, series_features))

            if verbose > 0: 
                print('static_features',static_features)
                print('static_input',static_input)
                print('semiseries_features',semiseries_features)
                print('semiseries_input',semiseries_features)
                print('series_features',series_features)
                print('series_input',series_input)

            static_x = Dense(
                    int(layers[0][0]['units']),
                    # activation=layers[0]['activation'],
                    # activation='selu',
                    activation=_getActivationString(layers[0][0]),
                    # input_dim=inputSize,
                    kernel_initializer='lecun_normal'
            )(static_input)
            for l in layers[0][1:]:
                static_x = Dense(
                    int(l['units']),
                    activation=_getActivationString(l),
                    kernel_initializer='lecun_normal'
                )(static_x)

            semiseries_x = GRU(
                int(layers[1][0]['units']),
                # activation='selu',
                kernel_initializer='lecun_normal',
                return_sequences=len(layers[2]) > 1
            )(semiseries_input)
            semiseries_x = Activation(_getActivationString(layers[1][0]))(semiseries_x)
            for l in layers[1][1:]:
                semiseries_x = GRU(
                    int(l['units']),
                    kernel_initializer='lecun_normal'
                )(semiseries_x)
                semiseries_x = Activation(_getActivationString(l))(semiseries_x)

            for indx,l in enumerate(layers[2]):
                series_x = GRU(
                    int(l['units']),
                    # input_shape=inputSize,  ## (time_steps, features) ...i.e. (days, datapoints per day)
                    kernel_initializer='lecun_normal',
                    return_sequences=indx < len(layers[2])-1 ## last does not need to return seq
                )(series_x if indx > 0 else series_input)
                series_x = Activation(_getActivationString(l))(series_x)

            x_combined = Concatenate()([
                static_x, 
                *([semiseries_x] if gconfig.feature.financials.enabled else []),
                series_x
            ])

            for l in layers[3]:
                x_combined = Dense(
                    int(l['units']),
                    activation=_getActivationString(l),
                    kernel_initializer='lecun_normal'
                )(x_combined)

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
                    activation=_getActivationString(layers[0]),
                    input_dim=inputSize,
                    kernel_initializer='lecun_normal'))
            for l in layers[1:]:
                model.add(Dense(int(l['units']),
                                # activation=l['activation']),
                                activation=_getActivationString(l),
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
            loss='categorical_crossentropy' if gconfig.dataForm.outputVector == DataFormType.CATEGORICAL else 
            # 'binary_crossentropy',
            'binary_focal_crossentropy', ## helps to apply a "focal factor" to down-weight easy examples and focus more on hard examples
                    # optimizer=SGD(optimizer['learningRate'], optimizer['momentum'], optimizer['decay'], optimizer['nesterov']),
                    optimizer=optimizer, ## Adam(amsgrad=True)
                    metrics=['accuracy'])

        if verbose > 0: 
            print('Input size:', inputSize)
            model.summary()

        return cls(id=id, model=model)

    @classmethod
    def fromSave(cls, factoryFile, factoryConfig, modelpath, rawDBStats):
        folder = '_dynamicallyLoadedFactories'
        id = str(rawDBStats.id)
        with open(os.path.join(path, 'managers', folder, id) + '.py', 'wb') as f:
            f.write(asBytes(factoryFile))
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

        return cls(inputVectorFactory=factory, factoryConfig=factoryConfig, filepath=modelpath, stats=NetworkStats.importFrom(rawDBStats))

    def updateStats(self, changeValue=None, changeType: ChangeType=None, precedingRange=None, followingRange=None, seriesType: SeriesType=None, accuracyType: AccuracyType=None, normalizationData=None, useAllSets=None, **kwargs):
        for k,v in locals().items():
            if k in ['self', 'kwargs']: continue
            if k is not None:
                if k == 'useAllSets': self.useAllSets = v
                else: setattr(self.stats, k, v)     

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
            self.useAllSetsAccumulator['last'] = {
                actype: 0 for actype in AccuracyType
            }

    def _generateAccuracyStatsObj(rootObj):
        retstats = {}
        for actype in AccuracyType:
            retstats[actype.name] = {
                'current': rootObj.stats.__getattribute__(actype.statsName),
                'last': rootObj.useAllSetsAccumulator['last'][actype]
            }
        return recdotdict(retstats)

    def updateAccuracyStats(self, resultsObj: EvaluationResultsObj, dryRun=False):
        if dryRun:
            rootObj = recdotdict()
            rootObj.useAllSetsAccumulator = copy.deepcopy(self.useAllSetsAccumulator)
            # parent.stats = copy.deepcopy(self.stats)
            rootObj.stats = NetworkStats(None, **{ actype.statsName: self.stats.__getattribute__(actype.statsName) for actype in AccuracyType })
        else:
            rootObj = self

        if self.useAllSets:
            for actype in AccuracyType:
                if not self.reEvaluating:
                    rootObj.useAllSetsAccumulator['last'][actype] = self.stats.__getattribute__(actype.statsName)
                    
                rootObj.useAllSetsAccumulator[actype].append(resultsObj[actype][LossAccuracy.ACCURACY])
                rootObj.stats.__setattr__(actype.statsName, numpy.average(rootObj.useAllSetsAccumulator[actype]))

        elif resultsObj[self.stats.accuracyType][LossAccuracy.ACCURACY] > self.stats[self.stats.accuracyType.statsName]:
            rootObj.stats.overallAccuracy = resultsObj[AccuracyType.OVERALL][LossAccuracy.ACCURACY]
            rootObj.stats.positiveAccuracy = resultsObj[AccuracyType.POSITIVE][LossAccuracy.ACCURACY]
            rootObj.stats.negativeAccuracy = resultsObj[AccuracyType.NEGATIVE][LossAccuracy.ACCURACY]

        if dryRun:
            return NeuralNetworkInstance._generateAccuracyStatsObj(rootObj)

    def prepareForReEvaluation(self):
        '''sets reEvaluating to true, clears useAllSetsAccumulator for new stats'''
        self.reEvaluating = True
        for actype in AccuracyType:
            self.useAllSetsAccumulator['last'][actype] = self.stats.__getattribute__(actype.statsName)
            self.useAllSetsAccumulator[actype] = []

    def fit(self, inputVectors, outputVectors, **kwargs):
        if not self.model: raise BufferError('Model not loaded')
        
        # self.model.fit(inputVectors, outputVectors, **kwargs)
        # print(len(inputVectors), inputVectors[0])
        # print(len(outputVectors), outputVectors[0])
        hist = self.model.fit(inputVectors, outputVectors, **kwargs)
        if kwargs['epochs']:
            # self.stats.epochs += kwargs['epochs']
            self.stats.epochs += len(hist.epoch)
    
    def evaluate(self, evaluationDataHandler: EvaluationDataHandler, updateAccuracyStats=True, verbose=1, **kwargs) -> EvaluationResultsObj:
        if not self.model: raise BufferError('Model not loaded')
        if verbose > 0: print(f"{'Re-e' if self.reEvaluating else 'E'}valuating... (overall > positive > negative)")
        
        results = evaluationDataHandler.evaluateAll(self.model, verbose=verbose, **kwargs)

        if updateAccuracyStats and evaluationDataHandler.accuracyTypesCount() == 3:
            self.updateAccuracyStats(results)
            if verbose > 0:
                # if self.useAllSets: print('Iterations:', len(self.useAllSetsAccumulator[AccuracyType.OVERALL]) + 1)
                if not self.reEvaluating: self.printAllAccuracyStats()

        return results

    def predict(self, inputData, raw=False, batchInput=False, **kwargs):
        if not self.model: raise BufferError('Model not loaded')

        if not batchInput and not gconfig.network.recurrent:
            inputData = inputData.reshape(-1, inputData.size)
        else:
            inputData = [tf.experimental.numpy.vstack(inputData[0]), tf.experimental.numpy.vstack(inputData[1])]

        p = self.model.predict(inputData, **kwargs) if shortcdict(kwargs, 'verbose', 0) != 0 else self.model(inputData)
        if batchInput:
            return p
        if self.config.dataForm.outputVector == DataFormType.BINARY:
            r = p if raw else numpy.round(p)
            return r[0][0]
        elif self.config.dataForm.outputVector == DataFormType.CATEGORICAL:
            return numpy.argmax(p, axis=None, out=None)

    def getAccuracyStats(self):
        return self._generateAccuracyStatsObj()

    @classmethod
    def prettyPrintAccuracyStat(cls, name, stats=None, current=None, last=None):
        current = shortc(current, shortcdict(stats, 'current'))
        last = shortc(last, shortcdict(stats, 'last'))
        print(
            f'{name} accuracy:'.ljust(19) + 
            f'{current}'.ljust(22) + 
            (f"({'+' if current >= last else '-'} {f'{abs(current - last):.20f}'})" if last else '')
        )

    @classmethod
    def printAccuracyStats(cls, statsDict, classValueRatio=None, config=None):
        if config:
            pass ## config already set
        elif hasattr(cls, 'inputVectorFactory'):
            config = cls.inputVectorFactory.config
        else:
            config = gconfig
        classValueRatio = shortc(classValueRatio, config.trainer.customValidationClassValueRatio)
        for name, stats in statsDict.items():
            cls.prettyPrintAccuracyStat(name, stats)
        cls.prettyPrintAccuracyStat('CUSTOM', current=getCustomAccuracy(statsDict, classValueRatio=classValueRatio))
        print()

    def printAllAccuracyStats(self):
        self.printAccuracyStats(self.getAccuracyStats())

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
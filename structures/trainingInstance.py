import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
import math, time
from tensorflow.keras.optimizers import Adam
from tensorflow import keras
from keras.callbacks import EarlyStopping
from keras.callbacks import ModelCheckpoint

from managers.dataManager import DataManager
from managers.neuralNetworkManager import NeuralNetworkManager
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.EvaluationDataHandler import EvaluationDataHandler
from structures.EarlyStoppingWithCustomValidationCallback import EarlyStoppingWithCustomValidation
from constants.enums import SeriesType, AccuracyType
from utils.support import recdotdict, shortc
from globalConfig import trainingConfig


class TimeBasedEarlyStoppingCallback(keras.callbacks.Callback):
    def __init__(self, stopTime=None, timeDuration=None):
        super(TimeBasedEarlyStoppingCallback, self).__init__()
        self.stopTime = stopTime
        self.timeDuration = timeDuration
    
    def on_train_begin(self, logs=None):
        self.startTime = time.time()

    def on_epoch_end(self, epoch, logs=None):
        if (self.stopTime and time.time() > self.stopTime) or (self.timeDuration and time.time() - self.startTime > self.timeDuration):
            self.stopped_epoch = epoch
            self.model.stop_training = True


class TrainingInstance():
    trainingSet = None
    validationSet = None
    testingSet = None

    def __init__(self, nnetwork: NeuralNetworkInstance, tconfig=trainingConfig, **kwargs):
            # trainingSet=None, validationSet=None, testingSet=None, 
            # validationPSet=None, validationNSet=None, testingPSet=None, testingNSet=None):
        self.network = nnetwork
        self.config = recdotdict(tconfig)

        self.updateSets(**kwargs)

    def updateSets(self, trainingSet=None, validationSet=None, testingSet=None, validationPSet=None, validationNSet=None, testingPSet=None, testingNSet=None):
        self.trainingSet = shortc(trainingSet, self.trainingSet)
        self.validationSet = shortc(validationSet, self.validationSet)
        self.testingSet = shortc(testingSet, self.testingSet)

        if (type(validationSet) is list and len(validationSet[0])) or (validationPSet and validationNSet):
            self.validationDataHandler: EvaluationDataHandler = EvaluationDataHandler(validationSet)
            self.validationDataHandler[AccuracyType.POSITIVE] = validationPSet
            self.validationDataHandler[AccuracyType.NEGATIVE] = validationNSet

        if (type(testingSet) is list and len(testingSet[0])) or (testingPSet and testingNSet):
            self.testingDataHandler: EvaluationDataHandler = EvaluationDataHandler(testingSet)
            self.testingDataHandler[AccuracyType.POSITIVE] = testingPSet
            self.testingDataHandler[AccuracyType.NEGATIVE] = testingNSet

    def setTrainingConfig(self, config=None, epochs=None, batchSize=None):
        if config:
            self.config = recdotdict(config)
        else:
            if epochs:
                self.config.epochs = epochs
            if batchSize:
                self.config.batchSize = batchSize

    def train_old(self, iterations, epochs=None, validatePeriodically=False, verbose=1):
        try:
            for i in range(iterations):
                self.network.fit(*self.trainingSet, epochs=shortc(epochs, self.config.epochs), batch_size=self.config.batchSize, verbose=verbose)
                if validatePeriodically and i-1 != iterations: self.evaluate(verbose)    
            pass
        except KeyboardInterrupt:
            print('interruptted')
            raise KeyboardInterrupt
            pass
        return self.evaluate(verbose)

    def train(self, epochs=None, minEpochs=5, validationType: AccuracyType=AccuracyType.OVERALL, patience=None, stopTime=None, timeDuration=None, verbose=1, **kwargs):
        print('split:', len(self.validationDataHandler[AccuracyType.POSITIVE][0]), ':', len(self.validationDataHandler[AccuracyType.NEGATIVE][0]))

        try:
            validation_data = self.validationDataHandler.getTuple(validationType) if validationType else None
            self.network.fit(*self.trainingSet, 
                epochs=minEpochs, 
                batch_size=self.config.batchSize, verbose=verbose, 
                validation_data=validation_data
            )
            
            ## train for a few epochs without any callbacks?

            callbacks = [TimeBasedEarlyStoppingCallback(stopTime=stopTime, timeDuration=timeDuration)]
            if patience: callbacks.append(EarlyStoppingWithCustomValidation(
                network = self.network, batchSize=self.config.batchSize, 
                    custom_validation_data= None if validationType == AccuracyType.OVERALL else [
                        self.validationDataHandler.getTuple(AccuracyType.POSITIVE),
                        self.validationDataHandler.getTuple(AccuracyType.NEGATIVE)
                    ], 
                    custom_validation_data_values=[1/3, 2/3] if validationType != AccuracyType.OVERALL else None,
                monitor='val_accuracy', mode='max', 
                # monitor='val_loss', mode='min', 
                verbose=verbose, patience=patience, restore_best_weights=True))

            if stopTime: 
                print('Stopping at', stopTime)
                print('Current time', time.time())

            if len(self.validationDataHandler[validationType][0]) == 0:
                raise IndexError('Validation set empty')

            self.network.fit(*self.trainingSet, 
                epochs=sys.maxsize if stopTime or timeDuration or patience else shortc(epochs, self.config.epochs), 
                batch_size=self.config.batchSize, verbose=verbose, 
                callbacks=callbacks
            )
            
            ## update stats
            self.evaluate(verbose)
            
            pass
        except KeyboardInterrupt:
            print('interruptted')
            raise KeyboardInterrupt
            pass
    
    def evaluate(self, verbose=1):
        if not self.validationDataHandler: raise AttributeError
        return self.network.evaluate(self.validationDataHandler, batch_size=self.config.batchSize, verbose=verbose)


    def test(self, verbose=1):
        if not self.testingDataHandler: raise AttributeError
        return self.network.evaluate(self.testingDataHandler, batch_size=self.config.batchSize, verbose=verbose)        












# # useSavedNetwork = '1615007016'
# # useSavedNetwork = '1616075899'
# try: useSavedNetwork
# except NameError: useSavedNetwork = None

# ## config
# seriesType = config.training.seriesType
# precedingRange = config.training.precedingRange
# followingRange = config.training.followingRange
# setCount = config.training.setCount
# setSplitTuple = config.training.setSplitTuple
# threshold = config.training.threshold

# sm = DataManager.new(seriesType, precedingRange, followingRange, setCount, setSplitTuple, threshold=threshold, minimumSetsPerSymbol=0) \
#     if not useSavedNetwork else DataManager.fromSave(useSavedNetwork)

# nnm = NeuralNetworkManager()

# ## training config
# epochs = config.training.epochs
# batchSize = config.training.batchSize

# training, validation, testing = sm.getKerasSets()
# validationP = sm.getKerasSets(1, validationDataOnly=True)
# validationN = sm.getKerasSets(2, validationDataOnly=True)
# validationData = [
#     [validation[0], validationP[0], validationN[0]],
#     [validation[1], validationP[1], validationN[1]]
# ]
# inputSize = training[0][0].shape[0]

# ## network init
# if useSavedNetwork:
#     nn = nnm.get(useSavedNetwork)
# else:
#     optimizer = Adam(amsgrad=True)
#     layers = [
#         { 'units': math.floor(inputSize / 1.5), 'dropout': False, 'dropoutRate': 0.001 },
#     ]
#     nn = nnm.createNetworkInstance(optimizer, layers, inputSize,
#             threshold, precedingRange, followingRange, seriesType, sm.normalizationInfo.high, sm.normalizationInfo.volume, accuracyType=AccuracyType.NEGATIVE
#         )

# ## training
# try:
#     for i in range(config.training.iterations):
#         nn.fit(*training, epochs=epochs, batch_size=batchSize, verbose=1)
#         nn.evaluate(*validationData, batch_size=batchSize, verbose=1)
#         print('epochs',nn.stats)
#     pass
# except KeyboardInterrupt:
#     # nnm.saveAll()
#     print('keyboard interrupt')
#     pass

# ## cleanup
# if not config.testing.enabled:
#     nnm.save(useSavedNetwork if useSavedNetwork else nn.stats.id)
#     if not useSavedNetwork: sm.save(nn.id)

# ## stats
# print('input size',inputSize)
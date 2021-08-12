import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import math
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
from tensorflow.keras.optimizers import Adam
from keras.callbacks import EarlyStopping
from keras.callbacks import ModelCheckpoint

from managers.dataManager import DataManager
from managers.neuralNetworkManager import NeuralNetworkManager
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.EvaluationDataHandler import EvaluationDataHandler
from constants.enums import SeriesType, AccuracyType
from utils.support import recdotdict, shortc
from globalConfig import trainingConfig


class TrainingInstance():
    def __init__(self, nnetwork: NeuralNetworkInstance, trainingSet, validationSet, testingSet, 
            tconfig=trainingConfig, validationPSet=None, validationNSet=None, testingPSet=None, testingNSet=None):
        self.network = nnetwork
        self.trainingSet = trainingSet
        self.validationSet = validationSet
        self.testingSet = testingSet
        self.config = recdotdict(tconfig)

        self.validationDataHandler: EvaluationDataHandler = EvaluationDataHandler(validationSet)
        self.validationDataHandler[AccuracyType.POSITIVE] = validationPSet
        self.validationDataHandler[AccuracyType.NEGATIVE] = validationNSet

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

    ## todo, custom callbacks for earlystopping, modelcheckpoint, to check against all eval sets
    def train(self, epochs, validationType: AccuracyType=None, earlyStopping=False, esPatience=1, modelCheckpoint=False, verbose=1):
        try:
            callbacks = []
            if earlyStopping: callbacks.append(EarlyStopping(monitor='val_loss', mode='min', verbose=verbose, patience=esPatience))
            if modelCheckpoint: callbacks.append(ModelCheckpoint(self.network.filepath, monitor='val_loss', mode='min', verbose=verbose, save_best_only=True))

            self.network.fit(*self.trainingSet, epochs=shortc(epochs, self.config.epochs), batch_size=self.config.batchSize, verbose=verbose,
                validationData=self.validationDataHandler[validationType] if validationType else None,
                callbacks=callbacks
            )

            ## reload best network from saved file
            if modelCheckpoint:
                self.network.reload()
            
            ## update stats
            self.evaluate(verbose)
            
            
            pass
        except KeyboardInterrupt:
            print('interruptted')
            raise KeyboardInterrupt
            pass
        # return self.evaluate(verbose)
    
    def evaluate(self, verbose=1):
        # if len(self.validationData[0]) > 0:
            # return self.network.evaluate(*self.validationData, batch_size=self.config.batchSize, verbose=verbose)
        return self.network.evaluate(self.validationDataHandler, batch_size=self.config.batchSize, verbose=verbose)


    def test(self, verbose=1):
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
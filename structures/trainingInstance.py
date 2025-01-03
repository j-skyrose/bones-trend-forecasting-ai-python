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
from keras.callbacks import EarlyStopping
from typing import Dict

from globalConfig import trainingConfig
from constants.enums import SeriesType
from managers.dataManager import DataManager
from managers.neuralNetworkManager import NeuralNetworkManager
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.callbacks.EarlyStoppingWithCustomValidationCallback import EarlyStoppingWithCustomValidation
from structures.callbacks.TimeBasedEarlyStoppingCallback import TimeBasedEarlyStopping
from structures.callbacks.DeviationFromBasedEarlyStoppingCallback import DeviationFromBasedEarlyStopping
from utils.support import recdotdict, shortc, shortcobj


class TrainingInstance():

    def __init__(self, nnetwork: NeuralNetworkInstance, tconfig=trainingConfig, **kwargs):
            # trainingSet=None, validationSet=None, testingSet=None):
        self.network = nnetwork
        self.config = recdotdict(tconfig)

        self.updateSets(**kwargs)

    def updateSets(self, trainingSet=None, validationSet=None, testingSet=None):
        self.trainingSet = shortc(trainingSet, shortcobj(self, 'trainingSet'))
        self.validationSet = shortc(validationSet, shortcobj(self, 'validationSet'))
        self.testingSet = shortc(testingSet, shortcobj(self, 'testingSet'))

    def updateNetworkMetrics(self, resultsObj: Dict, dryRun=False):
        return self.network.updateMetrics(resultsObj, self.validationSet, dryRun)

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

    def train(self, epochs=None, minEpochs=5, patience=None, stopTime=None, timeDuration=None, callbacks=None, verbose=1, **kwargs):

        try:
            if not epochs:
                validation_data = self.validationSet
                self.network.fit(*self.trainingSet,
                    epochs=sys.maxsize,
                    batch_size=self.config.batchSize, verbose=verbose,
                    validation_data=validation_data,
                    callbacks=[
                        # DeviationFromBasedEarlyStopping(minEpochs=minEpochs, validation_accuracy=1)
                        ## push network to max POSITIVE cases first, then pull it back to NEGATIVE during actual training
                        EarlyStoppingWithCustomValidation(
                            additionalLabel='POSITIVE',
                            network = self.network, batchSize=self.config.batchSize, verbose=verbose, restore_best_weights=True,
                            
                            custom_validation_data=None,
                            custom_validation_data_values=None,
                            monitor='val_accuracy', mode='max',
                            # monitor='val_loss', mode='min',
                            override_stops_on_value=0,

                            patience=math.ceil(patience/4)
                        )
                    ]
                )

            fitKWArgs = {}
            callbacks = asList(callbacks)
            callbacks.append(TimeBasedEarlyStopping(stopTime=stopTime, timeDuration=timeDuration))
            if patience:
                callbacks.append(EarlyStopping(
                    restore_best_weights=True,
                    # monitor='val_loss', mode='min',
                    monitor=f'val_{self.network.properties.focusedMetric}', mode='max',
                    patience=patience,
                    min_delta=0.00001
                ))
                fitKWArgs['validation_data'] = self.validationSet

            if stopTime and verbose > 0: 
                print('Stopping at', stopTime)
                print('Current time', time.time())

            if len(self.validationSet[0]) == 0:
                raise IndexError('Validation set empty')

            self.network.fit(*self.trainingSet,
                                       **fitKWArgs, 
                epochs=sys.maxsize if stopTime or timeDuration or patience else shortc(epochs, self.config.epochs), 
                batch_size=self.config.batchSize, verbose=verbose, 
                callbacks=callbacks
            )
            
            ## update stats
            return self.evaluate(verbose, **kwargs)
            
            pass
        except KeyboardInterrupt:
            print('interruptted')
            raise KeyboardInterrupt
            pass
    
    def evaluate(self, verbose=1, **kwargs):
        if not self.validationSet: raise AttributeError
        return self.network.evaluate(self.validationSet, batch_size=self.config.batchSize, verbose=verbose, **kwargs)

    def test(self, verbose=1):
        if not self.testingSet: raise AttributeError
        return self.network.evaluate(self.testingSet, batch_size=self.config.batchSize, verbose=verbose)        












# from tensorflow.keras.optimizers import Adam
# from tensorflow import keras
# from keras.callbacks import EarlyStopping
# from keras.callbacks import ModelCheckpoint

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
# validationP = sm.getKerasSets(1, validationSetOnly=True)
# validationN = sm.getKerasSets(2, validationSetOnly=True)
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
#             threshold, precedingRange, followingRange, seriesType, sm.normalizationInfo.high, sm.normalizationInfo.volume
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
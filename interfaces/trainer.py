import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, math, gc, time
from numpy.lib.function_base import median
from tensorflow.keras.optimizers import Adam
from datetime import date, datetime, timedelta
from typing import Tuple
import tensorflow.keras.backend as K

from utils.other import normalizeStockData
from managers.dataManagerDBWrapper import DataManagerDBWrapper
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.inputVectorFactory import InputVectorFactory
from structures.trainingInstance import TrainingInstance
from managers.statsManager import StatsManager
from structures.neuralNetworkInstance import NeuralNetworkInstance
from constants.enums import AccuracyType, LossAccuracy, OperatorDict, SeriesType
from constants.exceptions import SufficientlyUpdatedDataNotAvailable
from utils.support import shortc
from globalConfig import config as gconfig

nnm: NeuralNetworkManager = NeuralNetworkManager()

def getTimestamp(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day, hour=datetime.now().hour, minute=datetime.now().minute):
    return time.mktime(datetime(year, month, day, hour, minute).timetuple())

class Trainer:
    def __init__(self, network=None, networkId=None, **kwargs):
        startt = time.time()
        self.network = nnm.get(networkId) if networkId else network
        self.dm: DataManager = DataManager.forTraining(inputVectorFactory=self.network.inputVectorFactory, **kwargs)

        if network:
            self.network.updateStats(
                normalizationInfo=self.dm.normalizationInfo,
                **kwargs
            )

        setstartt = time.time()
        sets = self.dm.getKerasSets()
        class1set = self.dm.getKerasSets(1, True)
        class2set = self.dm.getKerasSets(2, True)

        print('Set creation time required:', time.time() - setstartt, 'seconds')
        print('Set creation breakdown')
        StatsManager().printAll()
        self.instance = TrainingInstance(self.network, *sets, { 'epochs': 1, 'batchSize': 32 }, class1set, class2set)  
        print('Startup time required:', time.time() - startt, 'seconds')

    ## todo, modify for validationData change to .fit, might not be interruptible
    def train(self, stopTime=None, trainingDuration=0, iterations=None, evaluateEveryXIterations=0, lossIterationTolerance=0):
        if iterations:
            epochs = 1
            periodicValidation = False
            if evaluateEveryXIterations:
                iterations, remainderIterations = divmod(iterations, evaluateEveryXIterations)
                epochs = evaluateEveryXIterations
                periodicValidation = True

            self.instance.train(iterations, epochs=epochs, validatePeriodically=periodicValidation)
            if remainderIterations: self.instance.train(1, epochs=remainderIterations)
        else:

            stopTime = shortc(stopTime, time.time() + trainingDuration)

            iterationTimeRequired = time.time()
            self.instance.train(1)
            iterationTimeRequired = time.time() - iterationTimeRequired

            previousLoss = self.instance.evaluate()[self.instance.network.stats.accuracyType][LossAccuracy.LOSS] if lossIterationTolerance else 0
            lossIterationToleranceCounter = 0

            batchingIterations = 1
            if not lossIterationTolerance:
                if evaluateEveryXIterations:
                        batchingIterations = evaluateEveryXIterations
                        iterationTimeRequired = iterationTimeRequired * evaluateEveryXIterations
                else:
                    batchingIterations = int((stopTime - time.time()) / iterationTimeRequired)
                    print(stopTime - time.time(), iterationTimeRequired, batchingIterations)

            itcount = 0
            while lossIterationTolerance or time.time() + iterationTimeRequired < stopTime:
                if itcount % 5 == 0:
                    # K.clear_session()
                    gc.collect()
                itcount += 1
                try:
                    print('Iterating...')
                    self.instance.train(1, epochs=batchingIterations)

                    if lossIterationTolerance:
                        loss = self.instance.evaluate()[self.instance.network.stats.accuracyType][LossAccuracy.LOSS]

                        if previousLoss < loss:
                            lossIterationToleranceCounter += 1
                            if lossIterationToleranceCounter > lossIterationTolerance:
                                break
                        else:
                            lossIterationToleranceCounter = 0
                            
                        previousLoss = loss

                    else:
                        if evaluateEveryXIterations:
                            self.instance.evaluate()
                        else:
                            batchingIterations = 1
                except KeyboardInterrupt:
                    break

    ## outddated with incorporation of validationSet, EarlyStopping, ModelCheckpoint in model.fit
    def train_old(self, stopTime=None, trainingDuration=0, iterations=None, evaluateEveryXIterations=0, lossIterationTolerance=0):
        if iterations:
            epochs = 1
            periodicValidation = False
            if evaluateEveryXIterations:
                iterations, remainderIterations = divmod(iterations, evaluateEveryXIterations)
                epochs = evaluateEveryXIterations
                periodicValidation = True

            self.instance.train(iterations, epochs=epochs, validatePeriodically=periodicValidation)
            if remainderIterations: self.instance.train(1, epochs=remainderIterations)
        else:

            stopTime = shortc(stopTime, time.time() + trainingDuration)

            iterationTimeRequired = time.time()
            self.instance.train(1)
            iterationTimeRequired = time.time() - iterationTimeRequired

            previousLoss = self.instance.evaluate()[self.instance.network.stats.accuracyType][LossAccuracy.LOSS] if lossIterationTolerance else 0
            lossIterationToleranceCounter = 0

            batchingIterations = 1
            if not lossIterationTolerance:
                if evaluateEveryXIterations:
                        batchingIterations = evaluateEveryXIterations
                        iterationTimeRequired = iterationTimeRequired * evaluateEveryXIterations
                else:
                    batchingIterations = int((stopTime - time.time()) / iterationTimeRequired)
                    print(stopTime - time.time(), iterationTimeRequired, batchingIterations)

            itcount = 0
            while lossIterationTolerance or time.time() + iterationTimeRequired < stopTime:
                if itcount % 5 == 0:
                    # K.clear_session()
                    gc.collect()
                itcount += 1
                try:
                    print('Iterating...')
                    self.instance.train(1, epochs=batchingIterations)

                    if lossIterationTolerance:
                        loss = self.instance.evaluate()[self.instance.network.stats.accuracyType][LossAccuracy.LOSS]

                        if previousLoss < loss:
                            lossIterationToleranceCounter += 1
                            if lossIterationToleranceCounter > lossIterationTolerance:
                                break
                        else:
                            lossIterationToleranceCounter = 0
                            
                        previousLoss = loss

                    else:
                        if evaluateEveryXIterations:
                            self.instance.evaluate()
                        else:
                            batchingIterations = 1
                except KeyboardInterrupt:
                    break


        self.instance.evaluate()

    def saveNetwork(self, withSets=False):
        nnm.save(self.network)

if __name__ == '__main__':

    try:
        fl, arg1, *argv = sys.argv
    except ValueError:
        arg1 = 'new'

    if arg1.lower() == 'new':
        # precrange = 202
        precrange = 150
        # precrange = 75
        folrange = 20
        threshold = 0.05
        setSplitTuple = (0.80,0.20)

        if gconfig.testing.enabled:
            ## testing
            setCount = 250
            # setCount = 5
            minimumSetsPerSymbol = 0
        else:
            ## real
            setCount = 75000
            minimumSetsPerSymbol = 10

        ## network
        inputSize = InputVectorFactory().getInputSize(precrange)
        optimizer = Adam(amsgrad=True)
        layers = [
            { 'units': math.floor(inputSize / 1.5), 'dropout': False, 'dropoutRate': 0.001 },
        ]

        t = Trainer(
            network=nnm.createNetworkInstance(
                optimizer, layers, inputSize
            ),
            precedingRange=precrange, 
            followingRange=folrange,
            threshold=threshold,
            setCount=setCount,
            setSplitTuple=setSplitTuple,
            minimumSetsPerSymbol=minimumSetsPerSymbol
        )



    else:
        # c.collectVIX()
        pass

    
    p: Trainer = t

    # p.train(iterations=50, evaluateEveryXIterations=20)
    # p.train(trainingDuration=0.2*60*60, evaluateEveryXIterations=20)
    p.train(lossIterationTolerance=2)
    # p.train(stopTime=getTimestamp(hour=14, minute=0))

    # p.saveNetwork()

    print('done')


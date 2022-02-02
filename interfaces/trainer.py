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
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.inputVectorFactory import InputVectorFactory
from structures.trainingInstance import TrainingInstance
from managers.statsManager import StatsManager
from structures.neuralNetworkInstance import NeuralNetworkInstance
from constants.enums import AccuracyType, LossAccuracy, OperatorDict, SeriesType
from constants.exceptions import SufficientlyUpdatedDataNotAvailable
from utils.support import containsAllKeys, shortc
from globalConfig import config as gconfig

nnm: NeuralNetworkManager = NeuralNetworkManager()

def getTimestamp(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day, hour=datetime.now().hour, minute=datetime.now().minute):
    return time.mktime(datetime(year, month, day, hour, minute).timetuple())

class Trainer:
    def __init__(self, network=None, networkId=None, useAllSets=False, **kwargs):
        startt = time.time()
        self.network = nnm.get(networkId) if networkId else network
        self.dm: DataManager = DataManager.forTraining(inputVectorFactory=self.network.inputVectorFactory, useAllSets=useAllSets, **kwargs)
        self.useAllSets = useAllSets

        # if network:
        #     self.network.updateStats(
        #         normalizationInfo=self.dm.normalizationInfo,
        #         **kwargs
        #     ) 

        kwparams = {}
        if not useAllSets:
            setstartt = time.time()
            kwparams = self._getSetKWParams()

            print('Set creation time required:', time.time() - setstartt, 'seconds')
            print('Set creation breakdown')
            StatsManager().printAll()

        self.instance = TrainingInstance(self.network, { 'epochs': 1, 'batchSize': 32 }, **kwparams)
        print('Startup time required:', time.time() - startt, 'seconds')

    def _getSetKWParams(self, **kwargs):
        print('Building KWParams object')
        t, v, ts = self.dm.getKerasSets(**kwargs)
        class1set = self.dm.getKerasSets(1, True, **kwargs)
        class2set = self.dm.getKerasSets(2, True, **kwargs)
        print('Keras sets built')
        return {
            'trainingSet': t, 
            'validationSet': v, 
            'testingSet': ts, 
            'validationPSet': class1set, 
            'validationNSet': class2set
        }

    def train(self, **kwargs):
        if not self.useAllSets:
            self.instance.train(**kwargs)
        else:
            self.instance.network.useAllSets = True

            print('Iterating through set slices')
            maxIterations = self.dm.getNumberOfWindowIterations()
            usePatienceGradient = containsAllKeys(kwargs, 'initialPatience', 'finalPatience', throwSomeError=ValueError('Missing some patience gradience arguments'))
            for s in range(maxIterations):
                if usePatienceGradient:
                    kwargs['patience'] = kwargs['initialPatience'] + int(s * (kwargs['finalPatience'] - kwargs['initialPatience']) / (maxIterations-1))
                    print('Patience:', kwargs['patience'])

                print('Slice', s+1, '/', maxIterations)
                self.instance.updateSets(**self._getSetKWParams(slice=s))
                self.instance.train(**kwargs)
                gc.collect()

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
                    # self.instance.train(1, epochs=batchingIterations)
                    self.instance.train(batchingIterations)

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
        useAllSets = True
        # precrange = 202
        # precrange = 150
        precrange = 65
        folrange = 30
        threshold = 0.1
        setSplitTuple = (0.80,0.20)

        if gconfig.testing.enabled:
            ## testing
            setCount = 250
            # setCount = 5
            minimumSetsPerSymbol = 0
        else:
            ## real
            setCount = 55000
            minimumSetsPerSymbol = 10

        ## network
        optimizer = Adam(amsgrad=True)
        if gconfig.network.recurrent:
            staticSize, semiseriesSize, seriesSize = InputVectorFactory().getInputSize()
            layers = [
                [
                    { 'units': math.floor(staticSize / 1), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(semiseriesSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(seriesSize / 1), 'dropout': False, 'dropoutRate': 0.001 }
                ]
            ]
        else:
            inputSize = InputVectorFactory().getInputSize(precrange)
            layers = [
                # { 'units': math.floor(inputSize / 0.85), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.3), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.7), 'dropout': False, 'dropoutRate': 0.001 },
                { 'units': math.floor(inputSize / 2), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 2.5), 'dropout': False, 'dropoutRate': 0.001 },
            ]

        t = Trainer(
            network=nnm.createNetworkInstance(
                optimizer, layers, 
                None if gconfig.network.recurrent else inputSize, 
                accuracyType=AccuracyType.NEGATIVE, useAllSets=useAllSets,
                precedingRange=precrange
            ),
            precedingRange=precrange, 
            followingRange=folrange,
            threshold=threshold,
            setCount=setCount,
            setSplitTuple=setSplitTuple,
            minimumSetsPerSymbol=minimumSetsPerSymbol,

            useAllSets=useAllSets
        )



    else:
        # c.collectVIX()
        pass

    
    p: Trainer = t

    # p.instance.train(iterations=50, evaluateEveryXIterations=20)
    # p.instance.train(trainingDuration=0.2*60*60, evaluateEveryXIterations=20)
    # p.instance.train(patience=4)
    # p.instance.train(stopTime=getTimestamp(hour=14, minute=0))
    # p.instance.train(validationType=AccuracyType.NEGATIVE, timeDuration=60*2)
    # p.instance.train(timeDuration=30)
    # p.instance.train(stopTime=getTimestamp(hour=22, minute=28))
    


    p.train(validationType=AccuracyType.NEGATIVE, 
        patience=30, 
        # initialPatience=10, finalPatience=30
        
    # stopTime=getTimestamp(hour=22, minute=0)
    )


    ## debugging getAdjustedSlidingWindowPercentage on real data
    # for i in range(p.dm.getNumberOfWindowIterations()):
    #     trsize = len(p.dm._getSetSlice(p.dm.trainingSet, i))
    #     vsize = len(p.dm._getSetSlice(p.dm.validationSet, i))
    #     tssize = len(p.dm._getSetSlice(p.dm.testingSet, i))
    #     print('it', i, 'sizes:', trsize, vsize, tssize)

    # p.saveNetwork()

    print('done')


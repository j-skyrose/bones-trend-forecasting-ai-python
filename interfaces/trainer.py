import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from globalConfig import config as gconfig

import tqdm, math, gc, time, numpy
from numpy.lib.function_base import median
from tensorflow.keras.optimizers import Adam
from datetime import date, datetime, timedelta
from typing import Tuple
from argparse import ArgumentError
import tensorflow.keras.backend as K

from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.inputVectorFactory import InputVectorFactory
from structures.trainingInstance import TrainingInstance
from managers.statsManager import StatsManager
from structures.neuralNetworkInstance import NeuralNetworkInstance
from constants.enums import AccuracyType, LossAccuracy, OperatorDict, SeriesType
from constants.exceptions import SufficientlyUpdatedDataNotAvailable
from utils.support import containsAllKeys, shortc, shortcdict
from constants.values import tseNoCommissionSymbols

nnm: NeuralNetworkManager = NeuralNetworkManager()
dbm: DatabaseManager = DatabaseManager()

def getTimestamp(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day, hour=datetime.now().hour, minute=datetime.now().minute):
    return time.mktime(datetime(year, month, day, hour, minute).timetuple())

class Trainer:
    def __init__(self, network=None, networkId=None, useAllSets=False, **kwargs):
        startt = time.time()
        self.network = nnm.get(networkId) if networkId else network
        self.dm: DataManager = DataManager.forTraining(inputVectorFactory=self.network.inputVectorFactory, useAllSets=useAllSets, **kwargs)
        self.useAllSets = useAllSets

        if network:
            self.network.updateStats(
                normalizationInfo=self.dm.normalizationInfo,
                **kwargs
            ) 

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
        omitValidation = shortcdict(kwargs, 'omitValidation', False)

        print('Building KWParams object')
        sets = self.dm.getKerasSets(**kwargs)
        if shortcdict(kwargs, 'validationDataOnly', False):
            if omitValidation: raise ArgumentError
            t = None
            v = sets
            ts = None
            del kwargs['validationDataOnly']
        else: 
            t, v, ts = sets
        print('KWParams class sets')

        class1set = None
        class2set = None
        if not omitValidation:
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
            if not any(x in kwargs.keys() for x in ['epochs', 'patience']):
                raise ArgumentError(None, 'Missing epochs, network will not train at all')
            self.instance.train(**kwargs)
        else:
            explicitValidation = self.dm.explicitValidationSet
            self.instance.network.useAllSets = True
            usePatienceGradient = containsAllKeys(kwargs, 'initialPatience', 'finalPatience', throwSomeError=ValueError('Missing some patience gradience arguments'))

            ## display runtime stats and estimated completion time (similar to TQDM)
            iterationTimes = []
            maxIterations = self.dm.getNumberOfWindowIterations()
            def printCurrentStatus(s):
                print('Slice', s+1, '/', maxIterations, end='')
                if len(iterationTimes) > 0:
                    avgtime = numpy.average(iterationTimes)
                    print(' [{}<{}, {}s/it]'.format(
                        ## time took
                        '{0:02.0f}:{1:02.0f}'.format(*divmod(sum(iterationTimes), 60)),
                        ## time remaining
                        '{0:02.0f}:{1:02.0f}'.format(*divmod((maxIterations - s) * avgtime, 60)),
                        ## rate
                        '{:.2f}'.format(avgtime)
                    ))
                else: print()

            print('Iterating through set slices')
            for s in range(maxIterations):
                startt = time.time()

                if usePatienceGradient:
                    kwargs['patience'] = kwargs['initialPatience'] + int(s * (kwargs['finalPatience'] - kwargs['initialPatience']) / (maxIterations-1))
                    print('Patience:', kwargs['patience'])

                printCurrentStatus(s)
                self.instance.updateSets(**self._getSetKWParams(slice=s, omitValidation=True if explicitValidation and s > 0 else False))
                self.instance.train(**kwargs)
                gc.collect()
                iterationTimes.append(time.time() - startt)
            

            if explicitValidation:
                ## validation set never changes, so no loop and re-build required
                self.instance.evaluate(reEvaluate=True)
            else:
                iterationTimes = []
                ## re-evaluating
                for s in range(maxIterations):
                    startt = time.time()

                    printCurrentStatus(s)
                    self.instance.updateSets(**self._getSetKWParams(slice=s, validationDataOnly=True))
                    self.instance.evaluate(reEvaluate=True)
                    gc.collect()

                    iterationTimes.append(time.time() - startt)

            self.instance.network.printAccuracyStats()

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
        # setSplitTuple = (0.80,0.20)
        # explicitValidationSymbolList = []
        setSplitTuple = (0.99,0)
        explicitValidationSymbolList = dbm.getSymbols(exchange='TSX', symbol=tseNoCommissionSymbols)[1:2]


        if gconfig.testing.enabled:
            ## testing
            setCount = 250
            # setCount = 5
            minimumSetsPerSymbol = 0
            useAllSets=False
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
                    { 'units': math.floor(staticSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(semiseriesSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(seriesSize / 1), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor((staticSize + semiseriesSize + seriesSize) / 2), 'dropout': False, 'dropoutRate': 0.001 },
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

            useAllSets=useAllSets,
            explicitValidationSymbolList=explicitValidationSymbolList
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


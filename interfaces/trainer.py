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
from constants.enums import AccuracyType, ChangeType, SetClassificationType, LossAccuracy, OperatorDict, SeriesType
from constants.exceptions import SufficientlyUpdatedDataNotAvailable
from utils.support import containsAllKeys, shortc, shortcdict
from constants.values import tseNoCommissionSymbols

nnm: NeuralNetworkManager = NeuralNetworkManager()
dbm: DatabaseManager = DatabaseManager()

def getTimestamp(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day, hour=datetime.now().hour, minute=datetime.now().minute):
    return time.mktime(datetime(year, month, day, hour, minute).timetuple())

accuracyStatsHeaderLine1 = ['','Curr Accum Acc', 'Future Accum Acc','Future Accum Acc']
accuracyStatsHeaderLine2 = ['','', 'bef-Training-acc', 'aft-Training-acc']
def getCustomAccuracy(statsObj): return statsObj[AccuracyType.POSITIVE.name].current*gconfig.trainer.customValidationClassValueRatio + statsObj[AccuracyType.NEGATIVE.name].current*(1 - gconfig.trainer.customValidationClassValueRatio)
def getAccDiffStr(forwardAccuracy, currentAccuracy):
    return f"{ '+' if forwardAccuracy > currentAccuracy else '' }{forwardAccuracy - currentAccuracy:.5f}"

class Trainer:
    def __init__(self, network=None, networkId=None, useAllSets=False, dataManager=None, **kwargs):
        verbose = shortcdict(kwargs, 'verbose', 1)
        startt = time.time()
        self.network = nnm.get(networkId) if networkId else network
        self.dm: DataManager = None
        if dataManager:
            self.dm = dataManager
        else:    
            self.dm =  DataManager.forTraining(inputVectorFactory=self.network.inputVectorFactory, useAllSets=useAllSets, **kwargs)
        self.useAllSets = useAllSets

        if network:
            self.network.updateStats(
                normalizationData=self.dm.normalizationData, useAllSets=useAllSets, seriesType=self.dm.seriesType,
                **kwargs
            ) 

        kwparams = {}
        if not useAllSets:
            setstartt = time.time()
            kwparams = self._getSetKWParams(verbose=verbose)

            if verbose >= 2:
                print('Set creation time required:', time.time() - setstartt, 'seconds')
                print('Set creation breakdown')
                StatsManager().printAll()

        self.instance = TrainingInstance(self.network, { 'epochs': 1, 'batchSize': 128 }, **kwparams)
        if verbose >= 2: print('Startup time required:', time.time() - startt, 'seconds')

    def _getSetKWParams(self, **kwargs):
        verbose = shortcdict(kwargs, 'verbose', 0)

        ksetsGroup = self.dm.getKerasSets(validationSetClassification=[_ for _ in SetClassificationType], **kwargs)
        
        t = v = vc1 = vc2 = ts = None
        if shortcdict(kwargs, 'validationSetOnly', False):
            v, vc1, vc2 = ksetsGroup

        elif shortcdict(kwargs, 'excludeValidationSet', False):
            t, ts = ksetsGroup
            t = t[0]
            ts = ts[0]
        else:
            t, v, ts = ksetsGroup
            v, vc1, vc2 = v
            t = t[0]
            ts = ts[0]

        if verbose >= 2: print('Keras sets built')
        return {
            'trainingSet': t, 
            'validationSet': v, 
            'testingSet': ts, 
            'validationPSet': vc1, 
            'validationNSet': vc2
        }

    def train(self, **kwargs):
        verbose = shortcdict(kwargs, 'verbose', 1)
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
                    timetookminutes, timetookseconds = divmod(sum(iterationTimes), 60)
                    timeremainingminutes, timeremainingseconds = divmod((maxIterations - s) * avgtime, 60)
                    print(' [{}<{}, {}s/it]'.format(
                        ## time took
                        '{0:02.0f}:{1:02.0f}:{2:02.0f}'.format(*divmod(timetookminutes, 60), timetookseconds),
                        ## time remaining
                        '{0:02.0f}:{1:02.0f}:{2:02.0f}'.format(*divmod(timeremainingminutes, 60), timeremainingseconds),
                        ## rate
                        '{:.2f}'.format(avgtime)
                    ))
                else: print()

            print('Iterating through set slices')
            for s in range(maxIterations):
                startt = time.time()
                printCurrentStatus(s)

                ## snapshot state/stats before training
                currentWeights = self.instance.network.model.get_weights()
                currentAccuracyStats = self.instance.network.getAccuracyStats()

                ## pre-training setup
                if usePatienceGradient:
                    kwargs['patience'] = kwargs['initialPatience'] + int(s * (kwargs['finalPatience'] - kwargs['initialPatience']) / (maxIterations-1))
                    print('Patience:', kwargs['patience'])
                self.instance.updateSets(**self._getSetKWParams(slice=s))

                ## snapshot accuracy stats on the new validation set before training
                prevaluateResults = self.instance.evaluate(updateAccuracyStats=False, verbose=verbose-1)
                futureAccuracyStats_prevaluate = self.instance.network.updateAccuracyStats(prevaluateResults, dryRun=True)

                ## train and evaluate
                if verbose >= 1: print('Training...')
                postEvaluateResults = self.instance.train(updateAccuracyStats=False, verbose=verbose-1, **kwargs)
                futureAccuracyStats_postEvaluate = self.instance.network.updateAccuracyStats(postEvaluateResults, dryRun=True)

                ## compare accuracy stats before and after training
                accuracyRows = []
                for acctype in AccuracyType:
                    currentAccuracy = currentAccuracyStats[acctype.name].current
                    futureAccuracy_prevaluate = futureAccuracyStats_prevaluate[acctype.name].current
                    futureAccuracy_postEvaluate = futureAccuracyStats_postEvaluate[acctype.name].current
                    accuracyRows.append([acctype.name, currentAccuracy, futureAccuracy_prevaluate, futureAccuracy_postEvaluate])
                    accuracyRows.append(['', '', getAccDiffStr(futureAccuracy_prevaluate, currentAccuracy), getAccDiffStr(futureAccuracy_postEvaluate, currentAccuracy)])
                currentCustomAccuracy = getCustomAccuracy(currentAccuracyStats)
                futureCustomAccuracy_prevaluate = getCustomAccuracy(futureAccuracyStats_prevaluate)
                futureCustomAccuracy_postEvaluate = getCustomAccuracy(futureAccuracyStats_postEvaluate)
                accuracyRows.append(['CUSTOM', currentCustomAccuracy, futureCustomAccuracy_prevaluate, futureCustomAccuracy_postEvaluate])
                accuracyRows.append(['','', getAccDiffStr(futureCustomAccuracy_prevaluate, currentCustomAccuracy), getAccDiffStr(futureCustomAccuracy_postEvaluate, currentCustomAccuracy)])

                for r in [accuracyStatsHeaderLine1, accuracyStatsHeaderLine2, *accuracyRows]:
                    print("{: >10} {: >21} {: >21} {: >21}".format(*r))

                ## if network was in a better state accuracy-wise before the training, then restore it to that original
                if futureCustomAccuracy_prevaluate > futureCustomAccuracy_postEvaluate:
                    print('Future state is worse, restoring weights...')
                    self.instance.network.model.set_weights(currentWeights)
                    self.instance.network.updateAccuracyStats(prevaluateResults)
                else:
                    self.instance.network.updateAccuracyStats(postEvaluateResults)

                print()

                gc.collect()
                iterationTimes.append(time.time() - startt)
            

            self.instance.network.prepareForReEvaluation()
            if explicitValidation:
                ## validation set never changes, so no loop and re-build required
                self.instance.evaluate()
            else:
                iterationTimes = []
                ## re-evaluating
                for s in range(maxIterations):
                    startt = time.time()

                    printCurrentStatus(s)
                    self.instance.updateSets(**self._getSetKWParams(slice=s, validationSetOnly=True))
                    self.instance.evaluate()
                    gc.collect()

                    iterationTimes.append(time.time() - startt)

            self.instance.network.printAllAccuracyStats()

    def saveNetwork(self, withSets=False, dryrun=False):
        nnm.save(self.network, dryrun)

if __name__ == '__main__':

    try:
        fl, arg1, *argv = sys.argv
    except ValueError:
        arg1 = 'new'

    if arg1.lower() == 'new':
        # useAllSets = True
        useAllSets = False
        # precrange = 95
        precrange = 60
        folrange = 10
        changeValue = 0.05
        changeType = ChangeType.PERCENTAGE

        setSplitTuple = (0.80,0.20)
        explicitValidationSymbolList = []
        # setSplitTuple = (0.99,0)
        # explicitValidationSymbolList = dbm.getSymbols(exchange='TSX', symbol='XQQ')


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
        inputSize = None
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
                optimizer, layers, precedingRange=precrange, inputSize=inputSize,
                # useAllSets=useAllSets
            ),
            verbose=1,
            precedingRange=precrange, 
            followingRange=folrange,
            changeValue=changeValue,
            changeType=changeType,
            setCount=setCount,
            setSplitTuple=setSplitTuple,
            accuracyType=AccuracyType.NEGATIVE,
            minimumSetsPerSymbol=minimumSetsPerSymbol,
            requireEarningsDates=True,

            maxGoogleInterestHandlers=0,

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


import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from globalConfig import config as gconfig

import tqdm, math, gc, time, numpy, optparse
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
from constants.enums import ChangeType, OperatorDict, SeriesType
from constants.exceptions import SufficientlyUpdatedDataNotAvailable
from utils.other import getPrecision
from utils.support import repackKWArgs, shortcdict, xorGeneralized
from constants.values import tseNoCommissionSymbols

nnm: NeuralNetworkManager = NeuralNetworkManager()
dbm: DatabaseManager = DatabaseManager()

def getTimestamp(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day, hour=datetime.now().hour, minute=datetime.now().minute):
    return time.mktime(datetime(year, month, day, hour, minute).timetuple())

metricsHeaderLine1 = ['','Curr Accum Met', 'Future Accum Met','Future Accum Met']
metricsHeaderLine2 = ['','', 'before Training', 'after Training']
def getDiffString(forwardValue, currentValue):
    if forwardValue == currentValue: return ''
    return f"{ '+' if forwardValue > currentValue else '' }{forwardValue - currentValue:.{min(5, max(getPrecision(forwardValue), getPrecision(currentValue)))}f}"

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
            self.network.updateProperties(
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

        validationSetOnly = shortcdict(kwargs, 'validationSetOnly', False)

        ksetsGroup = self.dm.getKerasSets(**kwargs)
        
        t = v = ts = None
        if validationSetOnly:
            v = ksetsGroup[0]
        elif shortcdict(kwargs, 'excludeValidationSet', False):
            t, ts = ksetsGroup
        else:
            t, v, ts = ksetsGroup

        if verbose >= 2: print('Keras sets built')
        return {
            'trainingSet': t,
            'validationSet': v,
            'testingSet': ts
        }

    def train(self, patience=None, initialPatience=None, finalPatience=None, epochs=None, trainingPatience=None, iterationPatience=None, verbose=1, **kwargs):
        kwargs = repackKWArgs(locals())
        if not self.useAllSets:
            if epochs is None and patience is None:
                raise ArgumentError(None, 'Missing epochs, network will not train at all')
            self.instance.train(**kwargs)
        else:
            if patience is not None and (trainingPatience is not None or iterationPatience is not None):
                raise ValueError('Unsure which patience to use')
            if xorGeneralized(trainingPatience, iterationPatience):
                raise ValueError('Missing some patience argument')
            if xorGeneralized(initialPatience, finalPatience):
                raise ValueError('Missing some patience gradience arguments')
            usePatienceGradient = initialPatience is not None and finalPatience is not None
            explicitValidation = self.dm.explicitValidationSet
            self.instance.network.useAllSets = True

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

            noProgressStreak = 0
            if trainingPatience is not None:
                kwargs['patience'] = trainingPatience
            elif patience is not None:
                iterationPatience = patience
            print('Iterating through set slices')
            for s in range(maxIterations):
                startt = time.time()
                printCurrentStatus(s)

                ## snapshot state/stats before training
                currentWeights = self.instance.network.model.get_weights()
                currentMetrics = self.instance.network.getMetricsDict()

                ## pre-training setup
                if usePatienceGradient:
                    kwargs['patience'] = initialPatience + int(s * (finalPatience - initialPatience) / (maxIterations-1))
                    print('Patience:', kwargs['patience'])
                self.instance.updateSets(**self._getSetKWParams(slice=s))

                ## snapshot metrics values on the new validation set before training
                prevaluateMetrics = self.instance.evaluate(updateMetrics=False, verbose=verbose-1)
                futureMetrics_prevaluate = self.instance.updateNetworkMetrics(prevaluateMetrics, dryRun=True)

                ## train and evaluate
                if verbose >= 1: print('Training...')
                postEvaluateMetrics = self.instance.train(updateMetrics=False, **kwargs)
                futureMetrics_postEvaluate = self.instance.updateNetworkMetrics(postEvaluateMetrics, dryRun=True)

                ## compare accuracy stats before and after training
                metricsRows = []
                for m,v in currentMetrics.items():
                    currentMetric = v.current
                    futureMetric_prevaluate = futureMetrics_prevaluate[m].current
                    futureMetric_postEvaluate = futureMetrics_postEvaluate[m].current
                    metricsRows.append([m, currentMetric, futureMetric_prevaluate, futureMetric_postEvaluate])
                    metricsRows.append(['', '', getDiffString(futureMetric_prevaluate, currentMetric), getDiffString(futureMetric_postEvaluate, currentMetric)])

                for r in [metricsHeaderLine1, metricsHeaderLine2, *metricsRows]:
                    print("{: >16} {: >21} {: >21} {: >21}".format(*r))

                ## if network was in a better state metrics-wise before the training, then restore those weights
                if futureMetrics_prevaluate[self.instance.network.properties.focusedMetric].current > futureMetrics_postEvaluate[self.instance.network.properties.focusedMetric].current:
                    noProgressStreak += 1
                    print('Future state is worse, restoring weights...')
                    self.instance.network.model.set_weights(currentWeights)
                    self.instance.updateNetworkMetrics(prevaluateMetrics)
                    if iterationPatience and noProgressStreak > iterationPatience:
                        print(f'No progress made in past {iterationPatience} slices, stopping training')
                        break
                else:
                    noProgressStreak = 0
                    self.instance.updateNetworkMetrics(postEvaluateMetrics)

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
                    self.instance.updateSets(**self._getSetKWParams(slice=s, validationSetOnly=True, 
                                                                    includeInValidationSetInstancesRemovedByReduction=gconfig.sets.instanceReduction.enabled
                                                                    ))
                    self.instance.evaluate()
                    gc.collect()
                    iterationTimes.append(time.time() - startt)
                    print()

            self.instance.network.printAllMetrics()

    def saveNetwork(self, withSets=False, dryrun=False):
        nnm.save(self.network, dryrun)

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-n', '--no-save',
        action='store_true', dest='no_save'
    )
    options, args = parser.parse_args()

    try:
        fl, arg1, *argv = sys.argv
    except ValueError:
        arg1 = 'new'

    if arg1.lower() == 'new':
        changeType = gconfig.training.changeType
        focusedMetric = gconfig.training.focusedMetric
        setSplitTuple = gconfig.training.setSplitTuple
        precrange = gconfig.training.precedingRange
        folrange = gconfig.training.followingRange
        changeValue = gconfig.training.changeValue

        # useAllSets = True
        useAllSets = False
        # precrange = 95
        # precrange = 60
        # folrange = 20
        # changeValue = 0.05
        # changeType = ChangeType.ENDING_PERCENTAGE
        # changeValue = 10
        # changeType = ChangeType.ANY_DAY_ABSOLUTE

        # setSplitTuple = (0.80,0.20)
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
            focusedMetric=focusedMetric,

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
    # p.instance.train(timeDuration=60*2)
    # p.instance.train(timeDuration=30)
    # p.instance.train(stopTime=getTimestamp(hour=22, minute=28))
    


    try:
        res1 = p.train(patience=4)


    ## debugging getAdjustedSlidingWindowPercentage on real data
    # for i in range(p.dm.getNumberOfWindowIterations()):
    #     trsize = len(p.dm._getSetSlice(p.dm.trainingSet, i))
    #     vsize = len(p.dm._getSetSlice(p.dm.validationSet, i))
    #     tssize = len(p.dm._getSetSlice(p.dm.testingSet, i))
    #     print('it', i, 'sizes:', trsize, vsize, tssize)
    except KeyboardInterrupt:
        pass
    finally:
        if not options.no_save and not gconfig.testing.enabled:
            p.saveNetwork(dryrun=False)
        pass

    print('done')


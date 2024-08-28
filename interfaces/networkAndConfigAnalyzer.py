import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import math, time, copy
from types import FunctionType
from typing import Callable
from tensorflow.keras.optimizers import Adam

from globalConfig import config as gconfig
from constants.enums import AccuracyType, ChangeType, OperatorDict
from constants.exceptions import InsufficientInstances
from constants.values import usExchanges
from interfaces.trainer import Trainer
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.neuralNetworkManager import NeuralNetworkManager
from managers.inputVectorFactory import InputVectorFactory
from structures.neuralNetworkInstance import NeuralNetworkInstance
from structures.sql.sqlArgumentObj import SQLArgumentObj
from utils.support import asList, shortc

nnm: NeuralNetworkManager = NeuralNetworkManager()
dbm: DatabaseManager = DatabaseManager()

class NetworkAndConfigAnalyzer:

    def __init__(self, network=None, networkId=None, networkGenerator=None, networkLabels=None, config=None, configLabels=None, useAllSets=False, maxPageSize=500, **trainingConfig):
        self.__useAllSets = useAllSets
        self.__maxPageSize = maxPageSize
        self.__trainingConfig = trainingConfig

        ## setup network(s)
        if not network and not networkId and not networkGenerator: raise ValueError('Network not specified in any manner')
        if networkId or network:
            if networkId:
                self.__network = [nnm.get(nid) for nid in asList(networkId)]
            elif network:
                self.__network = asList(network)
        elif networkGenerator:
            self.__network = asList(networkGenerator)
        self.__networkLabels = asList(networkLabels)
        if len(self.__network) != len(self.__networkLabels):
            if len(self.__networkLabels) == 0:
                self.__networkLabels = [i+1 for i in range(len(self.__network))]
            else:
                raise ValueError(f'Number of networks ({len(self.__network)}) does not match number of network labels ({len(networkLabels)})')

        ## setup config(s)
        if len(self.__network) > 1 and config:
            raise ValueError('Cannot combine multiple networks and configs')
        elif config:
            self.__config = asList(config)
            self.__configLabels = asList(configLabels)
            if len(self.__config) != len(self.__configLabels):
                if len(self.__configLabels) == 0:
                    self.__configLabels = [i+1 for i in range(len(self.__config))]
                else:
                    raise ValueError(f'Number of configs ({len(self.__config)}) does not match number of config labels ({len(configLabels)})')
        elif networkGenerator:
            self.__config = [gconfig for _ in self.__network]
        else:
            self.__config = [nn.config for nn in self.__network]

        if self.__useAllSets:
            if len(self.__network) > 1:   raise ValueError('Too many networks for useAllSets')
            if len(self.__config) > 1:    raise ValueError('Too many configs for useAllSets')

        self.__currentNetworkIndx = -1
        self.__currentConfigIndx = -1
        self.currentTrainer: Trainer = None
        self.dataManager: DataManager = None
        if len(self.__network) == 1 and len(self.__config) == 1:
            self._initializeTrainer(0, 0)

    def _initializeTrainer(self, networkIndx=None, configIndx=None, page=0):
        '''initialize/update dataManager and create new trainer for the current network/config'''

        ## check if already initialized
        if (len(self.__network) == 1 or (networkIndx is not None and self.__currentNetworkIndx == networkIndx)) and (len(self.__network) > 1 or (configIndx is not None and self.__currentConfigIndx == configIndx)) and self.currentTrainer is not None:
            return

        self.__currentNetworkIndx = shortc(networkIndx, self.__currentNetworkIndx)
        self.__currentConfigIndx = shortc(configIndx, self.__currentConfigIndx)
        network: NeuralNetworkInstance = self.__network[self.__currentNetworkIndx]
        config = self.__config[self.__currentConfigIndx]
        if type(network) in [Callable, FunctionType]:
            network = network(config, self.__trainingConfig)
        
        if self.dataManager:
            self.dataManager.setNewConfig(network.inputVectorFactory.config, page=page)
        else:
            self.dataManager: DataManager = DataManager.forTraining(inputVectorFactory=network.inputVectorFactory, useAllSets=self.__useAllSets, maxPageSize=self.__maxPageSize, **self.__trainingConfig)

        network.updateProperties(
            normalizationData=self.dataManager.normalizationData, useAllSets=useAllSets, seriesType=self.dataManager.seriesType,
            **self.__trainingConfig
        )

        self.currentTrainer = Trainer(network=network, useAllSets=self.__useAllSets, dataManager=self.dataManager, **self.__trainingConfig)

    def compareNetworks(self, **kwargs):
        '''compare different networks for the same data/training config'''
        metrics = []
        for nnindx in range(len(self.__network)):
            self._initializeTrainer(networkIndx=nnindx)
            self.currentTrainer.train(**kwargs)
            metrics.append(self.currentTrainer.network.getMetricsDict())
        
        for indx,nns in enumerate(metrics):
            print(f"Network '{self.__networkLabels[indx]}'")
            NeuralNetworkInstance.printMetrics(nns)
        
        return metrics

    def compareConfigs(self, iterations=1, **kwargs):
        '''compare different data/training configs for the same network'''
        skippedConfigs = []
        missedIterationConfigs = []
        configMetrics = [[] for i in range(len(self.__config))]

        if iterations == max:
            self._initializeTrainer(configIndx=0, page=0)
            iterations = self.dataManager.getSymbolListPageCount()
        for i in range(iterations):
            for cfindx in range(len(self.__config)):
                try:
                    self._initializeTrainer(configIndx=cfindx, page=i)
                    self.currentTrainer.train(**kwargs)
                    configMetrics[cfindx].append(self.currentTrainer.network.getMetricsDict())
                except InsufficientInstances:
                    pass
        
        for indx,cfs in enumerate(configMetrics):
            if not cfs:
                skippedConfigs.append(indx)
                continue
            if len(cfs) < iterations:
                missedIterationConfigs.append(indx)
            print(f"Config '{self.__configLabels[indx]}'")
            NeuralNetworkInstance.printMetrics(cfs, config=self.__config[indx])

        if skippedConfigs:
            print('Skipped below configs due to insufficient instances available')
            for cfindx in skippedConfigs:
                print(f'{cfindx+1} : {self.__configLabels[cfindx]}')

        if missedIterationConfigs:
            print('Below configs missed some iterations due to insufficient instances available')
            for cfindx in missedIterationConfigs:
                print(f'{cfindx+1} : {self.__configLabels[cfindx]}')                
        
        return configMetrics

if __name__ == '__main__':
    # useAllSets = True
    useAllSets = False
    gconfig.training.precedingRange = 60
    gconfig.training.followingRange = 10
    # gconfig.training.changeValue = 0.05
    # gconfig.training.changeType = ChangeType.PERCENTAGE
    gconfig.training.changeValue = 5
    gconfig.training.changeType = ChangeType.ENDING_ABSOLUTE

    gconfig.training.setSplitTuple = (0.80,0.20)
    explicitValidationSymbolList = []
    # gconfig.training.setSplitTuple = (0.99,0)
    # explicitValidationSymbolList = dbm.getSymbols(exchange='TSX', symbol='XQQ')
    iterations = max

    if gconfig.testing.enabled:
        ## testing
        setCount = 500
        minimumSetsPerSymbol = 0
    else:
        ## real
        setCount = 10000
        minimumSetsPerSymbol = 0

    ## network
    def generateNetwork1(config):
        precedingRange = config.training.precedingRange
        inputSize = None
        optimizer = Adam(amsgrad=True)
        if config.network.recurrent:
            staticSize, semiseriesSize, seriesSize = InputVectorFactory(config).getInputSize()
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
            inputSize = InputVectorFactory(config).getInputSize(precedingRange)
            layers = [
                # { 'units': math.floor(inputSize / 0.85), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.3), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.7), 'dropout': False, 'dropoutRate': 0.001 },
                { 'units': math.floor(inputSize / 2), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 2.5), 'dropout': False, 'dropoutRate': 0.001 },
            ]
        return nnm.createNetworkInstance(
            optimizer, layers, precedingRange=precedingRange, inputSize=inputSize
        )
    
    def generateNetwork2(config):
        precedingRange = config.training.precedingRange
        inputSize = None
        optimizer = Adam(amsgrad=True)
        if config.network.recurrent:
            staticSize, semiseriesSize, seriesSize = InputVectorFactory(config).getInputSize()
            layers = [
                [
                    { 'units': math.floor(staticSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(semiseriesSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(seriesSize * 3), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize*1.5), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor((staticSize + semiseriesSize + seriesSize) / 2), 'dropout': False, 'dropoutRate': 0.001 },
                ]
            ]
        else:
            inputSize = InputVectorFactory(config).getInputSize(precedingRange)
            layers = [
                # { 'units': math.floor(inputSize / 0.85), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.3), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.7), 'dropout': False, 'dropoutRate': 0.001 },
                { 'units': math.floor(inputSize / 2), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 2.5), 'dropout': False, 'dropoutRate': 0.001 },
            ]
        return nnm.createNetworkInstance(
            optimizer, layers, precedingRange=precedingRange, inputSize=inputSize
        )    

    def generateNetwork3(config):
        precedingRange = config.training.precedingRange
        inputSize = None
        optimizer = Adam(amsgrad=True)
        if config.network.recurrent:
            staticSize, semiseriesSize, seriesSize = InputVectorFactory(config).getInputSize()
            layers = [
                [
                    { 'units': math.floor(staticSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(semiseriesSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(seriesSize / 1), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize / 1.5), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize / 2), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize / 2.5), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize / 3), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor((staticSize + semiseriesSize + seriesSize) / 2), 'dropout': False, 'dropoutRate': 0.001 },
                ]
            ]
        else:
            inputSize = InputVectorFactory(config).getInputSize(precedingRange)
            layers = [
                # { 'units': math.floor(inputSize / 0.85), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.3), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.7), 'dropout': False, 'dropoutRate': 0.001 },
                { 'units': math.floor(inputSize / 2), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 2.5), 'dropout': False, 'dropoutRate': 0.001 },
            ]
        return nnm.createNetworkInstance(
            optimizer, layers, precedingRange=precedingRange, inputSize=inputSize
        )    

    def generateNetwork4(config):
        precedingRange = config.training.precedingRange
        inputSize = None
        optimizer = Adam(amsgrad=True)
        if config.network.recurrent:
            staticSize, semiseriesSize, seriesSize = InputVectorFactory(config).getInputSize()
            layers = [
                [
                    { 'units': math.floor(staticSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(semiseriesSize / 2), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor(seriesSize *3), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize *2.5), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize * 2), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize *1.5), 'dropout': False, 'dropoutRate': 0.001 },
                    { 'units': math.floor(seriesSize ), 'dropout': False, 'dropoutRate': 0.001 }
                ],
                [
                    { 'units': math.floor((staticSize + semiseriesSize + seriesSize) / 2), 'dropout': False, 'dropoutRate': 0.001 },
                ]
            ]
        else:
            inputSize = InputVectorFactory(config).getInputSize(precedingRange)
            layers = [
                # { 'units': math.floor(inputSize / 0.85), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.3), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 1.7), 'dropout': False, 'dropoutRate': 0.001 },
                { 'units': math.floor(inputSize / 2), 'dropout': False, 'dropoutRate': 0.001 },
                # { 'units': math.floor(inputSize / 2.5), 'dropout': False, 'dropoutRate': 0.001 },
            ]
        return nnm.createNetworkInstance(
            optimizer, layers, precedingRange=precedingRange, inputSize=inputSize
        )            

    ## configs
    configs = []
    cflabels = []

    for st in range(8):
        newcf = copy.deepcopy(gconfig)
        newcf.training.followingRange = int(5 * (st+1))
        newcf.training.changeValue = int(2 * (st+1))
        newcf.training.changeType = ChangeType.ENDING_ABSOLUTE
        configs.append(newcf)
        cflabels.append(f'{newcf.training.followingRange} day ${newcf.training.changeValue}')

        
    for st in range(8):
        newcf = copy.deepcopy(gconfig)
        newcf.training.followingRange = int(5 * (st+1))
        newcf.training.changeValue = 0.05 * (st+1)
        newcf.training.changeType = ChangeType.ENDING_PERCENTAGE
        configs.append(newcf)
        cflabels.append(f'{newcf.training.followingRange} day {newcf.training.changeValue*100:.2f}%')

    # newcf = copy.deepcopy(gconfig)
    # gconfig.training.followingRange = 5
    # gconfig.training.changeValue = 2
    # gconfig.training.changeType = ChangeType.ABSOLUTE
    # configs.append(newcf)
    # cflabels.append(f'5 day $2')

    # newcf = copy.deepcopy(gconfig)
    # gconfig.training.followingRange = 10
    # gconfig.training.changeValue = 4
    # gconfig.training.changeType = ChangeType.ABSOLUTE
    # configs.append(newcf)
    # cflabels.append(f'10 day $4')

    # newcf = copy.deepcopy(gconfig)
    # gconfig.training.followingRange = 5
    # gconfig.training.changeValue = 0.05
    # gconfig.training.changeType = ChangeType.PERCENTAGE
    # configs.append(newcf)
    # cflabels.append(f'5 day 5%')

    # newcf = copy.deepcopy(gconfig)
    # gconfig.training.followingRange = 10
    # gconfig.training.changeValue = 0.1
    # gconfig.training.changeType = ChangeType.PERCENTAGE
    # configs.append(newcf)
    # cflabels.append(f'10 day 10%')


    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.25
    # newcf.trainer.customValidationClassValueRatio = 0.25
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.25
    # newcf.trainer.customValidationClassValueRatio = 0.5
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.25
    # newcf.trainer.customValidationClassValueRatio = 0.75
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.5
    # newcf.trainer.customValidationClassValueRatio = 0.25
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.5
    # newcf.trainer.customValidationClassValueRatio = 0.5
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.5
    # newcf.trainer.customValidationClassValueRatio = 0.75
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.75
    # newcf.trainer.customValidationClassValueRatio = 0.25
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.75
    # newcf.trainer.customValidationClassValueRatio = 0.5
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')
    # newcf = copy.deepcopy(gconfig)
    # newcf.sets.positiveSplitRatio = 0.75
    # newcf.trainer.customValidationClassValueRatio = 0.75
    # configs.append(newcf)
    # cflabels.append(f'set ratio {newcf.sets.positiveSplitRatio}; value ratio {newcf.trainer.customValidationClassValueRatio}')

    pcr: NetworkAndConfigAnalyzer = NetworkAndConfigAnalyzer(
        # networkGenerator=[
        #     # generateNetwork1, generateNetwork2, 
        #     generateNetwork3, generateNetwork4],
        # networkLabels=[
        #     # 'baseline', 'big layers', 
        #     'more layers', 'big more layers'],
        network=generateNetwork1,
        config=configs,
        configLabels=cflabels,
        verbose=2,
        setCount=setCount,
        maxPageSize=500,
        accuracyType=AccuracyType.NEGATIVE,

        minimumSetsPerSymbol=minimumSetsPerSymbol,
        exchange=usExchanges,
        # exchange=['NYSE', 'NASDAQ', 'BATS'],
        # exchange='NASDAQ',
        assetType=['Stock', 'CS', 'CLA', 'CLB', 'CLC'],
        close=SQLArgumentObj(9.99, OperatorDict.GREATERTHAN),
        requireEarningsDates=True,

        maxGoogleInterestHandlers=0,
        useAllSets=useAllSets,
        explicitValidationSymbolList=explicitValidationSymbolList
    )

    startt = time.time()
    res1 = pcr.compareConfigs(validationType=AccuracyType.NEGATIVE, patience=7, iterations=iterations)

    print(f'Comparison took {time.time()-startt:.2f} seconds')

    print('done')


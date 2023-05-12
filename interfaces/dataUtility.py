import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, p_tqdm, random, numpy, numba
from functools import partial
from multiprocessing import shared_memory
from multiprocessing.managers import SharedMemoryManager
from typing import Dict, List

from globalConfig import config as gconfig
from constants.enums import IndicatorType, OutputClass
from constants.values import indicatorsKey
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.inputVectorFactory import InputVectorFactory
from structures.dataPointInstance import DataPointInstance
from structures.skipsObj import SkipsObj
from utils.other import getInstancesByClass, parseCommandLineOptions
from utils.support import asISOFormat, asList, tqdmLoopHandleWrapper
from utils.vectorSimilarity import euclideanSimilarity_jit

maxcpus = 3

'''
Determines the Euclidean similarity between input vectors for all negative instances of each ticker, writes resulting (sum) to DB
Input vector must only contain positive numbers, negatives may slightly change how accurate the similarity calculation is
Can be interuptted and resumed, and should be able to handle new stock data addition to existing calculated values
'''
def determineSimilarities(exchange=[], parallel=True, correctionRun=False, dryrun=False):
    parallel = parallel and not correctionRun and not dryrun

    ## remove unnecessary/redundant features
    ## only keep EMA200, since all are based on stock data, which is already included...and to not break stuff by having no indicators
    cf = gconfig
    for ind in IndicatorType.getActuals():
        cf.feature[indicatorsKey][ind].enabled = False
    cf.feature[indicatorsKey][IndicatorType.EMA200].enabled = True

    cf.feature.dayOfWeek.enabled = False
    cf.feature.dayOfMonth.enabled = False
    cf.feature.monthOfYear.enabled = False

    props = {
        'precedingRange': 60,
        'followingRange': 10,
        'threshold': 0.05
    }

    dm: DataManager = DataManager.forAnalysis(
        skips=SkipsObj(sets=True),
        saveSkips=True,
        skipAllDataInitialization=True,
        **props,
        maxPageSize=1,
        # exchanges=['NASDAQ'],
        exchanges=asList(exchange),

        inputVectorFactory=InputVectorFactory(cf),
        verbose=0.5
    )

    normalizationInfo = dm.normalizationInfo
    tickerList = dm.symbolList

    if parallel:
        with SharedMemoryManager() as smm:
            sharedmem = smm.ShareableList([0 for x in range(maxcpus)])

            p_tqdm.p_umap(partial(_calculateSimiliaritesAndInsertToDB, props=props, config=cf, normalizationInfo=normalizationInfo, cpuCoreUsage_sharedMemoryName=sharedmem.shm.name, correctionRun=correctionRun, dryrun=dryrun), tickerList, num_cpus=maxcpus, position=0, desc='Tickers')

    else: ## serial
        # for ticker in tqdm.tqdm(tickerList[217:], desc='Tickers'):
        for ticker in tqdm.tqdm(tickerList, desc='Tickers'):
            _calculateSimiliaritesAndInsertToDB(ticker, props, cf, normalizationInfo, correctionRun=correctionRun, dryrun=dryrun)

@numba.njit(numba.float64[:](numba.float64[:], numba.i8, numba.float64[:, :], numba.boolean), parallel=True)
def _calculateSimiliarites(similaritiesSum:List[float], startindex, vectors, dryrun): ## eliminate loophandle
    ## numba.jit does not support tqdm loop wrappers
    for cindx in range(startindex, len(vectors)):
    # for cindx in tqdm.tqdm(range(startindex, len(vectors)), desc='Columns'):
        vector = vectors[cindx]

        ## calculate similarites for each row
        similarities = numpy.zeros(cindx)
        for rindx in range(0, cindx):
            if not dryrun:
                calculatedValue = euclideanSimilarity_jit(vector, vectors[rindx])
            else:
                calculatedValue = random.randint(0,100)

            similarities[rindx] = calculatedValue

        ## add similarites to running sums
        for sindx in range(len(similarities)):
            similaritiesSum[sindx] += similarities[sindx]
        
        ## sum similarities for current index
        similaritiesSum[cindx] = sum(similarities)
    
    return similaritiesSum

def _calculateSimiliaritesAndInsertToDB(ticker, props: Dict, config, normalizationInfo, cpuCoreUsage_sharedMemoryName=None, correctionRun=False, dryrun=False):
    dbm: DatabaseManager = DatabaseManager()
    dm: DataManager = DataManager(
        skips=SkipsObj(sets=True),
        saveSkips=True,
        skipAllDataInitialization=True,
        **props,
        maxPageSize=1,
        analysis=True,
        
        normalizationInfo=normalizationInfo,
        symbolList=[ticker],
        inputVectorFactory=InputVectorFactory(config),
        verbose=0
    )

    parallel = cpuCoreUsage_sharedMemoryName
    if parallel:
        cpuCoreUsage = shared_memory.ShareableList(name=cpuCoreUsage_sharedMemoryName)
        pid = cpuCoreUsage.index(0)
        cpuCoreUsage[pid] = 1 ## lock index for progress bar position

    keyboardinterrupted = False
    maxpage = dm.getSymbolListPageCount()
    for i in range(maxpage):
        ## only iterating one SDH at a time
        dm.initializeAllDataForPage(i+1)
        ticker = list(dm.stockDataHandlers.keys())[0]

        neginstances = getInstancesByClass(dm.stockDataInstances.values())[1]
        def getDTArg(indx): ## specifically for neg instances
            return dm.stockDataHandlers[ticker].data[neginstances[indx].index].date

        ## prepare get/insert arguments
        def prepareArgs(indx=None):
            return {
                'exchange': ticker.exchange,
                'symbol': ticker.symbol,
                'dtype': dm.seriesType,
                'dt': getDTArg(indx) if indx is not None else None,
                'vclass': OutputClass.NEGATIVE,
                **props
            }

        similaritiesSum = numpy.zeros(len(neginstances))
        ## load already calculated sums from DB
        if not dryrun or correctionRun:
            dbsums = dbm.getVectorSimilarity(**prepareArgs())
            for dbsumindx in range(len(dbsums)):
                similaritiesSum[dbsumindx] = dbsums[dbsumindx].value
            if not parallel and len(dbsums) > 0: print(f'Loaded {len(dbsums)} values')
        else: dbsums = []

        ## temporary: correct already calculated data that was not inserted to DB with correct dates (used overall index rather than neginstance index)
        if correctionRun:
            dbsumCount = len(dbsums)
            if dbsumCount == 0:
                ## no data, no correction required
                continue
            else: ## some data
                dbsumLastDate = dbsums[dbsumCount-1].date
                stockDataDate = dm.stockDataHandlers[ticker].data[dbsumCount-1].date
                if dbsumLastDate == stockDataDate:
                    print(ticker.getTuple(), 'needs correction')
                    for dindx in range(dbsumCount-1, -1, -1): ## run in reverse so there are no conflicts with yet-to-be-corrected data rows
                        newDate = getDTArg(dindx)
                        oldDate = dm.stockDataHandlers[ticker].data[dindx].date
                        if not dryrun:
                            args = [asISOFormat(newDate), ticker.exchange, ticker.symbol, dm.seriesType.name, asISOFormat(oldDate), OutputClass.NEGATIVE.name, *list(props.values())]
                            dbm.dbc.execute('UPDATE historical_vector_similarity_data SET date=? WHERE exchange=? AND symbol=? AND date_type=? AND date=? AND vector_class=? AND preceding_range=? AND following_range=? AND change_threshold=?', tuple(args))
                        else:
                            print(oldDate, '->', newDate)

                else:
                    print(ticker.getTuple(), 'is good')
            continue

        ## skip if everything already calculated
        startindex = len(dbsums)
        if startindex == len(neginstances): continue

        try:
            ## loop calculating by column, then adding to running row sums for each


            ## progress bars do not maintain position properly, jumps around and overwrite each other, especially if maxcpus > 2
            ## tqdm issue is open with some possible workaround for linux but at this time does not sound like it for windows
            ## https://github.com/tqdm/tqdm/issues/1000
            # loopkwargs = {
            #     'verbose': (0.5 if pid<1 else 0) if parallel else 0.5,
            #     'desc': f'Core #{pid+1} Columns POS {(pid+1)*len(cpuCoreUsage)}' if parallel else 'Columns',
            #     'position': (pid+1) if parallel else 0
            # }
            # loopHandle = tqdmLoopHandleWrapper(range(startindex, len(neginstances)), **loopkwargs)

            ## series portion only
            neginstancevectors = numpy.zeros((len(neginstances), dm.inputVectorFactory.getInputSize()[2]*dm.precedingRange))
            for nindx in tqdm.tqdm(range(len(neginstances)), desc='Building input vectors', leave=False):
                neginstancevectors[nindx] = neginstances[nindx].getInputVector()[2]

            similaritiesSum = _calculateSimiliarites(similaritiesSum, startindex, neginstancevectors, dryrun)

            # ## old method, for sequential/parallel (not jit) using regular lists/appends
            # for cindx in tqdmLoopHandleWrapper(range(startindex, len(neginstances)), **loopkwargs):
            #     ci = neginstances[cindx]
            #     vector = ci.getInputVector()[2] ## series portion

            #     ## calculate similarites for each row
            #     similarities = []
            #     # for rindx in tqdm.tqdm(range(0, cindx), desc=f'{pid} Rows', leave=False, position=(pid+2)*len(cpuCoreUsage)):
            #     for rindx in range(0, cindx): ## parallel above, this temporary until tqdm lines are fixed
            #     # for rindx in tqdm.tqdm(range(0, cindx), desc='Rows', leave=False): ## serial
            #         ri = neginstances[rindx]
            #         if not dryrun:
            #             calculatedValue = euclideanSimilarity_jit(vector, ri.getInputVector()[2])
            #         else:
            #             calculatedValue = random.randint(0,100)

            #         similarities.append(calculatedValue)

            #     ## add similarites to running sums
            #     for sindx in range(len(similarities)):
            #         similaritiesSum[sindx] += similarities[sindx]
                
            #     ## sum similarities for current index
            #     similaritiesSum.append(sum(similarities))
        except KeyboardInterrupt:
            keyboardinterrupted = True

        if not dryrun:
            pass
            dbm.startBatch()
            for vsindx in range(numpy.count_nonzero(similaritiesSum)): ## only iterate through calculated values, filled 0 values indicate otherwise
                dbm.insertVectorSimilarity(*prepareArgs(vsindx).values(), similaritiesSum[vsindx], upsert=True)
            dbm.commitBatch()
        else:
            pass


        if keyboardinterrupted: break

    if parallel: cpuCoreUsage[pid] = 0 ## unlock index for progress bar position

if __name__ == '__main__':
    opts, kwargs = parseCommandLineOptions()
    if opts.function:
        locals()[opts.function](**kwargs)
    else:
        similarityCalculationAndInsertion(parallel=False)
        # similarityCalculationAndInsertion()
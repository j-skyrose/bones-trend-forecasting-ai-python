import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, p_tqdm, random, numpy, numba
from datetime import date, timedelta
from functools import partial
from multiprocessing import shared_memory
from multiprocessing.managers import SharedMemoryManager
from typing import Dict, List

from globalConfig import config as gconfig
from constants.enums import FeatureExtraType, IndicatorType, OutputClass, SeriesType
from constants.exceptions import InsufficientDataAvailable
from constants.values import indicatorsKey, unusableSymbols
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.inputVectorFactory import InputVectorFactory
from managers.marketDayManager import MarketDayManager
from structures.skipsObj import SkipsObj
from utils.other import buildCommaSeparatedTickerPairString, getIndicatorPeriod, getInstancesByClass, parseCommandLineOptions
from utils.support import asISOFormat, asList, tqdmLoopHandleWrapper, tqdmProcessMapHandlerWrapper
from utils.technicalIndicatorFormulae import generateADXs_AverageDirectionalIndex, generateATRs_AverageTrueRange, generateBollingerBands, generateCCIs_CommodityChannelIndex, generateDIs_DirectionalIndicator, generateEMAs_ExponentialMovingAverage, generateMACDs_MovingAverageConvergenceDivergence, generateRSIs_RelativeStrengthIndex, generateSuperTrends, unresumableGenerationIndicators
from utils.vectorSimilarity import euclideanSimilarity_jit

dbm: DatabaseManager = DatabaseManager()

maxcpus = 3

'''
Determines the Euclidean similarity between input vectors for all negative instances of each ticker, writes resulting (sum) to DB
Input vector must only contain positive numbers, negatives may slightly change how accurate the similarity calculation is
Can be interuptted and resumed, and should be able to handle new stock data addition to existing calculated values
'''
def similarityCalculationAndInsertion(exchange=[], parallel=True, correctionRun=False, dryrun=False):
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

    ## prevent instance reduction
    cf.sets.instanceReduction.enabled = False

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
        # exchange=['NASDAQ'],
        exchange=asList(exchange),

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
                'seriesType': dm.seriesType,
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
    
    print(f' {"Would insert" if dryrun else "Inserted"} {numpy.count_nonzero(similaritiesSum)-len(dbsums)} new values and {"would update" if dryrun else "updated"} {len(dbsums)} values for', ticker.getTuple())


def _multicore_updateTechnicalIndicatorData(ticker, seriesType: SeriesType, cacheIndicators, indicatorConfig):
    localdbm = DatabaseManager()
    latestIndicators = localdbm.dbc.execute('''
        SELECT MAX(date) AS date, exchange, symbol, indicator, period, value FROM historical_calculated_technical_indicator_data WHERE date_type=? AND exchange=? AND symbol=? group by exchange, symbol, indicator, period
    ''', (seriesType.name, ticker.exchange, ticker.symbol)).fetchall()
    def getLatestIndicator(i: IndicatorType, period):
        for li in latestIndicators:
            if li.indicator == i.key and li.period == period:
                return li

    ## data should already be in ascending (date) order
    stkdata = localdbm.getStockData(ticker.exchange, ticker.symbol, SeriesType.DAILY)

    ## skip if everything is already updated
    missingIndicators = []
    notuptodateIndicators = []
    if len(latestIndicators) > 0:
        ## check if any indicators are missing in DB
        for ik in IndicatorType:
            missing = True
            for r in latestIndicators:
                if r.indicator == ik.key:
                    missing = False
                    break
            if missing: missingIndicators.append(ik)
        ## check if all indicators are calculated up to latest stock data
        for r in latestIndicators:
            if r.date < stkdata[-1].date:
                notuptodateIndicators.append(IndicatorType[r.indicator])
        if len(missingIndicators) == 0 and len(notuptodateIndicators) == 0: return 0

    returntpls = []
    i: IndicatorType
    for i in cacheIndicators:
        iperiod = getIndicatorPeriod(i, indicatorConfig)

        ## generate fresh/all data (some indicators use smoothing so their initial values contribute to their latest, meaning they cannot be 'picked up where they left off')
        if i in missingIndicators or (i in notuptodateIndicators and i in unresumableGenerationIndicators):
            try:
                if i.isEMA():
                    indcdata = generateEMAs_ExponentialMovingAverage(stkdata, iperiod)
                elif i == IndicatorType.RSI:
                    indcdata = generateRSIs_RelativeStrengthIndex(stkdata, iperiod)
                elif i == IndicatorType.CCI:
                    indcdata = generateCCIs_CommodityChannelIndex(stkdata, iperiod)
                elif i == IndicatorType.ATR:
                    indcdata = generateATRs_AverageTrueRange(stkdata, iperiod)
                elif i == IndicatorType.DIS:
                    indcdata = list(zip(
                        generateDIs_DirectionalIndicator(stkdata, iperiod),
                        generateDIs_DirectionalIndicator(stkdata, iperiod, positive=False)
                    ))
                elif i == IndicatorType.ADX:
                    indcdata = generateADXs_AverageDirectionalIndex(stkdata, iperiod)
                elif i == IndicatorType.MACD:
                    indcdata = generateMACDs_MovingAverageConvergenceDivergence(stkdata)
                elif i == IndicatorType.BB:
                    indcdata = generateBollingerBands(stkdata, iperiod)
                elif i == IndicatorType.ST:
                    indcdata = generateSuperTrends(stkdata, iperiod)
            except InsufficientDataAvailable:
                continue

        ## only generate missing values
        elif i in notuptodateIndicators:
            latesti = getLatestIndicator(i, iperiod)   

            minDateIndex = 0
            for j in range(len(stkdata)-1, -1, -1):
                if stkdata[j].date == latesti.date:
                    minDateIndex = j
                    break

            if i.isEMA():
                indcdata = generateEMAs_ExponentialMovingAverage(stkdata[minDateIndex-1:], iperiod, usingLastEMA=latesti.value)
            elif i == IndicatorType.CCI:
                ## TODO: not currently cached
                indcdata = generateCCIs_CommodityChannelIndex(stkdata, iperiod)
            elif i == IndicatorType.MACD:
                ## TODO: not currently cached
                indcdata = generateMACDs_MovingAverageConvergenceDivergence(stkdata)
            elif i == IndicatorType.BB:
                indcdata = generateBollingerBands(stkdata[minDateIndex-iperiod+1:], iperiod)

        else: ## already up to date
            continue

        ## convert generated values to DB tuples in proper chronological order
        tpls = []
        for indx in range(len(indcdata)):
            val = indcdata[-(indx+1)]
            if i.featureExtraType == FeatureExtraType.MULTIPLE:
                if i == IndicatorType.ST:
                    val = ','.join([str(val[0]), val[1].name])
                else:
                    val = ','.join([str(v) for v in val])

            tpls.append((ticker.exchange, ticker.symbol, seriesType.name, stkdata[-(indx+1)].date, i.key, iperiod, val))

        tpls.reverse()
        returntpls.extend(tpls)

    return returntpls

## generates or updates cached technical indicator data; should be run after every stock data dump
def technicalIndicatorDataCalculationAndInsertion(exchange=[], seriesType: SeriesType=SeriesType.DAILY, indicatorConfig=gconfig.defaultIndicatorFormulaConfig, doNotCacheADX=True):
    exchange = asList(exchange)
    tickers = dbm.dbc.execute('''
        SELECT MAX(date) AS date, exchange, symbol FROM historical_data WHERE type=? {} group by exchange, symbol
    '''.format(
            ('AND exchange IN (\'{}\')'.format('\',\''.join(exchange))) if len(exchange)>0 else ''
        ), (seriesType.name,)).fetchall()
    print('Got {} tickers'.format(len(tickers)))

    purgedCount = len(tickers)
    ## purge invalid/inappropriate tickers
    tickers[:] = [t for t in tickers if (t.exchange, t.symbol) not in unusableSymbols]
    purgedCount -= len(tickers)
    print('Purged {} tickers'.format(purgedCount))

    tickersupdated = 0
    rowsadded = 0
    cacheIndicators: List = gconfig.cache.indicators
    if doNotCacheADX: cacheIndicators.remove(IndicatorType.ADX)

    inserttpls = []
    for tpls in tqdmProcessMapHandlerWrapper(partial(_multicore_updateTechnicalIndicatorData, seriesType=seriesType, cacheIndicators=cacheIndicators, indicatorConfig=indicatorConfig), tickers, verbose=1, desc='Updating techInd data for tickers'):
        if len(tpls) != 0:
            rowsadded += len(tpls)
            tickersupdated += 1
            inserttpls.extend(tpls)
    
    dbm.dbc.executemany('''
        INSERT OR REPLACE INTO historical_calculated_technical_indicator_data VALUES (?,?,?,?,?,?,?)
    ''', inserttpls)

    print('Updated {} tickers'.format(tickersupdated))
    print('Added or replaced {} rows'.format(rowsadded))


## helper function to fillHistoricalGaps
def _getDailyHistoricalGaps(exchange=None, symbol=None, autoUpdateDamagedSymbols=True, verbose=1):
    ALL = not (exchange and symbol)

    results = dbm.getHistoricalStartEndDates(exchange, symbol)
    if verbose>=2: print('result count', len(results))

    dateGaps = {} if ALL else []
    damagedTickers = set()
    for rerun in range(2):
        for r in tqdmLoopHandleWrapper(results, verbose%2, desc='Determining DAILY historical gaps'):
            if (r.exchange, r.symbol) in unusableSymbols or (r.exchange, r.symbol) in damagedTickers: continue

            data = dbm.getStockData(r.exchange, r.symbol, SeriesType.DAILY)
            startDate = date.fromisoformat(r.start)
            endDate = date.fromisoformat(r.finish)
            if verbose>=2: 
                print('###############################################')
                print(r.exchange, r.symbol)
                print(startDate, ' -> ', endDate)

            dindex = 0
            cyear = 0
            holidays = []
            consecgaps = 0
            for d in range(int((endDate - startDate).total_seconds() / (60 * 60 * 24))):
                cdate = startDate + timedelta(days=d)
                if verbose>=2: print('Checking', cdate)
                if cdate.weekday() > 4: # is Saturday (5) or Sunday (6)
                    if verbose>=2: print('is weekend')
                    continue

                ## holiday checker
                if cyear != cdate.year:
                    holidays = MarketDayManager.getMarketHolidays(cdate.year, r.exchange)
                    cyear = cdate.year
                    if verbose>=2: print('holidays for', cyear, holidays)
                if cdate in holidays:
                    if verbose>=2: print('is holiday')
                    continue

                ## actual gap checker
                if cdate != date.fromisoformat(data[dindex].date):
                    if verbose>=2: 
                        ddt = date.fromisoformat(data[dindex].date)
                        print('is gap')
                    if ALL:
                        try:
                            dateGaps[cdate].append((r.exchange, r.symbol))
                        except KeyError:
                            dateGaps[cdate] = [(r.exchange, r.symbol)]
                    else:
                        dateGaps.append(cdate)
                    consecgaps += 1

                    if consecgaps > 75: 
                        damagedTickers.add((r.exchange, r.symbol))
                else:
                    dindex += 1
                    consecgaps = 0

        if len(damagedTickers) == 0:
            break
        else:
            if verbose>=1: print(buildCommaSeparatedTickerPairString(damagedTickers))
            if autoUpdateDamagedSymbols and rerun == 0:
                if verbose>=1: print('Consecutive gaps too big for some symbols')

                ## update damagedSymbols variable, written directly to the constants/values file, then re-determine gaps omitting these tickers
                newfile = ''
                valuesFile = os.path.join(path, 'constants', 'values') + '.py'
                with open(valuesFile, 'r') as f:
                    autoWrittenLineIsNext=False
                    for line in f:
                        if line.startswith('## AUTO-WRITTEN - DO NOT REMOVE OR CHANGE THIS OR NEXT TWO LINES'):
                            autoWrittenLineIsNext = True
                        elif autoWrittenLineIsNext:
                            ## parse existing tickers, ensure no duplicates when appending damagedTickers
                            line = line[:-1].replace(',(','')
                            tickers = line.split(')')
                            for tindx in range(len(tickers)):
                                tickers[tindx] = (*tickers[tindx].replace('\'','').split(','),)
                            newDamagedTickers = set()
                            for t in tickers:
                                newDamagedTickers.add(t)
                            for t in damagedTickers:
                                newDamagedTickers.add(t)

                            line = buildCommaSeparatedTickerPairString(newDamagedTickers) + '\n'
                            autoWrittenLineIsNext = False
                        newfile += line
                with open(valuesFile, 'w') as f:
                    f.write(newfile)

                ## reset gaps so next iteration will re-build, excluding damaged symbols
                dateGaps = {} if ALL else []

            else:
                raise Exception('consecutive gaps too big for some symbols')

    return dateGaps

## generally only used after large data acquisitions/dumps
## fill any data gaps with artificial data using last real trading day
def historicalGapCalculationAndInsertion(exchange=None, symbol=None, seriesType=SeriesType.DAILY, dryrun=False, autoUpdateDamagedSymbols=True, verbose=1):
    ALL = not (exchange and symbol)
    tuples = []
    gaps = []
    if seriesType == SeriesType.DAILY:
        gaps = _getDailyHistoricalGaps(exchange, symbol, autoUpdateDamagedSymbols=autoUpdateDamagedSymbols, verbose=verbose)

    if len(gaps) == 0:
        if verbose>=1: print('No gaps found')
    else:
        for g in tqdmLoopHandleWrapper(gaps, verbose, desc='Determining historical gap fillers for ' + seriesType.name):
            for t in tqdmLoopHandleWrapper(gaps[g], verbose-0.5, desc=str(g)) if ALL else [(exchange, symbol)]:
                if (t[0], t[1]) in unusableSymbols: continue
                ## find closest date without going over
                prevclose = None
                for d in dbm.getStockData(t[0], t[1], seriesType):
                    if date.fromisoformat(d.date) > g: break
                    prevclose = d.close
                tuples.append((t[0], t[1], seriesType.name, str(g), prevclose, prevclose, prevclose, prevclose, 0, True))

        if len(tuples) == 0:
            if verbose>=1: print('No filling required')
        else:
            if verbose>=1: print('Writing gap fillers to database')
            if not dryrun:
                dbm.insertHistoricalData(tuples)
            elif verbose>=1:
                ## count number of gaps for each ticker
                sumdict = {}
                for t in tuples:
                    sumdict[(t[0], t[1])] = 0
                for t in tuples:
                    sumdict[(t[0], t[1])] += 1

                ## print first handful of gaps for each ticker
                sumdict = dict(sorted(sumdict.items(), key=lambda item: item[1]))
                for tk, v in sumdict.items():
                    print(tk, v)
                    c = 0
                    for t in tuples:
                        if (t[0], t[1]) == tk:
                            print(t)
                            c+=1
                        if c > 4:
                            break


if __name__ == '__main__':
    opts, kwargs = parseCommandLineOptions()
    if opts.function:
        locals()[opts.function](**kwargs)
    else:
        similarityCalculationAndInsertion(parallel=False)
        # similarityCalculationAndInsertion()
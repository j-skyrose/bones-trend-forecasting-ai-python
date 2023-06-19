import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, numpy, numba
from datetime import date, timedelta
from functools import partial
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
from utils.types import TickerKeyType
from utils.technicalIndicatorFormulae import generateADXs_AverageDirectionalIndex, generateATRs_AverageTrueRange, generateBollingerBands, generateCCIs_CommodityChannelIndex, generateDIs_DirectionalIndicator, generateEMAs_ExponentialMovingAverage, generateMACDs_MovingAverageConvergenceDivergence, generateRSIs_RelativeStrengthIndex, generateSuperTrends, unresumableGenerationIndicators
from utils.vectorSimilarity import euclideanSimilarity_jit

dbm: DatabaseManager = DatabaseManager()

maxcpus = 3

'''
Determines the Euclidean similarity between input vectors for all negative instances of each ticker, writes resulting (sum) to DB
Input vector must only contain positive numbers, negatives may slightly change how accurate the similarity calculation is
Can be interuptted and resumed, and should be able to handle new stock data addition to existing calculated values
'''
def similarityCalculationAndInsertion(exchange=None, **kwargs):
    '''KWARGS: checkDBIntegrity, wipeDataOnDBIntegrityFailure, correctImproperlyInsertedDates, dryrun, freshrun'''
    ''' DB Integrity gets messed up when stock data is updated (or possibly due to a [local] symbol lookup bug); just something that needs to be dealt with whenever updating vector similarities
            alphavantage: high/low/close/volume values can change possibly because the previous last day may not have gone til end of after-market trading
                Data mismatch found for TSX FST
                {'exchange': 'TSX', 'symbol': 'FST', 'type': 'DAILY', 'date': '2023-05-19', 'open': 43.24, 'high': 43.24, 'low': 43.14, 'close': 43.24, 'volume': 460.0}
                {'exchange': 'TSX', 'symbol': 'FST', 'type': 'DAILY', 'date': '2023-05-19', 'open': 43.24, 'high': 43.26, 'low': 43.14, 'close': 43.26, 'volume': 500.0}
            polygon: unknown reason
    '''
    
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

    normalizationData = dm.normalizationData
    tickerList = dm.symbolList

    # for ticker in tqdm.tqdm(tickerList[217:], desc='Tickers'):
    for ticker in tqdm.tqdm(tickerList, desc='Tickers'):
        _calculateSimiliaritesAndInsertToDB(ticker, props, cf, normalizationData, **kwargs)

@numba.njit(numba.float64[:](numba.float64[:], numba.i8, numba.float64[:, :]), parallel=True)
def _calculateSimiliarites(similaritiesSum:List[float], startindex, vectors):
    ## numba.jit does not support tqdm loop wrappers
    for cindx in range(startindex, len(vectors)):
    # for cindx in tqdm.tqdm(range(startindex, len(vectors)), desc='Columns'):
        vector = vectors[cindx]

        ## calculate similarites for each row
        similarities = numpy.zeros(cindx)
        for rindx in range(0, cindx):
            calculatedValue = euclideanSimilarity_jit(vector, vectors[rindx])
            similarities[rindx] = calculatedValue

        ## add similarites to running sums
        for sindx in range(len(similarities)):
            similaritiesSum[sindx] += similarities[sindx]
        
        ## sum similarities for current index
        similaritiesSum[cindx] = sum(similarities)
    
    return similaritiesSum

def _calculateSimiliaritesAndInsertToDB(ticker, props: Dict, config, normalizationData, checkDBIntegrity=False, wipeDataOnDBIntegrityFailure=False, correctImproperlyInsertedDates=False, dryrun=False, freshrun=False):
    dm: DataManager = DataManager(
        skips=SkipsObj(sets=True),
        saveSkips=True,
        **props,
        maxPageSize=1,
        analysis=True,
        
        normalizationData=normalizationData,
        symbolList=[ticker],
        inputVectorFactory=InputVectorFactory(config),
        verbose=0
    )

    ticker = TickerKeyType.fromDict(ticker)
    neginstances = getInstancesByClass(dm.stockDataInstances.values())[1]
    def getDTArg(indx): ## specifically for neg instances
        return dm.stockDataHandlers[ticker].data[neginstances[indx].index].period_date

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
    dbsums = []
    def clearDataDueToIntegrityFailure():
        nonlocal dbsums
        print(f' DB integrity check failed for {ticker.getTuple()}, wiping data')
        dbsums = []
        if not dryrun: dbm.deleteVectorSimilarities(**prepareArgs())
    if checkDBIntegrity or not freshrun:
        try:
            dbsums = dbm.getVectorSimilarity(**prepareArgs())
            for dbsumindx in range(len(dbsums)):
                similaritiesSum[dbsumindx] = dbsums[dbsumindx].value
            ## load done
        except IndexError as e:
            if not checkDBIntegrity and not wipeDataOnDBIntegrityFailure: raise e
            if wipeDataOnDBIntegrityFailure:
                print(f' Missing date {dbsums[dbsumindx].date}')
                clearDataDueToIntegrityFailure()
            else: ## i.e. checkDBIntegrity = True
                print(f' For {ticker.getTuple()}')
                ## determine which date(s) are missing
                neginstanceDates = set()
                for nindx in range(len(neginstances)):
                    neginstanceDates.add(getDTArg(nindx))
                for dbsumindx in range(len(dbsums)):
                    if dbsums[dbsumindx].date not in neginstanceDates:
                        print(f'{dbsums[dbsumindx].date} not in negative instances, dbsums index {dbsumindx}')

        ## start/end date integrity checks
        if len(dbsums) > 0 and (checkDBIntegrity or wipeDataOnDBIntegrityFailure):
            integrityError = False
            if dbsums[0].date != getDTArg(0):
                print(f'Start dates do not align - DB {dbsums[0].date} vs NegInst {getDTArg(0)}')
                integrityError = True
            if len(dbsums) == len(neginstances):
                if dbsums[-1].date != getDTArg(-1): 
                    print(f'End dates do not align - DB {dbsums[-1].date} vs NegInst {getDTArg(-1)}')
                    integrityError = True

            if checkDBIntegrity: return
            if integrityError and wipeDataOnDBIntegrityFailure: clearDataDueToIntegrityFailure()
        if checkDBIntegrity: return

    ## correct already calculated data that was not inserted to DB with correct dates (used overall index rather than neginstance index) [limited use now, corrections already done as of May 25, 2023]
    if correctImproperlyInsertedDates:
        dbsumCount = len(dbsums)
        if dbsumCount == 0:
            ## no data, no correction required
            return
        else: ## some data
            dbsumLastDate = dbsums[dbsumCount-1].date
            stockDataDate = dm.stockDataHandlers[ticker].data[dbsumCount-1].period_date
            if dbsumLastDate == stockDataDate:
                print(ticker.getTuple(), 'needs correction')
                for dindx in range(dbsumCount-1, -1, -1): ## run in reverse so there are no conflicts with yet-to-be-corrected data rows
                    newDate = getDTArg(dindx)
                    oldDate = dm.stockDataHandlers[ticker].data[dindx].period_date
                    if not dryrun:
                        args = [asISOFormat(newDate), ticker.exchange, ticker.symbol, dm.seriesType.name, asISOFormat(oldDate), OutputClass.NEGATIVE.name, *list(props.values())]
                        dbm.dbc.execute('UPDATE historical_vector_similarity_data SET date=? WHERE exchange=? AND symbol=? AND date_type=? AND date=? AND vector_class=? AND preceding_range=? AND following_range=? AND change_threshold=?', tuple(args))
                    else:
                        print(oldDate, '->', newDate)

            else:
                print(ticker.getTuple(), 'is good')
        return

    ## skip if everything already calculated
    startindex = len(dbsums)
    if startindex == len(neginstances): return

    if len(dbsums) > 0: print(f' Loaded {len(dbsums)} values for', ticker.getTuple())

    ## loop calculating by column, then adding to running row sums for each
    ## series portion only
    neginstancevectors = numpy.zeros((len(neginstances), dm.inputVectorFactory.getInputSize()[2]*dm.precedingRange))
    for nindx in tqdm.tqdm(range(len(neginstances)), desc='Building input vectors', leave=False):
        neginstancevectors[nindx] = neginstances[nindx].getInputVector()[2]

    similaritiesSum = _calculateSimiliarites(similaritiesSum, startindex, neginstancevectors)

    if not dryrun:
        dbm.startBatch()
        for vsindx in range(numpy.count_nonzero(similaritiesSum)): ## only iterate through calculated values, filled 0 values indicate otherwise
            dbm.insertVectorSimilarity(*prepareArgs(vsindx).values(), similaritiesSum[vsindx], upsert=True)
        dbm.commitBatch()

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
            if r.date < stkdata[-1].period_date:
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
                if stkdata[j].period_date == latesti.date:
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

            tpls.append((ticker.exchange, ticker.symbol, seriesType.name, stkdata[-(indx+1)].period_date, i.key, iperiod, val))

        tpls.reverse()
        returntpls.extend(tpls)

    return returntpls

## generates or updates cached technical indicator data; should be run after every stock data dump
def technicalIndicatorDataCalculationAndInsertion(exchange=[], seriesType: SeriesType=SeriesType.DAILY, indicatorConfig=gconfig.defaultIndicatorFormulaConfig, doNotCacheADX=True):
    exchange = asList(exchange)
    tickers = dbm.dbc.execute('''
        SELECT MAX(period_date) AS date, exchange, symbol FROM historical_data WHERE series_type=? {} group by exchange, symbol
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
    currentDamagedTickers = set()
    lastDamagedTickers = set()
    for rerun in range(2):
        for r in tqdmLoopHandleWrapper(results, verbose%2, desc='Determining DAILY historical gaps'):
            if (r.exchange, r.symbol) in unusableSymbols or (r.exchange, r.symbol) in lastDamagedTickers: continue

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
                if cdate != date.fromisoformat(data[dindex].period_date):
                    if verbose>=2: 
                        ddt = date.fromisoformat(data[dindex].period_date)
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
                        currentDamagedTickers.add((r.exchange, r.symbol))
                else:
                    dindex += 1
                    consecgaps = 0

        if len(currentDamagedTickers) == 0:
            break
        else:
            if verbose>=1: print(buildCommaSeparatedTickerPairString(currentDamagedTickers))
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
                            tickers = line.split(')')[:-1] ## drop empty
                            for tindx in range(len(tickers)):
                                tickers[tindx] = (*tickers[tindx].replace('\'','').split(','),)
                            newDamagedTickers = set()
                            for t in tickers:
                                newDamagedTickers.add(t)
                            for t in currentDamagedTickers:
                                newDamagedTickers.add(t)

                            line = buildCommaSeparatedTickerPairString(newDamagedTickers) + '\n'
                            autoWrittenLineIsNext = False
                        newfile += line
                with open(valuesFile, 'w') as f:
                    f.write(newfile)

                ## reset gaps so next iteration will re-build, excluding damaged symbols
                dateGaps = {} if ALL else []
                lastDamagedTickers = currentDamagedTickers.copy()
                currentDamagedTickers.clear()

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
                    if date.fromisoformat(d.period_date) > g: break
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
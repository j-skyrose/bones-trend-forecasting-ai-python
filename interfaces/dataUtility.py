import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, numpy, numba, calendar, sqlite3, shutil
from datetime import date, timedelta
from functools import partial
from typing import Dict, List, Union

from globalConfig import config as gconfig
from constants.enums import Api, ChangeType, Direction, FeatureExtraType, IndicatorType, NormalizationMethod, OperatorDict, OptionsDataSource, OutputClass, SQLInsertHelpers, SeriesType, StockDataSource
from constants.exceptions import DamageDetected, InsufficientDataAvailable, NotSupportedYet
from constants.values import indicatorsKey, unusableSymbols
from managers.apiManager import APIManager
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.inputVectorFactory import InputVectorFactory
from managers.marketDayManager import MarketDayManager
from structures.optionsContract import OptionsContract
from structures.skipsObj import SkipsObj
from structures.sql.sqlArgumentObj import SQLArgumentObj
from structures.sql.sqlOrderObj import SQLOrderObj
from utils.collectorSupport import getExchange
from utils.dbSupport import getTableString
from utils.other import buildCommaSeparatedTickerPairString, getIndicatorPeriod, getInstancesByClass, parseCommandLineOptions
from utils.support import addItemToContainerAtDictKey, asDate, asISOFormat, asList, flatten, getIndex, partition, recdotdict, recdotobj, shortc, tqdmLoopHandleWrapper, tqdmProcessMapHandlerWrapper
from utils.types import TickerKeyType
from utils.technicalIndicatorFormulae import generateADXs_AverageDirectionalIndex, generateATRs_AverageTrueRange, generateBollingerBands, generateCCIs_CommodityChannelIndex, generateDIs_DirectionalIndicator, generateEMAs_ExponentialMovingAverage, generateMACDs_MovingAverageConvergenceDivergence, generateRSIs_RelativeStrengthIndex, generateSuperTrends, generateVolumeBars, getExpectedLengthForIndicator, unresumableGenerationIndicators
from utils.vectorSimilarity import euclideanSimilarity_jit

dbm: DatabaseManager = DatabaseManager()

maxcpus = 3

#region vector similarities
'''
Determines the Euclidean similarity between input vectors for all negative instances of each ticker, writes resulting (sum) to DB
Input vector must only contain positive numbers, negatives may slightly change how accurate the similarity calculation is
Can be interuptted and resumed, and should be able to handle new stock data addition to existing calculated values
'''
def similarityCalculationAndInsertion(exchange=None, **kwargs):
    '''KWARGS: checkDBIntegrity, wipeDataOnDBIntegrityFailure, correctImproperlyInsertedDates, dryrun, freshrun'''
    ''' DB Integrity gets messed up when stock data is updated (or possibly due to a [local] symbol lookup bug); just something that needs to be dealt with whenever updating vector similarities
            alphavantage: high/low/close/volume values can change possibly because the previous last day may not have gone til end of after-market trading, or post-date corrections are made
                Data mismatch found for TSX FST
                {'exchange': 'TSX', 'symbol': 'FST', 'type': 'DAILY', 'date': '2023-05-19', 'open': 43.24, 'high': 43.24, 'low': 43.14, 'close': 43.24, 'volume': 460.0}
                {'exchange': 'TSX', 'symbol': 'FST', 'type': 'DAILY', 'date': '2023-05-19', 'open': 43.24, 'high': 43.26, 'low': 43.14, 'close': 43.26, 'volume': 500.0}
            polygon: unknown reason
    '''
    
    ## remove unnecessary/redundant features
    ## only keep EMA200, since all are based on stock data, which is already included...and to not break stuff by having no indicators
    cf = gconfig
    cf.similarityCalculation.enabled = True
    for ind in IndicatorType.getActuals():
        cf.feature[indicatorsKey][ind].enabled = False
    # cf.feature[indicatorsKey][IndicatorType.EMA200].enabled = True

    cf.feature.dayOfWeek.enabled = False
    cf.feature.dayOfMonth.enabled = False
    cf.feature.monthOfYear.enabled = False

    ## prevent instance reduction
    cf.sets.instanceReduction.enabled = False

    cf.data.normalize = True
    cf.data.normalizationMethod.default.type = NormalizationMethod.REAL_MAX
    cf.data.normalizationMethod.earningsDate.value = 181

    props = {
        'precedingRange': cf.training.precedingRange,
        'followingRange': cf.training.followingRange,
        'changeType': cf.training.changeType,
        'changeValue': cf.training.changeValue
    }

    if gconfig.testing.enabled:
        props['precedingRange'] = 1

    dm: DataManager = DataManager.forAnalysis(
        skips=SkipsObj(sets=True),
        saveSkips=True,
        skipAllDataInitialization=True,
        **props,
        maxPageSize=1,
        # exchange=['NASDAQ'],
        exchange=asList(exchange) if exchange else None,

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

        for indx,v in enumerate(vector):
            if v > 1.25 or v < 0:
                raise RuntimeError(f'Value above max (1): {v} at {indx}')

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
    neginstances = getInstancesByClass(dm.stockDataInstances.values(), class_=OutputClass.NEGATIVE)
    def getDTArg(indx): ## specifically for neg instances
        return neginstances[indx].getAnchorDay().period_date

    ## prepare get/insert arguments
    def prepareArgs(indx=None, dt=None):
        if indx is not None:
            if dt is not None: raise ValueError
            dt = getDTArg(indx)
        else:
            if dt is not None:
                dt = asISOFormat(dt)
        return {
            'exchange': ticker.exchange,
            'symbol': ticker.symbol,
            'dateType': dm.seriesType,
            'date': dt,
            'vectorClass': OutputClass.NEGATIVE,
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
                        dbm.updateVectorSimilarity(**prepareArgs(dt=oldDate), newPeriodDate=asISOFormat(newDate))
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
        for vsindx in range(numpy.count_nonzero(similaritiesSum)): ## only iterate through calculated values, filled 0 values indicate no calculation was performed
            dbm.insertVectorSimilarity(*prepareArgs(vsindx).values(), similaritiesSum[vsindx], upsert=True)
        dbm.commitBatch()

    print(f' {"Would insert" if dryrun else "Inserted"} {numpy.count_nonzero(similaritiesSum)-len(dbsums)} new values and {"would update" if dryrun else "updated"} {len(dbsums)} values for', ticker.getTuple())
#endregion vector similarities

#region technical indicators
def _verifyTechnicalIndicatorDataIntegrity(stockdata, indicator: IndicatorType, indicatorCount, indicatorPeriod, indicatorMaxDate=None):
    if indicatorMaxDate and indicatorMaxDate > stockdata[-1].period_date: return False
    return indicatorCount == getExpectedLengthForIndicator(indicator, len(stockdata), indicatorPeriod)
    # exp = getExpectedLengthForIndicator(indicator, len(stockdata), indicatorPeriod)
    # return indicatorCount == exp

def _multicore_updateTechnicalIndicatorData(ticker, seriesType: SeriesType, cacheIndicators, indicatorConfig, verbose=0):
    exchange, symbol = ticker
    latestIndicators = dbm.dbc.execute(f'''
        SELECT MAX(date) AS date, COUNT(*) AS count, exchange, symbol, indicator, period, value FROM {getTableString("technical_indicator_data_c")} WHERE date_type=? AND exchange=? AND symbol=? group by exchange, symbol, indicator, period
    ''', (seriesType.name, exchange, symbol))
    def getLatestIndicator(i: IndicatorType, period):
        for li in latestIndicators:
            if li.indicator == i.key and li.period == period:
                return li

    ## data should already be in ascending (date) order
    stkdata = dbm.getStockDataDaily(exchange, symbol)

    ## skip if everything is already updated
    missingIndicators = []
    notuptodateIndicators = []
    if latestIndicators:
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
        ## check integrity of up-to-date indicators
        for ik in IndicatorType:
            if ik in notuptodateIndicators: continue ## will verify integrity after update
            iperiod = getIndicatorPeriod(ik, indicatorConfig)
            lindc = getLatestIndicator(ik, iperiod)
            if not lindc: continue ## likely not configured for caching

            if not _verifyTechnicalIndicatorDataIntegrity(stkdata, ik, lindc.count, iperiod, indicatorMaxDate=lindc.date):
                if verbose: print(f'{ik.longForm} integrity check failed for {latestIndicators[0].exchange}:{latestIndicators[0].symbol}; will regenerate')
                missingIndicators.append(ik)
        if len(missingIndicators) == 0 and len(notuptodateIndicators) == 0: return 0
    else:
        missingIndicators = [ik for ik in IndicatorType]

    returntpls = []
    i: IndicatorType
    for i in cacheIndicators:
        iperiod = getIndicatorPeriod(i, indicatorConfig)

        continueFlag = False
        ## breaks out if there are no issues with generated data
        for regenLoop in range(2):
            ## generate fresh/all data (some indicators use smoothing so their initial values contribute to their latest, meaning they cannot be 'picked up where they left off')
            if regenLoop == 1 or i in missingIndicators or (i in notuptodateIndicators and i in unresumableGenerationIndicators):
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
                    elif i == IndicatorType.RGVB:
                        indcdata = generateVolumeBars(stkdata)
                except InsufficientDataAvailable:
                    continueFlag = True

                break

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

                if _verifyTechnicalIndicatorDataIntegrity(stkdata, i, len(indcdata), iperiod):
                    break
                else:
                    if verbose: print(f'Integrity check failed for {latestIndicators[0].exchange}:{latestIndicators[0].symbol}; regenerating')

            else: ## already up to date
                continueFlag = True
                break
        
        if continueFlag: continue

        ## convert generated values to DB tuples in proper chronological order
        tpls = []
        for indx in range(len(indcdata)):
            val = indcdata[-(indx+1)]
            if i.featureExtraType == FeatureExtraType.MULTIPLE:
                if i == IndicatorType.ST:
                    val = ','.join([str(val[0]), val[1].name])
                else:
                    val = ','.join([str(v) for v in val])

            tpls.append((exchange, symbol, seriesType.name, stkdata[-(indx+1)].period_date, i.key, iperiod, val))

        tpls.reverse()
        returntpls.extend(tpls)

    return returntpls

def technicalIndicatorDataCalculationAndInsertion(exchange=None, symbol=None, seriesType: SeriesType=SeriesType.DAILY, indicatorConfig=gconfig.defaultIndicatorFormulaConfig, doNotCacheADX=True, sequential=False, maxTickerChunkSize=500):
    '''Generates or updates cached technical indicator data; should be run after every stock data dump, but can be time-consuming as there is no easy way to determine if the data is already up to date or not'''
    if seriesType != SeriesType.DAILY: raise NotSupportedYet
    
    if exchange is None:
        ## iterate by exchange to save on RAM
        exchanges = dbm.getDistinct(columnNames='exchange')
    else:
        exchanges = asList(exchange)

    cacheIndicators: List = gconfig.cache.indicators
    if doNotCacheADX: cacheIndicators.remove(IndicatorType.ADX)

    tickersupdated = 0
    rowsadded = 0
    for exch in tqdmLoopHandleWrapper(exchanges, verbose=1, desc='Exchanges'):
        tickers = dbm.getDistinct(exchange=exch, symbol=symbol, purgeUnusables=True)
        print('Got {} tickers'.format(len(tickers)))
        for tickerChunk in tqdmLoopHandleWrapper(numpy.array_split(tickers, int(math.ceil(len(tickers)/maxTickerChunkSize))), verbose=0.5, desc='Ticker chunks'):
            inserttpls = []
            gc.collect()
            for tpls in tqdmProcessMapHandlerWrapper(partial(_multicore_updateTechnicalIndicatorData, seriesType=seriesType, cacheIndicators=cacheIndicators, indicatorConfig=indicatorConfig), tickerChunk, verbose=1, sequentialOverride=sequential, desc='Calculating techInd data for tickers'):
                if len(tpls) != 0:
                    rowsadded += len(tpls)
                    tickersupdated += 1
                    inserttpls.extend(tpls)
            
            stmt = f'INSERT OR REPLACE INTO {dbm.getTableString("technical_indicator_data_c")} VALUES (?,?,?,?,?,?,?)'
            dbm.dbc.executemany(stmt, inserttpls)
            
        dbm.commit()

    print('Updated {} tickers'.format(tickersupdated))
    print('Added or replaced {} rows'.format(rowsadded))
#endregion technical indicators

#region network
def deleteNetwork(networkId):
    '''deletes network and associated data from all database tables; and deletes neural network save'''
    for nid in asList(networkId):
        nrow = dbm.getNetworks_basic(nid)
        dbm.startBatch()
        dbm.deleteNetwork(nid)
        if nrow:
            factoryId = nrow[0].factory_id
            othernrows = dbm.getNetworks_basic(factoryId=factoryId)
            if not othernrows:
                ## only delete if not used by any other networks
                dbm.deleteInputVectorFactory(factoryId)
        dbm.deleteNetworkTrainingConfig(nid)
        dbm.deleteNetworkAccuracy(nid)
        dbm.deleteMetrics(nid)
        dbm.commitBatch()
        try:
            shutil.rmtree(os.path.join(path, f'data/network_saves/{nid}'), ignore_errors=True)
        except FileNotFoundError:
            pass
#endregion network

#region historical data gaps
def _getHistoricalGaps(data, startDate, endDate, vix=False, options=False, verbose=0) -> List[date]:
    '''helper for helper function _getDailyHistoricalGaps'''

    exchange = data[0].exchange if not vix else 'NYSE'
    startDate = asDate(startDate)
    endDate = asDate(endDate)

    if verbose>=2:
        if not vix:
            print('###############################################')
            print((data[0].exchange, data[0].symbol))
        print(startDate, ' -> ', endDate)

    gaps = []
    dindex = 0
    gapStreak = 0
    for d in range(int((endDate - startDate).total_seconds() / (60 * 60 * 24))):
        cdate = startDate + timedelta(days=d)
        if verbose>=2: print('Checking', cdate)
        if cdate.weekday() > 4: # is Saturday (5) or Sunday (6)
            if verbose>=2: print('is weekend')
            continue

        ## holiday checker
        if vix:
            ## vix will need to fill all (holi)dates, regardless of market
            pass
        elif MarketDayManager.isHoliday(cdate, exchange=exchange):
            if verbose>=2: print('is holiday')
            continue

        ## actual gap checker
        if cdate != date.fromisoformat(data[dindex].period_date):
            if verbose>=2:
                ddt = date.fromisoformat(data[dindex].period_date)
                print('is gap')

            gaps.append(cdate)
            gapStreak += 1

            if not vix and not options and gapStreak > 40:
                raise DamageDetected
        else:
            dindex += 1
            gapStreak = 0
    return gaps

def _verifyAndGetTickerList(exchange=None, symbol=None, optionTicker=None, tickers=None, **kwargs):
    '''argument check and ticker list setup if required'''
    if (exchange or symbol or optionTicker) and tickers: raise ValueError
    if (exchange or symbol or optionTicker) and not tickers:
        if optionTicker:
            tickers = [(exchange, symbol, optionTicker)]
        else:
            tickers = [(exchange, symbol)]
    return asList(tickers)

## helper function to fillHistoricalGaps
def _getAllDailyHistoricalGaps(exchange=None, symbol=None, optionTicker=None, tickers=[], options=False, autoUpdateDamagedSymbols=True, verbose=1) -> Union[List[date], Dict[date,List[str]]]:
    tickers = _verifyAndGetTickerList(**locals())
    if tickers and len(tickers[0]) == 3: options = True

    ## exclude purgable (i.e. damaged, extreme, etc) tickers from passed list
    allTickers = dbm.getDistinct(purgeUnusables=True)
    if tickers:
        if options and len(tickers) == 1 and len(tickers[0]) == 2:
            exchange, symbol = tickers[0]
            optionTickers = dbm.getDistinct('options_data_daily_c', 'ticker', exchange=exchange, symbol=symbol)
            loopTickers = [(exchange, symbol, ot) for ot in optionTickers]
        else:
            checkList = [(t[0],t[1]) for t in tickers] if options else tickers
            loopTickers = [r for r in allTickers if r in checkList]
    else:
        if options:
            loopTickers = []
            for exchange,symbol in allTickers:
                optionTickers = dbm.getDistinct('options_data_daily_c', 'ticker', exchange=exchange, symbol=symbol)
                loopTickers.extend([(exchange, symbol, ot) for ot in optionTickers])
        else:
            loopTickers = allTickers

    dateGapsInit = lambda: ({} if len(tickers) > 1 or options else [])
    dateGaps = dateGapsInit()
    currentDamagedTickers = set()
    lastDamagedTickers = set()
    for rerun in range(2):
        for ticker in tqdmLoopHandleWrapper(loopTickers, verbose, desc='Determining DAILY historical gaps'):
            if not options and ticker in lastDamagedTickers: continue
            if options:
                exchange, symbol, optionsTicker = ticker
                data = dbm.getOptionsDataDaily_basic(exchange=exchange, symbol=symbol, ticker=optionsTicker, orderBy='period_date')
                endDate = OptionsContract.getExpirationDate(optionsTicker) + timedelta(days=1)
                data.append(recdotdict({
                    'period_date': endDate.isoformat(),
                    'open': 0,
                    'high': 0,
                    'low': 0,
                    'close': 0
                }))
            else:
                exchange, symbol = ticker
                data = dbm.getStockDataDaily(exchange=exchange, symbol=symbol)
                endDate = date.fromisoformat(data[-1].period_date)

            try:
                gaps = _getHistoricalGaps(
                    data,
                    date.fromisoformat(data[0].period_date),
                    endDate,
                    options=options,
                    verbose=verbose
                )
                if len(tickers) > 1 or options:
                    for cdt in gaps:
                        try:
                            dateGaps[cdt].append(ticker)
                        except KeyError:
                            dateGaps[cdt] = [ticker]  
                else:
                    dateGaps.extend(gaps)
            except DamageDetected:
                currentDamagedTickers.add(ticker)

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
                            newDamagedTickers = set(tickers + list(currentDamagedTickers))

                            line = buildCommaSeparatedTickerPairString(newDamagedTickers) + '\n'
                            autoWrittenLineIsNext = False
                        newfile += line
                with open(valuesFile, 'w') as f:
                    f.write(newfile)

                ## reset gaps so next iteration will re-build, excluding damaged symbols
                dateGaps = dateGapsInit()
                lastDamagedTickers = currentDamagedTickers.copy()
                currentDamagedTickers.clear()

            else:
                raise Exception('consecutive gaps too big for some symbols')

    return dateGaps

def vixTradingDayGapDeterminationAndInsertion(fillForNonUSMarkets=True, dryrun=False, verbose=1):
    '''Fill any data gaps with artificial data using last real trading day.
    artificial 0 = real data\n
    artificial 1 = fake data\n
    artificial 2 = fake data for US market holiday\n\nGenerally only used after VIX update dumps.'''
    
    data = dbm.getCboeVolatilityIndex_basic(orderBy='period_date')
    gaps = _getHistoricalGaps(
        data,
        data[0].period_date,
        data[-1].period_date,
        vix=True, verbose=verbose
    )

    for gdt in gaps:
        ## find closest date without going over
        prevclose = None
        for d in data:
            if date.fromisoformat(d.period_date) > gdt: break
            prevclose = d.close

        artificial = 2 if fillForNonUSMarkets and MarketDayManager.isHoliday(gdt) else 1
        if not dryrun:
            dbm.insertVIX(gdt.isoformat(), prevclose, prevclose, prevclose, prevclose, artificial, SQLInsertHelpers.IGNORE)
        else:
            print(str(gdt), prevclose, artificial)

    if verbose: print(f'{len(gaps)} gaps filled')

def historicalTradingDayGapDeterminationAndInsertion(exchange=None, symbol=None, optionTicker=None, tickers=[], options=False, seriesType=SeriesType.DAILY, dryrun=False, autoUpdateDamagedSymbols=True, verbose=1):
    '''Fill any data gaps with artificial data using last real trading day.\n\nGenerally only used after large data acquisitions/dumps.'''
    if seriesType != SeriesType.DAILY: raise NotSupportedYet
    tickers = _verifyAndGetTickerList(**locals())
    if tickers and len(tickers[0]) == 3: options = True

    insertData = []
    gaps = _getAllDailyHistoricalGaps(tickers=tickers, autoUpdateDamagedSymbols=autoUpdateDamagedSymbols, options=options, verbose=verbose)

    if len(gaps) == 0:
        if verbose>=1: print('No gaps found')
    else:
        for g in tqdmLoopHandleWrapper(gaps, verbose, desc='Determining historical gap fillers for ' + seriesType.name):
            for gap in tqdmLoopHandleWrapper(gaps[g], verbose-0.5, desc=str(g)) if len(tickers) != 1 or options else tickers:
                if options:
                    exchange, symbol, optionTicker = gap
                else:
                    exchange, symbol = gap
                if (exchange, symbol) in unusableSymbols: continue
                ## find closest date without going over
                if options:
                    expiryDate = OptionsContract.getExpirationDate(optionTicker)
                    daysUntilExpiry = lambda d: (expiryDate - asDate(d)).days + 1
                    prevRealOptionDay = None
                    nextRealOptionDay = None
                    for d in dbm.getOptionsDataDaily_basic(exchange=exchange, symbol=symbol, ticker=optionTicker, artificial=False, orderBy='period_date'):
                        if date.fromisoformat(d.period_date) > g:
                            nextRealOptionDay = d
                            break
                        prevRealOptionDay = d
                    if not nextRealOptionDay:
                        nextRealOptionDay = recdotdict({
                            'period_date': (expiryDate + timedelta(days=1)).isoformat(),
                            'open': 0,
                            'high': 0,
                            'low': 0,
                            'close': 0
                        })
                    # prevStockDay = dbm.getStockDataDaily_basic(exchange=exchange, symbol=symbol, periodDate=prevRealOptionDay.period_date, limit=1)[0]
                    # currStockDay = dbm.getStockDataDaily_basic(exchange=exchange, symbol=symbol, periodDate=str(g), limit=1)[0]
                    # nextStockDay = dbm.getStockDataDaily_basic(exchange=exchange, symbol=symbol, periodDate=nextRealOptionDay.period_date, limit=1)[0]

                    prevDaysUntilExpiry = daysUntilExpiry(prevRealOptionDay.period_date)
                    currDaysUntilExpiry = daysUntilExpiry(g)
                    nextDaysUntilExpiry = daysUntilExpiry(nextRealOptionDay.period_date)

                    artificalDay = {
                        'exchange': exchange,
                        'symbol': symbol,
                        'ticker': optionTicker,
                        'period_date': str(g),
                        'artificial': True,
                    }

                    #region method 1: linear transition from last known day to next known day
                    for pkey in ['high', 'low', 'open', 'close']:

                        slope = (nextRealOptionDay[pkey] - prevRealOptionDay[pkey]) / (nextDaysUntilExpiry - prevDaysUntilExpiry)
                        yint = prevRealOptionDay[pkey] - slope * prevDaysUntilExpiry
                        artificialp = slope * currDaysUntilExpiry + yint
                        if pkey == 'close':
                            artificalDay[pkey] = min(artificialp, artificalDay['high'])
                        elif pkey == 'open':
                            artificalDay[pkey] = max(artificialp, artificalDay['low'])
                        else:
                            artificalDay[pkey] = artificialp

                    insertData.append(artificalDay)
                    #endregion

                else:
                    prevclose = None
                    for d in dbm.getStockDataDaily(exchange=exchange, symbol=symbol):
                        if date.fromisoformat(d.period_date) > g: break
                        prevclose = d.close
                    insertData.append({
                        'exchange': exchange,
                        'symbol': symbol,
                        'period_date': str(g),
                        'open': prevclose,
                        'high': prevclose,
                        'low': prevclose,
                        'close': prevclose,
                        'artificial': True,
                    })

        if len(insertData) == 0:
            if verbose>=1: print('No filling required')
        else:
            if verbose>=1: print(f'Writing {len(insertData)} gap fillers to database')
            if not dryrun:
                if options:
                    dbm.insertOptionsData(data=insertData)
                else:
                    dbm.insertStockData(data=insertData)
                dbm.commit()
            elif verbose>=1:
                insertData = recdotobj(insertData)
                ## count number of gaps for each ticker
                sumdict = {}
                for d in insertData:
                    sumdict[(d.exchange, d.symbol)] = 0
                for d in insertData:
                    sumdict[(d.exchange, d.symbol)] += 1

                ## print first handful of gaps for each ticker
                sumdict = dict(sorted(sumdict.items(), key=lambda item: item[1]))
                for tk, v in sumdict.items():
                    print(tk, v)
                    c = 0
                    for d in insertData:
                        if (d.exchange, d.symbol) == tk:
                            print(d)
                            c+=1
                        if c > 4:
                            break
#endregion historical data gaps

#region earnings dates
def _getAdjustedDate(masterDate, operandDate, yearOnly=False, modifierOnly=False):
    if yearOnly and modifierOnly: raise ValueError("'xxxOnly' args are mutually exclusive")
    masterDate = asDate(masterDate)
    operandDate = asDate(operandDate)
    modifiers = [-1,0,1]
    ## prevent error when operandDate is a leap year
    opDay = 28 if calendar.isleap(operandDate.year) and operandDate.month == 2 and operandDate.day == 29 else operandDate.day
    diffs = [abs(masterDate - date(masterDate.year + mod, operandDate.month, opDay)) for mod in modifiers]
    modifier = modifiers[diffs.index(min(diffs))]
    if modifierOnly:
        return modifier
    elif yearOnly:
        return masterDate.year + modifier
    else:
        return date(masterDate.year + modifier, operandDate.month, opDay)
def _dateDifference(dt1, dt2, excludeYear=False):
    dt1 = asDate(dt1)
    dt2 = asDate(dt2)
    if excludeYear:
        dt2 = _getAdjustedDate(dt1, dt2)
    return abs((dt1 - dt2).days)
def _dateWithinDiffParition(iterable, masterIterable, diff=30):
    met = []
    notmet = []
    for otr in iterable:
        datediffs = []
        for mr in masterIterable:
            datediffs.append(_dateDifference(mr.earnings_date, otr.earnings_date))
        if all(dd > diff for dd in datediffs): notmet.append(otr)
        else: met.append(otr)
    return met, notmet
def _removeAbnormalFiscalQuarterRows(rows):
    ## fiscal quarter may not directly match with earnings date; data error, ignore for now e.g. ABEO
    rows[:] = [r for r in rows if not hasattr(r, 'fiscal_quarter_ending') or _dateDifference(r.earnings_date, r.fiscal_quarter_ending) < 160]
    ## if error due to fiscal_quarter_ending == '2000', data should be corrected probably to '2008-03-01'
def _getAverageDate(iterable, key=None, excludeYear=True):
    dtList = [asDate(d) for d in (iterable if not key else [getattr(x, key) for x in iterable])]
    if excludeYear:
        dtList[:] = [dtList[0]] + [_getAdjustedDate(dtList[0], dt) for dt in dtList[1:]]
    return date.fromordinal(int(numpy.average([ dt.toordinal() for dt in dtList ]))) 

def earningsDateCalculationAndInsertion(simple=True, verbose=1):
    DEBUG = False
    ## exclude until more data is available, or there is a better way to narrow these down to actual dates
    excludeTickers=['AIM','AMN','BRTX',
              'CSR',
              'GEN','GHI','JEF','RGP','TAL','VAL'] ## excessive earnings dates per year (>7)

    # exchange='NASDAQ'
    exchange=None
    symbolTables = ['earnings_dates_nasdaq_d', 'earnings_dates_marketwatch_d', 'earnings_dates_yahoo_d']
    allSymbolList = []
    for st in symbolTables:
        allSymbolList += dbm.getDistinct(st, columnNames='symbol')
    ntickers = set([s for s in allSymbolList if s not in excludeTickers])
    # ntickers = ['OILSF']
    # ntickers = ['WBD'] ## 2008 - 5, 2009 - 6, 2010 - 7
    # ntickers = ['VRME'] ## 2021 - 5; 2 removed
    ## remove abnormal fiscal quarter ending rows ... 2023-08-30 = 0
    # def abnormalCond(r): not hasattr(r, 'fiscal_quarter_ending') or dateDifference(r.earnings_date, r.fiscal_quarter_ending) < 160
    # abnormalNasdaqFiscalQuarterEndingRows, rawNasdaqDBData = partition(rawNasdaqDBData, lambda r: abnormalCond(r))
    # abnormalMarketwatchFiscalQuarterEndingRows, rawMarketwatchDBData = partition(rawMarketwatchDBData, lambda r: abnormalCond(r))
    # print(f'Found {len(abnormalNasdaqFiscalQuarterEndingRows) + len(abnormalMarketwatchFiscalQuarterEndingRows)} abnormal fiscal quater ending records')

    ## build up average earnings date by fiscal quarter ending
    # fqeDaysFollowingBuckets = { q: [] for q in range(1, 13) }
    # for r in rawNasdaqDBData + rawMarketwatchDBData:
    #     fqeDaysFollowingBuckets[int(r.fiscal_quarter_ending[5:7])].append((date.fromisoformat(r.earnings_date) - date.fromisoformat(r.fiscal_quarter_ending)).days)
    # ## NOTE: fiscal_quarter_ending basically only indicates year and month, actual day could be any, e.g. COST ending on 7th/12th/28th
    # def withAdjustedYear(edate, bucket):
    #     dtdt = date.fromisoformat(edate)
    #     year = '2000'
    #     if dtdt.month < 3 and any(qdate.month > 10 for qdate in [date.fromisoformat(q.earnings_date) for q in bucket]):
    #         year = '2001'
    #     return year + edate[4:]
    
    fqeAverageDaysFollowing = {1: 67, 2: 64, 3: 66, 4: 65, 5: 67, 6: 64, 7: 61, 8: 68, 9: 63, 10: 63, 11: 65, 12: 79} ## cache
    # fqeAverageDaysFollowing = { q: int(numpy.average(fqeDaysFollowingBuckets[q])) for q in fqeDaysFollowingBuckets.keys() }
    # print(fqeAverageDaysFollowing)

    dbm.dbc.execute(f'DELETE FROM {dbm.getTableString("earnings_dates_c")}') ## clear table as processing may change some old data
    totalRowsInserted = 0
    for symbol in tqdmLoopHandleWrapper(ntickers, verbose=verbose):
        if verbose > 1: print(f'Starting {symbol}')
        dbdata = [recdotdict({"api": eapi, "earnings_date": r.earnings_date, "input_date": r.input_date, **r}) for eapi in APIManager.getEarningsCollectionAPIs() for r in dbm.getDumpEarningsDates(eapi, exchange=exchange, symbol=symbol)]
        if verbose > 1: 
            print(f'{len(dbdata)} rows queried from database')
            snapshotDBCount = len(dbdata)
            if snapshotDBCount == 0: continue
        _removeAbnormalFiscalQuarterRows(dbdata)
        if verbose > 1:
            removedCount = snapshotDBCount - len(dbdata)
            if removedCount: print(f'Removed {removedCount} abnormal fiscal quarter ending rows')
        historicalRows, upcomingRows = partition(dbdata, lambda r: r.earnings_date < r.input_date)

        ####################################################################################
        #region - remove redundant, bad, unclear historical data
        fqeRows, otherRows = partition(historicalRows, lambda r: hasattr(r, 'fiscal_quarter_ending') and r.fiscal_quarter_ending is not None)
        if verbose > 1: snapshotFQERowCount = len(fqeRows)
        #region - ensure uniqueness of fqe rows; considered to have higher certainty
        fqeBuckets = {}
        for r in fqeRows:
            addItemToContainerAtDictKey(fqeBuckets, r.fiscal_quarter_ending[:7], r)
        for fqe, fqeBucket in fqeBuckets.items():
            if len(fqeBucket) < 2: continue
            if simple:
                if all(r.earnings_date == fqeBucket[0].earnings_date for r in fqeBucket):
                    fqeBucket[:] = [fqeBucket[0]]
                    continue
            nasdaqRows, nonNasdaqRows = partition(fqeBucket, lambda r: r.api == Api.NASDAQ)
            if len(nasdaqRows) == 0:
                raise ValueError()
            elif len(nasdaqRows) == 1:
                fqeBucket[:] = nasdaqRows
                continue
            elif len(nasdaqRows) > 1:
                if simple:
                    nasdaqRows.sort(key=lambda x: shortc(x.number_of_estimates, 0))
                    fqeBucket[:] = [nasdaqRows[-1]]
                    continue
                raise ValueError()
            if len(nonNasdaqRows) > 0:
                raise ValueError('Has non-Nasdaq rows to deal with')
            ## TODO: proper advanced determination, e.g. combining values, averaging, etc.
            raise ValueError()
            if not simple:

                ## most recent/accurate row should have most data for specific keys compared to others
                xkeys = ['eps', 'surprise_percentage', 'eps_forecast']
                hasX_rows = []
                for xkey in xkeys:
                    for r in fqeBucket:
                        if r[xkey] is not None:
                            hasX_rows.append(r)
                    if len(hasX_rows) == 0:
                        hasX_rows = []
                    elif len(hasX_rows) == 1:
                        break
                    elif len(hasX_rows) > 1:
                        fqeBucket = hasX_rows
                        hasX_rows = []
                ## highest number of estimates should be most recent/accurate
                if len(hasX_rows) > 1:
                    if not all(hasattr(r, 'number_of_estimates') for r in hasX_rows):
                        raise ValueError()
                    fqeBucket.sort(key=lambda x: x.number_of_estimates)
                    for r in fqeBucket[:-1]:
                        fqeBucket.remove(r)
        #endregion
        interimData = flatten(list(fqeBuckets.values()))
        if verbose > 1:
            removedCount = snapshotFQERowCount - len(interimData)
            if removedCount: print(f'Removed {removedCount} rows during FQE uniqueness section')
        #region - ensure uniqueness of other rows that are not duplicates of interim rows; lower certainty
        dups, nonDups = _dateWithinDiffParition(otherRows, interimData, 30)
        if verbose > 1:
            removedCount = len(dups)
            if removedCount: print(f'Removed {removedCount} duplicate rows')
        nonDups.sort(key=lambda x: x.earnings_date)

        #region - attempt to condense rows that may be duplicates of the same event, date diff < 7 days
        if verbose > 1: snapshotNonDupsCount = len(nonDups)
        dateGroupings = []
        for r in nonDups:
            datediffs = [_dateDifference(r.earnings_date, _getAverageDate(grp, key='earnings_date')) for grp in dateGroupings]
            closestIndex = 0
            closestdd = sys.maxsize
            for indx,dd in enumerate(datediffs):
                if dd < 7 and dd < closestdd:
                    closestdd = dd
                    closestIndex = indx
            if closestdd == sys.maxsize: ## not close to anything
                dateGroupings.append([r])
            else:
                dateGroupings[closestIndex].append(r)
        ## ignore solo groups
        dateGroupings[:] = [dgrp for dgrp in dateGroupings if len(dgrp) > 1]
        
        for dgrp in dateGroupings:
            if len(dgrp) > 1:
                if simple:
                    for r in dgrp[:-1]:
                        nonDups.remove(r)
                else:
                    pass
                    ## TODO: eps_forecast, eps, surprise_percentage, event_name
        if verbose > 1:
            removedCount = snapshotNonDupsCount - len(nonDups)
            if removedCount: print(f'Removed {removedCount} rows during non-duplicate condensation')
        #endregion

        yearBuckets = {}
        for r in interimData + nonDups:
            addItemToContainerAtDictKey(yearBuckets, r.earnings_date[:4], r)

        #region - determine average typical earnings dates, for use in fixing aberrant years, and condensing upcoming data
        ## assume four earnings per year is normal, determine the typical dates
        method1 = False
        if method1:
            ## tries to use any API row, no priority
            typicalQrDateBuckets = [[] for _ in range(4)]
            for yrBucket in yearBuckets.values():
                if len(yrBucket) != 4: continue
                for r in yrBucket:
                    inserted = False
                    for qindx in range(len(typicalQrDateBuckets)):
                        dt = date.fromisoformat(r.earnings_date)
                        if len(typicalQrDateBuckets[qindx]) > 0:
                            if _dateDifference(dt, typicalQrDateBuckets[qindx][0], excludeYear=True) < 30:
                                typicalQrDateBuckets[qindx].append(dt)
                                inserted = True
                                break
                        else:
                            typicalQrDateBuckets[qindx].append(dt)
                            inserted = True
                            break
                    if not inserted: raise ValueError(f'Not able to fit into typical quarter earnings date bucket\n{r}')
        else:
            ## method2: use NASDAQ prefentially, match remaining to them
            typicalQrDateBuckets = [[] for _ in range(12)]
            typicalQrDateBucketsFQE = [[] for _ in range(len(typicalQrDateBuckets))]
            for nasdaqOnly in [True, False]:
                for yrBucket in yearBuckets.values():
                    if len(yrBucket) > 4: continue
                    yrNasdaqRows, yrOtherRows = partition(yrBucket, lambda r: r.api == Api.NASDAQ)
                    for r in yrNasdaqRows if nasdaqOnly else yrOtherRows:
                        inserted = False
                        for qindx in range(len(typicalQrDateBuckets)):
                            dt = date.fromisoformat(r.earnings_date)
                            if len(typicalQrDateBuckets[qindx]) > 0:
                                avgTypicalDt = _getAverageDate(typicalQrDateBuckets[qindx])
                                if (nasdaqOnly and r.fiscal_quarter_ending[5:] == typicalQrDateBucketsFQE[qindx][0][5:] and _dateDifference(dt, avgTypicalDt, excludeYear=True) < 60) \
                                or _dateDifference(dt, avgTypicalDt, excludeYear=True) < 30:
                                        typicalQrDateBuckets[qindx].append(dt)
                                        if nasdaqOnly: typicalQrDateBucketsFQE[qindx].append(r.fiscal_quarter_ending)
                                        inserted = True
                                        break
                            elif not nasdaqOnly or r.fiscal_quarter_ending is not None:
                                typicalQrDateBuckets[qindx].append(dt)
                                if nasdaqOnly: typicalQrDateBucketsFQE[qindx].append(r.fiscal_quarter_ending)
                                inserted = True
                                break
                        if not inserted:
                            if r.eps is not None: ## i.e. is more than just a date -> higher chance it's not some random data artifact/error
                                raise ValueError(f'Not able to fit into typical quarter earnings date bucket\n{r}')

        ## adjust years so everything is together
        for bucket in typicalQrDateBuckets:
            if len(bucket) == 0: continue
            for indx in range(1, len(bucket)):
                bucket[indx] = _getAdjustedDate(bucket[0], bucket[indx])
        
        avgTypicalQrDates = [
            _getAverageDate(bucket)
            for bucket in typicalQrDateBuckets if len(bucket) > 0
        ]
        #endregion

        #region - aberrant year determination and fixing
        if verbose > 1: snapshotNonDupsCount = len(nonDups)
        ## some years may have abnormal numbers of earnings dates, need to check if they are valid or determine which ones are most likely to be
        aberrantYears = []
        for yr in yearBuckets.keys():
            # if len(yearBuckets[yr]) > 7: ##TODO: >4
            if len(yearBuckets[yr]) > 4:
                # raise ValueError()
                if DEBUG: print(f'{exchange}:{symbol}:{yr} - {len(yearBuckets[yr])}')
                aberrantYears.append(yr)
                pass
        if len(aberrantYears) > 0:
            interimYearBuckets = {}
            nonDupsYearBuckets = {}
            for r in interimData:
                addItemToContainerAtDictKey(interimYearBuckets, r.earnings_date[:4], r)
            for r in nonDups:
                addItemToContainerAtDictKey(nonDupsYearBuckets, r.earnings_date[:4], r)

            ## now try to match aberrant year rows to typical dates
            for yrBucket in nonDupsYearBuckets.values():
                if len(yrBucket) == 4: continue
                matchedBuckets = [[] for _ in range(len(avgTypicalQrDates))]
                ## assign to buckets based on proximity to average typical earnings dates, drop any not sufficiently close
                for r in yrBucket:
                    if hasattr(r, 'fiscal_quarter_ending') and r.fiscal_quarter_ending is not None: continue
                    matched = False
                    for indx,avgTypicalQrDate in enumerate(avgTypicalQrDates):
                        if _dateDifference(r.earnings_date, avgTypicalQrDate, excludeYear=True) < 30:
                            matched = True
                            matchedBuckets[indx].append(r)
                            break
                    if not matched:
                        if not simple and r.eps is not None:
                            raise ValueError(f'Would remove row with EPS data\n{r}')
                        # yrBucket.remove(r)
                        nonDups.remove(r)
                        if DEBUG: print(r)
                for mbucket in matchedBuckets:
                    if len(mbucket) > 1:
                        pass
            
            if verbose > 1:
                removedCount = snapshotNonDupsCount - len(nonDups)
                if removedCount: print(f'Removed {removedCount} rows from aberrant years')
        #endregion
        #endregion
        interimData.extend(nonDups)
        #endregion

        ####################################################################################
        #region - condense upcoming data
        
        ## sort to buckets based on average earnings date
        upcomingQrBuckets = [[] for _ in range(len(avgTypicalQrDates))]
        for r in upcomingRows:
            for qbindx in range(len(upcomingQrBuckets)):
                if len(upcomingQrBuckets[qbindx]) > 0:
                    if _dateDifference(r.earnings_date, upcomingQrBuckets[qbindx][0].earnings_date, excludeYear=True) < 30:
                        upcomingQrBuckets[qbindx].append(r)
                        break
                else:
                    upcomingQrBuckets[qbindx].append(r)
                    break
        ## condense redundant upcoming data
        for qrBucket in upcomingQrBuckets:
            qrBucket.sort(key=lambda x: x.earnings_date + x.input_date)
            lastrow = None
            for r in qrBucket[:]:
                if not lastrow: 
                    lastrow = r
                    continue
                if lastrow.earnings_date == r.earnings_date:
                    if simple:
                        qrBucket.remove(r)
                        if DEBUG: print('condensing', r)
                    else:
                        ## TODO: any change to forecast may be lost by simple removal
                        pass
                else:
                    lastrow = r

        ## separate (quarter) buckets by year
        upcomingQrYrBuckets = []
        for qrBucket in upcomingQrBuckets:
            yrBuckets = []
            qrBucket.sort(key=lambda x: x.earnings_date)
            lastRow = None
            for r in qrBucket:
                if not lastRow:
                    lastRow = r
                    yrBuckets.append([r])
                else:
                    if _dateDifference(r.earnings_date, lastRow.earnings_date) > 180:
                        yrBuckets.append([r])
                    else:
                        yrBuckets[-1].append(r)
            upcomingQrYrBuckets.extend(yrBuckets)

        ## remove incorrect upcoming data for known earnings dates
        for qrBucket in upcomingQrYrBuckets:
            for r in qrBucket:
                realEarningsDate = None
                for idr in interimData:
                    if r.earnings_date == idr.earnings_date:
                        realEarningsDate = r.earnings_date
                        break
                if realEarningsDate:
                    if simple:
                        for r in qrBucket[getIndex(qrBucket, lambda x: x.earnings_date == realEarningsDate):]:
                            qrBucket.remove(r)
                            if DEBUG: print('removing', r)
                    else:
                        ## TODO: any change to forecast may be lost by simple removal
                        pass
        flattenedQrBuckets = flatten(upcomingQrBuckets)
        if verbose > 1:
            removedCount = len(upcomingRows) - len(flattenedQrBuckets)
            if removedCount: print(f'Removed {removedCount} rows during upcoming data condensation')
        #endregion
        interimData.extend(flattenedQrBuckets)
        
        if len(interimData) > 0: 
            interimData.sort(key=lambda x: x.earnings_date)
            if verbose > 1: print(f'prepared to insert {len(interimData)} for {"NASDAQ" if interimData[0].api == Api.NASDAQ else interimData[0].exchange}:{symbol}')
            countSnapshot = int(totalRowsInserted)
            for r in interimData:
                try: 
                    dbm.insertEarningsDate(
                        'NASDAQ' if r.api == Api.NASDAQ else r.exchange, 
                        r.symbol, r.input_date, r.earnings_date
                    )
                    totalRowsInserted += 1
                except sqlite3.IntegrityError: pass
            if verbose > 1: print(f'inserted {totalRowsInserted - countSnapshot} rows')
        elif verbose > 1: print('No data to insert')
        
        continue

    dbm.commit()
    print(f'Inserted {totalRowsInserted} rows')
#endregion earnings dates

#region data consolidation
## combines from various dump tables: alphavantage, polygon, old historical_data
## alphavantage seems to be the more correct one than polygon, i.e. NASDAQ:AACG 2023-05-30 volume according to NASDAQ site is incorrect for polygon row (17k vs 9.5k); open is off by 1c but rest is correct
def consolidateDailyStockData(limit=None, fillGaps=True, verbose=1, **kwargs):
    exceptionTickers = []
    exchangeAliasDict = dbm.getAliasesDictionary()
    limitTickers = []
    tickersUpdated = set()
    
    for source in StockDataSource.getInPriorityOrder():
        getFunction = getattr(dbm, f'getDumpStockDataDaily{source.name.capitalize()}_basic') if source != StockDataSource.HISTORIC else dbm.getHistoricalData_basic
        def kwargsBuilder(exchange, symbol):
            ret = {}
            if source == StockDataSource.POLYGON:
                ret['ticker'] = symbol
            else:
                if source == StockDataSource.HISTORIC:
                    ret['artificial'] = False
                ret['exchange'] = exchange
                ret['symbol'] = symbol
            return ret
        insertStrategy = SQLInsertHelpers.REPLACE if source == StockDataSource.ALPHAVANTAGE else SQLInsertHelpers.IGNORE
        
        ## check which tickers have new data and require consolidation
        queuedTickers = dbm.getDumpQueueStockDataDaily_basic(source=source.name)
        for exchange,symbol,_ in tqdmLoopHandleWrapper([qt.values() for qt in queuedTickers], verbose=verbose, desc=f'Transfering {source.name} ticker data'):
            exchangeWasUnknown = False
            if source == StockDataSource.POLYGON and exchange == 'UNKNOWN':
                ## attempt to match ticker to an exchange
                res = dbm.getDumpSymbolInfoPolygon_basic(ticker=symbol, orderBy=[SQLOrderObj('active', Direction.DESCENDING), SQLOrderObj('delisted_utc', Direction.DESCENDING)], onlyColumn_asList='primary_exchange')
                try:
                    exchange = res[0]
                    if exchange == 'UNKNOWN': raise IndexError
                except IndexError:
                    ## TODO: fallback to other info tables
                    exceptionTickers.append(symbol)
                    continue
                exchange = exchangeAliasDict[exchange]
                exchangeWasUnknown = True

            ## do not proceed if limit is in force and ticker was not updated with a previous source this run
            if limit and len(limitTickers) == limit and (exchange, symbol) not in limitTickers: continue

            data = getFunction(**kwargsBuilder(exchange, symbol))
            if not data: raise ValueError

            ## insert data to DB
            dbm.insertStockData(exchange, symbol, data=data, insertStrategy=insertStrategy)
            dbm.dequeueStockDataDailyTickerFromUpdate(exchange='UNKNOWN' if exchangeWasUnknown else exchange, symbol=symbol, source=source)
            tickersUpdated.add((exchange, symbol))
            dbm.commit()

            if limit and len(limitTickers) < limit: limitTickers.append((exchange, symbol))

    if fillGaps: historicalTradingDayGapDeterminationAndInsertion(tickers=tickersUpdated, verbose=verbose, **kwargs)

    if exceptionTickers: print('Exceptions:', len(exceptionTickers), exceptionTickers)
    print(f'{len(tickersUpdated)} tickers updated')

def consolidateDailyOptionsData(limit=None, fillGaps=True, verbose=1, **kwargs):
    '''
        consolidates daily options data from various dump tables: alphavantage, polygon, old historical_data\n
        Alphavantage seems to be the more correct one compared to Polygon, e.g. NASDAQ:AACG 2023-05-30 volume according to NASDAQ site is incorrect from Polygon (17k vs 9.5k); open is off by $0.01 but rest is correct
    '''
    exceptionTickers = []
    limitTickers = []
    tickersUpdated = set()
    
    if len(OptionsDataSource.getInPriorityOrder()) == 1:
        ## only POLYGON as source, can utilize quick dirty transfer of options data from dump table to computed
        data = dbm.getDumpOptionsDataDailyPolygon_basic()
        alreadydata = dbm.getOptionsDataDaily_basic(sqlColumns='DISTINCT exchange,symbol,ticker', onlyColumn_asList=['exchange','symbol','ticker'])
        exchdict = {}
        for d in tqdm.tqdm(data):
            sym = OptionsContract.getSymbol(d.ticker)
            try:
                exch = exchdict[sym]
            except KeyError:
                exch = getExchange(sym, source=OptionsDataSource.POLYGON)
                exchdict[sym] = exch
            if (exch, sym, d.ticker) in alreadydata: continue
            dbm.insertOptionsData(exch, sym, d.ticker, d.period_date, d.open, d.high, d.low, d.close, d.volume, d.transactions, )
        dbm.dequeueOptionsDataDailyTickerFromUpdate(None, None, None, None) ## delete all
    else:
        for source in OptionsDataSource.getInPriorityOrder():
            getFunction = getattr(dbm, f'getDumpOptionsDataDaily{source.name.capitalize()}_basic')
            def kwargsBuilder(optionsTicker, minDate=None):
                ret = {}
                if source == OptionsDataSource.POLYGON:
                    ret['ticker'] = optionsTicker
                    ret['periodDate'] = SQLArgumentObj(asISOFormat(minDate), OperatorDict.GREATERTHAN) if minDate else None
                return ret
            insertStrategy = SQLInsertHelpers.IGNORE ## only one source currently, will need to change depending on reliability of further sources
            
            ## check which tickers have new data and require consolidation
            queuedTickers = dbm.getDumpQueueOptionsDataDaily_basic(source=source.name)

            for exchange,symbol,optionsTicker,_ in tqdmLoopHandleWrapper([qt.values() for qt in queuedTickers], verbose=verbose, desc=f'Transfering {source.name} data'):
                latestDataDate = None # mainly for polygon, not alphavantage
                exchangeWasUnknown = False
                if source == OptionsDataSource.POLYGON:
                    if exchange == 'UNKNOWN':
                        exchangeWasUnknown = True
                        exchange = getExchange(symbol, source=OptionsDataSource.POLYGON)
                        if exchange == 'UNKNOWN' or exchange is None:
                            exceptionTickers.append(symbol)
                            continue
                    latestDataDate = dbm.getOptionsDataDaily_basic(exchange=exchange, symbol=symbol, ticker=optionsTicker, sqlColumns='MAX(period_date) as dt', onlyColumn_asList='dt')[0]

                ## do not proceed if limit is in force and ticker was not updated with a previous source this run
                if limit and len(limitTickers) == limit and (exchange, symbol) not in limitTickers: continue

                data = getFunction(**kwargsBuilder(optionsTicker, latestDataDate))
                if not data and insertStrategy == SQLInsertHelpers.REPLACE: raise ValueError((exchange, symbol, optionsTicker))

                ## insert data to DB
                dbm.insertOptionsData(exchange, symbol, optionsTicker, data=data, insertStrategy=insertStrategy)
                dbm.dequeueOptionsDataDailyTickerFromUpdate(exchange='UNKNOWN' if exchangeWasUnknown else exchange, symbol=symbol, optionsTicker=optionsTicker, source=source)
                tickersUpdated.add((exchange, symbol, optionsTicker))
                dbm.commit()

                if limit and len(limitTickers) < limit: limitTickers.append((exchange, symbol))

    if fillGaps: historicalTradingDayGapDeterminationAndInsertion(tickers=tickersUpdated, verbose=verbose, options=True, **kwargs)

    if exceptionTickers: print('Exceptions:', len(exceptionTickers), exceptionTickers)
    print(f'{len(tickersUpdated)} tickers updated')
#endregion data consolidation

if __name__ == '__main__':
    opts, kwargs = parseCommandLineOptions()
    if opts.function:
        locals()[opts.function](**kwargs)
    else:
        similarityCalculationAndInsertion(parallel=False)
        # similarityCalculationAndInsertion()
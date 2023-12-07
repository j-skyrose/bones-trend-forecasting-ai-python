import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, re, time, numba
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Dict, List

from globalConfig import config as gconfig
from constants.enums import DataFormType, FeatureExtraType, IndicatorType, IndicatorTypeSimplified, InputVectorDataType, SuperTrendDirection, SuperTrendDirectionList
from constants.values import standardExchanges, minGoogleDate, indicatorsKey
from managers.statsManager import StatsManager
from managers.vixManager import VIXManager
from structures.dataPointInstance import DataPointInstance
from structures.financialDataHandler import FinancialDataHandler
from structures.googleInterestsHandler import GoogleInterestsHandler
from structures.stockDataHandler import StockDataHandler
from structures.stockEarningsDateHandler import StockEarningsDateHandler
from structures.stockSplitsHandler import StockSplitsHandler
from utils.other import maxQuarters
from utils.support import Singleton, asDate, asISOFormat, datetime64Weekday, flatten, getIndex, getTimedeltaInDays, recdotdict, _isoformatd, shortc, _edgarformatd, shortcdict
from utils.types import TickerKeyType

# from managers.databaseManager import DatabaseManager
# dbm: DatabaseManager = DatabaseManager()
sm: StatsManager = StatsManager()
collectStats = True

loggedonce = False
warnedonce = False

@numba.njit
def _newNumbaDict(
                    keyType=numba.types.int64,
                #    keyType=numba.types.NPDatetime('D'), 
                    valueType=numba.types.float64):
    return numba.typed.Dict.empty(
        key_type=keyType,
        value_type=valueType,
    )

@numba.njit
def _inpVecStats_newNumbaDict():
    return _newNumbaDict(keyType=numba.types.unicode_type, valueType=numba.types.int64)

inpVecStatsDictType = numba.typeof(_inpVecStats_newNumbaDict())

def _numpyDate64(dt):
    return numpy.datetime64(asISOFormat(dt)).view('int64')

class InputVectorFactory(Singleton):

    def __init__(self, config=gconfig):
        self.config = config
        self.stats = None

        from managers.databaseManager import DatabaseManager
        self.dbm: DatabaseManager = DatabaseManager()

        ## flatten feature dict into tuples for use when building input vectors
        ## (key, extraType, compositeKey); compositeKey for sub-features e.g. indicators_relativeStrengthIndex, stock_high, vix_open
        ## also filters out any features that are not enabled
        self.featureTuples = self._flattenFeatureDict(self.config.feature)

    def _flattenFeatureDict(self, fdict, parentKey='', returnKeysOnly=False):
        if returnKeysOnly and shortcdict(self, 'featureKeyCache', False) and shortcdict(self, 'featureKeyCacheParent', False) == parentKey: 
            return self.featureKeyCache
        
        tpls = []
        for k,v in fdict.items():
            strk = str(k) if k not in [ik for ik in IndicatorType] else k.longForm
            compositeKey = strk if not parentKey else '_'.join([parentKey, strk])
            if 'enabled' in v.keys():
                if v['enabled']:
                    tpls.append((
                        k if type(k) == str else k.name, 
                        v['extraType'], compositeKey))
            else:
                tpls.extend(self._flattenFeatureDict(v, compositeKey))

        if returnKeysOnly:
            self.featureKeyCacheParent = parentKey
            self.featureKeyCache = [tpl[2] for tpl in tpls]
            return self.featureKeyCache
        else:
            return tpls 

    ## e.g. indicators_relativeStrengthIndex, indicators_exponentialMovingAverage50, indicators_bollingerBands
    def getIndicatorCompositeKeys(self) -> List[str]:
        return self._flattenFeatureDict(self.config.feature[indicatorsKey], indicatorsKey, returnKeysOnly=True)
    
    def getIndicators(self) -> List[IndicatorType]:
        return [IndicatorType.getByProp(i, 'compositeKey') for i in self.getIndicatorCompositeKeys()]

    def _convertStockDataToNumbaDict(self, stockDataList):
        def newDict(): return _newNumbaDict(keyType=numba.types.unicode_type)
        retd = _newNumbaDict(valueType=numba.typeof(newDict()))
        for dct in stockDataList:
            intd = newDict()
            for k,v in dct.items():
                if k in ['open', 'high', 'low', 'close', 'volume']: intd[k] = v
            retd[_numpyDate64(dct['period_date'])] = intd
            
        return retd

    def _convertVixDataToNumbaDict(self, vixDataDict):
        def newDict(): return _newNumbaDict(keyType=numba.types.unicode_type)
        retd = _newNumbaDict(valueType=numba.typeof(newDict()))
        for k,v in vixDataDict.items():
            intd = newDict()
            for k2,v2 in v.items():
                if k2 != 'date': intd[k2] = v2
            retd[_numpyDate64(k)] = intd
            
        return retd

    def _convertGoogleInterestDataToNumbaDict(self, giDataDict):
        retd = _newNumbaDict()
        for k,v in giDataDict.items():
            retd[_numpyDate64(k)] = v
        return retd

    def _convertIndicatorDataToNumbaDict(self, indicatorDataDict):    
        ### convert to numbadict
        ## keys must be string literals (i.e. .name)
        ## numpy.array wraps values, with dtype='f8'
        ## internal lists can be tuples
        retd = _newNumbaDict(keyType=numba.types.unicode_type, valueType=numba.types.float64[:, :])
        for k,v in indicatorDataDict.items():
            if k == IndicatorType.ST:
                v = [[s[0], getIndex(SuperTrendDirectionList, s[1])] for s in v]
            elif len(v) and not hasattr(v[0], '__len__'):
                ## all values must be within a sub-tuple/list
                v = [[s] for s in v]
            retd[k.name] = numpy.array(v, dtype='f8')

        return retd

    def _generateEarningsDateNumbaDict(self, stockDataList, earningsDateHandler: StockEarningsDateHandler):
        # retd = _newNumbaDict(valueType=numba.types.NPDatetime('D'))
        retd = _newNumbaDict(valueType=numba.types.int64)
        if earningsDateHandler:
            for d in stockDataList:
                edate = earningsDateHandler.getNextEarningsDate(d.period_date)
                retd[_numpyDate64(d.period_date)] = _numpyDate64(edate) if edate else 0
        return retd
    
    def _convertFoundedDate(self, dt):
        if not dt: return 0

        year = month = day = None
        fdatesplit = dt.split('-')
        if len(fdatesplit) > 0:
            year = int(fdatesplit[0])
            if len(fdatesplit) > 1:
                month = int(fdatesplit[1])
                if len(fdatesplit) > 2:
                    day = int(fdatesplit[2])
        
        if not month: month = 1
        if not day: day = 1
        return _numpyDate64(date(int(year), month, day))
    
    def _convertIPODate(self, dt):
        if dt and dt != 'todo': return _numpyDate64(dt)
        else: return 0

    def _convertDateToDict(self, dt):
        if not dt: return
        if type(dt) != str: dt = asDate(dt).isoformat()
        retd = _newNumbaDict(keyType=numba.types.unicode_type, valueType=numba.types.int64)
        # retd = {}

        datesplit = dt.split('-')
        if len(datesplit) > 0:
            retd['year'] = int(datesplit[0])
            if len(datesplit) > 1:
                retd['month'] = int(datesplit[1])
                if len(datesplit) > 2:
                    retd['day'] = int(datesplit[2])
                    
        if 'month' not in retd.keys(): retd['month'] = 1
        if 'day' not in retd.keys(): retd['day'] = 1

        return retd
    
    def _generateDateDicts(self, dts):
        retd = _newNumbaDict(valueType=numba.typeof(self._convertDateToDict('1970-01-01')))
        # retd = {}
        for dt in dts:
            retd[_numpyDate64(dt)] = self._convertDateToDict(dt)
        return retd
    
    def _configKWArgs(self):
        return {
            'recurrentNetwork': self.config.network.recurrent,
            'dayOfMonthDataForm': self.config.dataForm.dayOfMonth,
            'dayOfWeekDataForm': self.config.dataForm.dayOfWeek,
            'monthOfYearDataForm': self.config.dataForm.monthOfYear,
            'superTrendDataForm': self.config.dataForm.superTrend,
            'includeDatesForFinancials': self.config.feature.financials.includeDates,
            'earningsDateDataForm_vectorSize2': self.config.dataForm.earningsDate.vectorSize2,
            'featureTuples': self.featureTuples,
        }

    def buildAll(self,
                 dataPointInstances: List[DataPointInstance]=[],
            #   stockDataHandlers: Dict[TickerKeyType, StockDataHandler]=None,
                vixData: VIXManager=None, financialDataHandlers: Dict[TickerKeyType, FinancialDataHandler]=None, googleInterestsHandlers: Dict[TickerKeyType, GoogleInterestsHandler]=None, stockSplitsHandlers: Dict[TickerKeyType, StockSplitsHandler]=None, earningsDateHandlers: Dict[TickerKeyType, StockEarningsDateHandler]=None, **kwargs):

        startt = time.time()

        startt2 = time.time()
        precedingSets = [dpi.stockDataHandler.getPrecedingSet(dpi.index) for dpi in dataPointInstances]
        print('prec sets time:', time.time() - startt2)

        startt2 = time.time()
        timet3 = 0
        ## prepare handler lists so they are in-sync with the dpi list
        googleInterestsDicts = []
        initializedDicts = {}
        for dpi in dataPointInstances:
            key = dpi.stockDataHandler.getTickerTuple()
            if key not in initializedDicts.keys():
                startt3 = time.time()
                initializedDicts[key] = self._convertGoogleInterestDataToNumbaDict(googleInterestsHandlers[key].dataDict)
                timet3 += time.time() - startt3
            googleInterestsDicts.append(initializedDicts[key])
        print('gi prep time:', time.time() - startt2)
        print('conversion only:', timet3)

        factoryLineKWArgs = {
            ## config
            **self._configKWArgs(),
            ## data
            'stockDataDicts': [self._convertStockDataToNumbaDict(ps) for ps in precedingSets],
            'dateDataDict': self._generateDateDicts([d.period_date for ps in precedingSets for d in ps]),
            'vixDataDict': self._convertVixDataToNumbaDict(vixData),
            # 'googleInterestsDicts': [self._convertGoogleInterestDataToNumbaDict(gih) for gih in googleInterestsHandlers],
            'googleInterestsDicts': googleInterestsDicts,
            'indicatorDataDicts': [self._convertIndicatorDataToNumbaDict(dpi.stockDataHandler.getPrecedingIndicators(dpi.index)) for dpi in dataPointInstances],
            'earningsDateMappingDicts': [self._generateEarningsDateNumbaDict(precedingSets[i], shortcdict(earningsDateHandlers, dataPointInstances[i].stockDataHandler.getTickerTuple())) for i in range(len(precedingSets))],
            # financialDataSet=None, # TODO
            # stockSplits=None, # TODO
            
            'foundedDates': [self._convertFoundedDate(dpi.stockDataHandler.symbolData.founded) for dpi in dataPointInstances],
            'ipoDates': [self._convertIPODate(
                # dpi.stockDataHandler.symbolData.?
                'todo'
                ) for dpi in dataPointInstances],
            'etfFlags': [dpi.stockDataHandler.symbolData.asset_type == 'ETF' for dpi in dataPointInstances],

            ## python-generated values
            'inputVectorDataTypeNames': list([i.name for i in InputVectorDataType])
        }

        print('build all time:', time.time() - startt)

        return _inputVectorFactoryLine(**factoryLineKWArgs)

    # @numba.njit
    def build(self,
              dataPointInstance: DataPointInstance=None,
              vixData=None, 
              googleInterestsDict: Dict[str,float]={}, 
              financialDataSet=None,  stockSplits=None,
              earningsDateHandler: StockEarningsDateHandler=None,
              ## other
              getSplitStat=False, **kwargs):

        # stockDataDict = self._convertStockDataToNumbaDict(stockDataSet)
        # foundedDate = self._convertFoundedDate(foundedDate)
        # ipoDate = self._convertIPODate(ipoDate)

        # return _inputVectorFactoryWorker(
        #     ## config
        #     **self._configKWArgs(),
        #     getSplitStat=getSplitStat,
        #     ## data
        #     stockDataDict=stockDataDict,
        #     dateDataDict=self._generateDateDicts(stockDataDict.keys()),
        #     vixDataDict=self._convertVixDataToNumbaDict(vixData),
        #     googleInterestsDict=self._convertGoogleInterestDataToNumbaDict(googleInterests),
        #     indicatorDataDict=self._convertIndicatorDataToNumbaDict(indicators),
        #     earningsDateMappingDict=self._generateEarningsDateNumbaDict(stockDataSet, earningsDateHandler),
        #     # financialDataSet=None, # TODO
        #     # stockSplits=None, # TODO

        #     foundedDate=foundedDate, ipoDate=ipoDate, etfFlag=etfFlag,
        #     # exchange=exchange,
        #     # sector=sector, sectorLookupList=self.dbm.getSectors()

        #     inputVectorDataTypeNames=list([i.name for i in InputVectorDataType])
        # )
    
        seq_inpVecStats, rec_inpVecStats, staticArrays, semiSeriesArrays, seriesArrays = self.buildAll(
            ## config
            **self._configKWArgs(),
            getSplitStat=getSplitStat,
            ## data
            dataPointInstances=[dataPointInstance],
            vixData=vixData,
            googleInterestsHandlers=googleInterestsDict,
            earningsDateHandlers=[earningsDateHandler] if earningsDateHandler else None,
            # financialDataSet=None, # TODO
            # stockSplits=None, # TODO

            # sector=sector, sectorLookupList=self.dbm.getSectors()

            inputVectorDataTypeNames=list([i.name for i in InputVectorDataType])
        )

        return seq_inpVecStats, rec_inpVecStats, *([staticArrays[0], semiSeriesArrays[0], seriesArrays[0]] if not getSplitStat else [None, None, None])
    

    def _buildMockData(self, precedingRange=1):
        mockexchange = 'mockexchange'
        mocksymbol = 'mocksymbol'
        mockstartdt = '2000-01-01'
        def _gendt(x): return (date.fromisoformat(mockstartdt) + timedelta(days=x)).isoformat()
        mocklistdt = '1970-01-01'
        mockipodt = '1999-01-01'
        mockstockDataSet = [recdotdict({
            'period_date': _gendt(x),
            'open': 5.1 + x,
            'high': 6.1 + x,
            'low': 7.1 + x,
            'close': 8.1 + x,
            'volume': 50.1 + x
        }) for x in range(precedingRange)]
        mockvix = recdotdict({
            _gendt(x): {
                'date': _gendt(x),
                'open': 7.2 + x,
                'high': 8.2 + x,
                'low': 9.2 + x,
                'close': 10.2 + x
            } for x in range(precedingRange)
        })
        mockfinancialDataSet = [recdotdict({
            'period': '20120112',
            'filed': '20090606',
            'quarter': 2,
            'nums': {
                'Assets': 9000,
                'Liabilities': 250,
                'StockholdersEquity': 8750
            }
        })]
        mockginterests = recdotdict({
            _gendt(x): 6.3 + x for x in range(precedingRange)
        })
        mockindicators = recdotdict({
            k: [9.4 + x for x in range(precedingRange)] for k in self.getIndicators()
        })
        mockindicators[IndicatorType.DIS] = [(3.5+x,3.5) for x in range(precedingRange)]
        mockindicators[IndicatorType.BB] = [(4.6+x,4.6+x,4.6+x) for x in range(precedingRange)]
        mockindicators[IndicatorType.ST] = [(2.7+x,SuperTrendDirection.UP) for x in range(precedingRange)]

        mocksymdata = recdotdict({
            'exchange': mockexchange,
            'symbol': mocksymbol,
            'founded': mocklistdt,
            'ipoDate': mockipodt,
            'asset_type': 'ETF'
        })

        mocksdh = StockDataHandler(mockstockDataSet, mocksymdata, precedingRange=precedingRange)
        mocksdh.indicators = mockindicators
        mockdpi = DataPointInstance(None, mocksdh, precedingRange, None)

        mockgidict = recdotdict({(mockexchange, mocksymbol): {'dataDict': mockginterests}})

        return { 'dataPointInstance': mockdpi, 'vixData': mockvix, 'googleInterestsDict': mockgidict, 'financialDataSet': mockfinancialDataSet }


    def getStats(self, precedingRange=1):
        if not self.stats or precedingRange != 1:
            seq_stats, rec_stats, _,_,_ = self.build(**self._buildMockData(precedingRange), sector='Technology', exchange='NYSE', stockSplits=[1], etfFlag=False, getSplitStat=True)
            self.stats = rec_stats if self.config.network.recurrent else seq_stats
        return self.stats

    def getInputSize(self, precedingRange=1):
        if self.config.network.recurrent:
            stats = self.getStats(precedingRange)
            # if len(stats) and type(list(stats.keys())[0]) != InputVectorDataType:
            #     stats = { }
            return [sum(stats[t.name].values()) for t in InputVectorDataType]
        else:
            return sum(self.getStats(precedingRange).values())

    # def build(self, *args):
    #     return self._inputVector(*args)

@numba.njit(numba.int64[:](numba.int64, numba.int64, 
                        #    numba.types.unicode_type[:], 
                        #    ommitted(numba.int64), omitted(numba.int64)
                           ))
def _getCategoricalVector(i, max=None, 
                        #   lookupList=numpy.array([], dtype='U'), ## TODO: https://stackoverflow.com/questions/46123657/numba-calling-jit-with-explicit-signature-using-arguments-with-default-values
                        #   topBuffer=0, bottomBuffer=0
                          ):
    ## integer input
    if max:
        if i >= max: raise ValueError
        endrange = max - i - 1
    ## string input
    # if len(lookupList) > 0:
    #     foundIndx = -1
    #     for lindx in range(len(lookupList)):
    #         if i == lookupList[lindx]: 
    #             foundIndx = lindx
    #             break
        
    #     if foundIndx != -1: i = foundIndx + 1 + bottomBuffer
    #     else: i = 0    ## not found = 0
    #     endrange = len(lookupList) - i + topBuffer

    retl = numpy.zeros(i + 1 + endrange, dtype='i8')
    retl[i] = 1
    return retl
    # return [0 for x in range(i)] + [1] + [0 for x in range(endrange)]

@numba.njit(parallel=True)
def _inputVectorFactoryLine(

# # @numba.njit(parallel=True)
# def _inputVectorFactoryWorker(

        ## config (from self global config)
        recurrentNetwork=False, dayOfMonthDataForm=None, dayOfWeekDataForm=None, monthOfYearDataForm=None, superTrendDataForm=None, includeDatesForFinancials=False,
            earningsDateDataForm_vectorSize2=False,
        featureTuples=None,
        getSplitStat=False, # recdotdict

        ## worker
        ## data
        # stockDataDict={}, # convertStockDataToNumbaDict
        # dateDataDict={}, # generateDateDicts; supporting utility data
        # vixDataDict={}, # convertVixDataToNumbaDict
        # googleInterestsDict={}, # convertGoogleInterestDataToNumbaDict
        # indicatorDataDict={}, # convertIndicatorDataToNumbaDict
        # earningsDateMappingDict={}, # generateEarningsDateNumbaDict
        # # financialDataSet=None, # TODO
        # # stockSplits=None, # TODO

        # foundedDate=None, ipoDate=None, etfFlag=None,
        # # exchange=None,
        # # sector=None, sectorLookupList=[],
        ## END worker

        ## factory line
        ## data
        stockDataDicts=[], # convertStockDataToNumbaDict
        dateDataDict={}, # generateDateDicts; supporting utility data
        vixDataDict={}, # convertVixDataToNumbaDict
        googleInterestsDicts=[], # convertGoogleInterestDataToNumbaDict
        earningsDateMappingDicts=[], # generateEarningsDateNumbaDict
        indicatorDataDicts=[], # convertIndicatorDataToNumbaDict

        foundedDates=[], # _convertFoundedDate
        ipoDates=[], # todo
        etfFlags=[], # bools
        ## END factory line

        ## python-generated values needed for njit execution; do not touch, or ensure they are passed with their default value if noted in comment
        minGoogleDatetime64=numpy.datetime64(minGoogleDate.isoformat()).view('int64'), # leave
        inputVectorDataTypeNames=list([i.name for i in InputVectorDataType]) # pass
):
        ## factory line
        staticArrays = []
        semiSeriesArrays = []
        seriesArrays = []
        for stockDataDict, googleInterestsDict, earningsDateMappingDict, indicatorDataDict, foundedDate, ipoDate, etfFlag in zip(stockDataDicts, googleInterestsDicts, earningsDateMappingDicts, indicatorDataDicts, foundedDates, ipoDates, etfFlags):
        ## END factory line

            ## all dates are numpy.datetime64, including keys and values
            stockDataDictKeys = list(stockDataDict.keys())

            ## i.e. SERIES, len(stockDataDictKeys)
            arraySizeRequired = numpy.zeros(len(featureTuples), dtype='i8')
            x1 = len(stockDataDictKeys)

            featureVectorTypes = []

            ## loop thru all features and sub-features and determine array sizes needed, vector types
            # e.g. open FeatureExtraType.KEY stock_open
            for ftindx, (k, extraType, compositeKey) in enumerate(featureTuples):
                logstuff = False

                ##############################################################################################################################
                ## daily "instances"
                if extraType == FeatureExtraType.KEY:
                    featureVectorTypes.append(inputVectorDataTypeNames[2]) ## SERIES
                    arraySizeRequired[ftindx] = 1

                elif extraType == FeatureExtraType.VIXKEY:
                    featureVectorTypes.append(inputVectorDataTypeNames[2]) ## SERIES
                    arraySizeRequired[ftindx] = 1

                elif k == 'dayOfWeek':
                    featureVectorTypes.append(inputVectorDataTypeNames[2]) ## SERIES
                    if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                        arraySizeRequired[ftindx] = 1
                    elif dayOfMonthDataForm == DataFormType.VECTOR:
                        arraySizeRequired[ftindx] = 5

                # TODO: monthrange equivalent
                # elif k == 'dayOfMonth':
                #     vectorListType = InputVectorDataType.SERIES

                #     if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #         vectorAsList = [(pdt.day - 1)/monthrange(pdt.year, pdt.month)[1] - (0.5 if dayOfMonthDataForm == DataFormType.INTEGER else 0) for pdt in stockDataDictKeys]
                #     elif dayOfMonthDataForm == DataFormType.VECTOR:
                #         vectorAsList = [i for pdt in stockDataDictKeys for i in _getCategoricalVector(dateDataDict[pdt]['day'] - 1, max=31)]

                elif k == 'monthOfYear':
                    featureVectorTypes.append(inputVectorDataTypeNames[2]) ## SERIES
                    if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                        arraySizeRequired[ftindx] = 1
                    elif dayOfMonthDataForm == DataFormType.VECTOR:
                        arraySizeRequired[ftindx] = 12

                elif k == 'googleInterests':
                    featureVectorTypes.append(inputVectorDataTypeNames[2]) ## SERIES
                    arraySizeRequired[ftindx] = 4

                # elif k == 'stockSplits':
                #     vectorListType = InputVectorDataType.SERIES
                #     # stockSplitDates = [s.period_date for s in stockSplits]
                #     ## zero center split ratio: 1:2 -> 2, 3:1 -> -3
                #     stockSplitDict = {s.date: ((max(s.split_from, s.split_to) / min(s.split_from, s.split_to)) - 1) * (1 if s.split_from < s.split_to else -1) for s in stockSplits}

                #     vectorAsList = [(1 if splitBooleanAndNotRatio else stockSplitDict[pdt]) if pdt in stockSplitDict.keys() else 0 for pdt in stockDataDictKeys for splitBooleanAndNotRatio in [True, False]]

                elif k == 'earningsDate':
                    featureVectorTypes.append(inputVectorDataTypeNames[2]) ## SERIES
                    arraySizeRequired[ftindx] = 2 if earningsDateDataForm_vectorSize2 else 4

                elif compositeKey.startswith(indicatorsKey):
                    featureVectorTypes.append(inputVectorDataTypeNames[2]) ## SERIES
                    if k == IndicatorTypeSimplified.ST:
                        if superTrendDataForm == DataFormType.VECTOR:
                            # arraySizeRequired[ftindx] = len(indicatorDataDict[k]) * 2
                            arraySizeRequired[ftindx] = 2
                        else: ## INTEGER
                            # arraySizeRequired[ftindx] = len(indicatorDataDict[k])
                            arraySizeRequired[ftindx] = 1
                    else:
                        if extraType == FeatureExtraType.SINGLE:
                            # arraySizeRequired[ftindx] = len(indicatorDataDict[k])
                            arraySizeRequired[ftindx] = 1
                        else: ## multiple
                            # arraySizeRequired[ftindx] = len(indicatorDataDict[k]) * len(indicatorDataDict[k][0])
                            arraySizeRequired[ftindx] = len(indicatorDataDict[k][0])

                #region semi-series
                ##############################################################################################################################
                ## non-daily, semi-repeated "instances"
                # elif k == 'financials':
                #     vectorListType = InputVectorDataType.SEMISERIES
                #     tags = flatten([v['tierTags'][t] for t in range(v['maxTierIndex'])]) ## combine all tags from tiers upto and including v['maxTierIndex']

                #     def createReportVector(report={}, blank=False):
                #         retvector = []

                #         ## quarter
                #         if blank:
                #             retvector += [0,0,0,0]
                #         else:
                #             retvector += _getCategoricalVector(report.quarter - 1, 4)
                        
                #         if includeDatesForFinancials:
                #             ## month for: end of quarter, filing
                #             if monthOfYearDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #                 if blank:
                #                     monthGen = lambda d: [0]
                #                 else:
                #                     monthGen = lambda d: [(d.month - 1)/12 - (0.5 if monthOfYearDataForm == DataFormType.INTEGER else 0)]
                #             elif monthOfYearDataForm == DataFormType.VECTOR:
                #                 if blank:
                #                     monthGen = lambda d: [0 for x in range(12)]
                #                 else:
                #                     monthGen = lambda d: _getCategoricalVector(d.month - 1, max=12)
                            
                #             ## ending month of quarter
                #             retvector += monthGen(_edgarformatd(report.period) if not blank else None)

                #             ## filing date
                #             ## include bit about how many days are in month? 28, 29, 30, 31
                #             if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #                 if blank:
                #                     dayGen = lambda d: [0]
                #                 else:
                #                     dayGen = lambda d: [(d.day - 1)/monthrange(d.year, d.month)[1] - (0.5 if dayOfMonthDataForm == DataFormType.INTEGER else 0)]
                #             elif dayOfMonthDataForm == DataFormType.VECTOR:
                #                 if blank:
                #                     dayGen = lambda d: [0 for x in range(31)]
                #                 else:
                #                     dayGen = lambda d: _getCategoricalVector(d.day - 1, max=31)
                #             filingDate = _edgarformatd(report.filed) if not blank else None
                #             retvector += dayGen(filingDate)
                #             retvector += monthGen(filingDate)
                #         if logstuff: print('intermiediateretvector',len(retvector))

                #         ## add values of each tag within the config (tiered) scope
                #         for k in tags:
                #             if k not in tags: continue
                #             if blank: 
                #                 retvector.extend([0,0]) ## for filling out the overall vector if date range resulted in less than max reports
                #             else:
                #                 try:
                #                     retvector.extend([
                #                         1,              ## is value present in report
                #                         shortc(report['nums'][k], 0)   ## actual value
                #                     ])
                #                 except KeyError:
                #                     retvector.extend([0, 0])
                        
                #         if logstuff: print('finalretvec',len(retvector), blank)
                        
                #         return retvector
                #     ## done createReportVector

                #     vectorAsList = [[],[]]
                #     try:
                #         reportNotFiledYetForCurrentPeriod = [1 if asDate(stockDataDictKeys[-1]).month - _edgarformatd(financialDataSet[-1].period).month > 3 else 0]
                #     except IndexError:
                #         reportNotFiledYetForCurrentPeriod = [0]

                #     reportVector = []
                #     # first index = report presence flag
                #     for m in range(maxQuarters(len(stockDataDictKeys)) - len(financialDataSet)):
                #         reportVector += [0] + createReportVector(blank=True)

                #     for r in financialDataSet:
                #         reportVector += [1] + createReportVector(r)

                #     if logstuff: 
                #         print('maxq', maxQuarters(len(stockDataDictKeys)))
                #         print('fdset', len(financialDataSet))
                #         print('reportvec',len(reportVector))

                #     vectorAsList[0] = reportNotFiledYetForCurrentPeriod
                #     vectorAsList[1] = reportVector
                #endregion

                ##############################################################################################################################
                # non-daily, single "instances"
                # elif k == 'exchange':
                #     vectorListType = InputVectorDataType.STATIC
                #     vectorAsList = _getCategoricalVector(exchange, lookupList=standardExchanges)

                # elif k == 'sector':
                #     vectorListType = InputVectorDataType.STATIC
                #     vectorAsList = _getCategoricalVector(sector, lookupList=sectorLookupList, topBuffer=3)

                elif k == 'companyAge':
                    featureVectorTypes.append(inputVectorDataTypeNames[0]) ## STATIC
                    arraySizeRequired[ftindx] = 1

                elif k == 'ipoAge':
                    featureVectorTypes.append(inputVectorDataTypeNames[0]) ## STATIC
                    arraySizeRequired[ftindx] = 1

                elif k == 'etf':
                    featureVectorTypes.append(inputVectorDataTypeNames[0]) ## STATIC
                    arraySizeRequired[ftindx] = 1


                ##############################################################################################################################

            ## initialize matrices for vector arrays
            staticSizesRequiredCounts = {}
            # semiSeriesSizesRequiredCounts = {}
            seriesSizesRequiredCounts = {}
            sizeToMatrixIndexMapping = numpy.zeros(len(arraySizeRequired), dtype='i8')
            for ftindx,v in enumerate(arraySizeRequired):
                # v = int(v)
                if featureTuples[ftindx][1] == FeatureExtraType.SINGLE and not featureTuples[ftindx][2].startswith(indicatorsKey):
                    if v in staticSizesRequiredCounts:
                        staticSizesRequiredCounts[v] += 1
                    else:
                        staticSizesRequiredCounts[v] = 1
                    sizeToMatrixIndexMapping[ftindx] = staticSizesRequiredCounts[v] - 1
                # elif semi series
                else: ## series
                    if v in seriesSizesRequiredCounts:
                        seriesSizesRequiredCounts[v] += 1
                    else:
                        seriesSizesRequiredCounts[v] = 1
                    sizeToMatrixIndexMapping[ftindx] = seriesSizesRequiredCounts[v] - 1

            ## static matrix
            staticSizesRequiredCountsKeys = list(staticSizesRequiredCounts.keys())
            columnsRequired = numpy.zeros(len(staticSizesRequiredCountsKeys))
            for i,(k,v) in enumerate(staticSizesRequiredCounts.items()):
                columnsRequired[i] = k*v
            staticMatrix = numpy.zeros((len(staticSizesRequiredCountsKeys), int(columnsRequired.max())), dtype='f8')

            ## series matrices
            def generateSeriesMatrix(x): 
                return numpy.zeros((seriesSizesRequiredCounts[x], x * x1), dtype='f8')
            sizesRequiredCountsKeys = list(seriesSizesRequiredCounts.keys())
            if 1 in sizesRequiredCountsKeys: x1Matrix = numpy.zeros(seriesSizesRequiredCounts[1] * x1, dtype='f8')
            if 2 in sizesRequiredCountsKeys: x2Matrix = generateSeriesMatrix(2)
            if 3 in sizesRequiredCountsKeys: x3Matrix = generateSeriesMatrix(3)
            if 4 in sizesRequiredCountsKeys: x4Matrix = generateSeriesMatrix(4)
            if 5 in sizesRequiredCountsKeys: x5Matrix = generateSeriesMatrix(5)
            if 12 in sizesRequiredCountsKeys: x12Matrix = generateSeriesMatrix(12)

            if logstuff: 
                print('size req cont', seriesSizesRequiredCounts)
                # print('array size req', arraySizeRequired)
                # print('feats', featureTuples)
                for a,f in zip(arraySizeRequired, featureTuples):
                    print(a, f)
                print('done zip loop')

            ## TODO
            ## if loaded, should be using its own config; otherwise network is new and as such was initialized with gconfig
            seq_inpVecStats = _newNumbaDict(
                keyType=numba.types.unicode_type,
                valueType=numba.types.int64
            )
                # def _newDict(): return _newNumbaDict(key_type=numba.types.unicode_type, value_type=numba.types.int64)
            rec_inpVecStats = _newNumbaDict(
                keyType=numba.types.unicode_type,
                valueType=inpVecStatsDictType
            )
            for n in inputVectorDataTypeNames:
                rec_inpVecStats[n] = _inpVecStats_newNumbaDict()

            ## REMOVE?
            # retarr = []
            # seriesarr = []
            # seriesmatrix = []
            # semiseriesarr = []
            # staticarr = []

            vectorLength = 0

            ## loop thru all features/sub-features again and add them to their respective matrices
            # e.g. open FeatureExtraType.KEY stock_open
            for ftindx, (k, extraType, compositeKey) in enumerate(featureTuples):
                logstuff = False

                ##############################################################################################################################
                ## daily "instances"
                if extraType == FeatureExtraType.KEY:
                    # vectorListType = InputVectorDataType.SERIES
                    # print(x1Matrix[0])
                    # print(x1Matrix[sizeToMatrixIndexMapping[ftindx]])
                    for dindx,pdt in enumerate(stockDataDictKeys):
                        # print(x1Matrix[sizeToMatrixIndexMapping[ftindx]+dindx])

                        # print(stockDataDict[pdt][k])
                        # print(f'{k} inserting at {(x1*sizeToMatrixIndexMapping[ftindx])+dindx} : {(x1*sizeToMatrixIndexMapping[ftindx])} + {dindx}')
                        x1Matrix[(sizeToMatrixIndexMapping[ftindx]*x1)+dindx] = stockDataDict[pdt][k]
                    vectorLength = len(stockDataDictKeys)

                elif extraType == FeatureExtraType.VIXKEY:
                    # vectorListType = InputVectorDataType.SERIES
                    for dindx,pdt in enumerate(stockDataDictKeys):
                        x1Matrix[(sizeToMatrixIndexMapping[ftindx]*x1)+dindx] = (vixDataDict[pdt])[k]
                    vectorLength = len(stockDataDictKeys)

                elif k == 'dayOfWeek':
                    # vectorListType = InputVectorDataType.SERIES
                    if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                        for dindx,pdt in enumerate(stockDataDictKeys):
                            x1Matrix[(sizeToMatrixIndexMapping[ftindx]*x1)+dindx] = datetime64Weekday(pdt)/6 - (0.5 if dayOfWeekDataForm == DataFormType.INTEGER else 0)
                        vectorLength = len(stockDataDictKeys)
                    elif dayOfMonthDataForm == DataFormType.VECTOR:
                        for dindx,pdt in enumerate(stockDataDictKeys):
                            for d2indx,i in enumerate(_getCategoricalVector(datetime64Weekday(pdt), max=5)):
                                x5Matrix[sizeToMatrixIndexMapping[ftindx]][(dindx*5)+d2indx] = i
                        vectorLength = len(stockDataDictKeys) * 5

                #region dayofmonth
                # TODO: monthrange equivalent
                # elif k == 'dayOfMonth':
                #     vectorListType = InputVectorDataType.SERIES

                #     if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #         vectorAsList = [(pdt.day - 1)/monthrange(pdt.year, pdt.month)[1] - (0.5 if dayOfMonthDataForm == DataFormType.INTEGER else 0) for pdt in stockDataDictKeys]
                #     elif dayOfMonthDataForm == DataFormType.VECTOR:
                #         vectorAsList = [i for pdt in stockDataDictKeys for i in _getCategoricalVector(dateDataDict[pdt]['day'] - 1, max=31)]
                #endregion

                elif k == 'monthOfYear':
                    # vectorListType = InputVectorDataType.SERIES
                    if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                        for dindx,pdt in enumerate(stockDataDictKeys):
                            x1Matrix[(sizeToMatrixIndexMapping[ftindx]*x1)+dindx] = (dateDataDict[pdt]['month'] - 1)/12 - (0.5 if monthOfYearDataForm == DataFormType.INTEGER else 0)
                        vectorLength = len(stockDataDictKeys)
                    elif dayOfMonthDataForm == DataFormType.VECTOR:
                        for dindx,pdt in enumerate(stockDataDictKeys):
                            for d2indx,i in enumerate(_getCategoricalVector(dateDataDict[pdt]['month'] - 1, max=12)):
                                x12Matrix[sizeToMatrixIndexMapping[ftindx]][(dindx*12)+d2indx] = i
                        vectorLength = len(stockDataDictKeys) * 12

                elif k == 'googleInterests':
                    # vectorListType = InputVectorDataType.SERIES
                    for dindx in range(len(stockDataDictKeys)):
                        pdt = stockDataDictKeys[dindx]
                        giHasDate = pdt in googleInterestsDict
                        givector = [
                            1 if pdt < minGoogleDatetime64 else 0,               ## date is before any Google data is available, 0 !=~ 0
                            1 if dindx > len(stockDataDictKeys) - 4 else 0,  ## data is not available on date due to how recent it is, 0 !=~ 0
                            1 if not giHasDate else 0,                  ## data unknown, may have not been collected yet or due to lack of topic ID
                            googleInterestsDict[pdt] if giHasDate and dindx <= len(stockDataDictKeys) - 4 else 0
                            # googleInterests[pdt] if index <= len(stockDataDictKeys) - 4 else 0
                        ]
                        # print('gi', givector, sizeToMatrixIndexMapping[ftindx], dindx*4)
                        for d2indx,d in enumerate(givector):
                            x4Matrix[sizeToMatrixIndexMapping[ftindx]][(dindx*4)+d2indx] = d
                    vectorLength = len(stockDataDictKeys) * 4

                #region stocksplits
                # elif k == 'stockSplits':
                #     vectorListType = InputVectorDataType.SERIES
                #     # stockSplitDates = [s.period_date for s in stockSplits]
                #     ## zero center split ratio: 1:2 -> 2, 3:1 -> -3
                #     stockSplitDict = {s.date: ((max(s.split_from, s.split_to) / min(s.split_from, s.split_to)) - 1) * (1 if s.split_from < s.split_to else -1) for s in stockSplits}

                #     vectorAsList = [(1 if splitBooleanAndNotRatio else stockSplitDict[pdt]) if pdt in stockSplitDict.keys() else 0 for pdt in stockDataDictKeys for splitBooleanAndNotRatio in [True, False]]
                #endregion

                elif k == 'earningsDate':
                    # vectorListType = InputVectorDataType.SERIES
                    if earningsDateMappingDict:
                        for index in range(len(stockDataDictKeys)):
                            pdt = stockDataDictKeys[index]
                            earningsDate = earningsDateMappingDict[pdt]
                            if earningsDate:
                                daydiff = getTimedeltaInDays(earningsDate, pdt)
                            
                            if earningsDateDataForm_vectorSize2:
                                edvector = [
                                    1 if earningsDate else 0, ## current earnings date is known; unknown being either missing, or current day is more than 180 days (~2 quarters) away from closest known earnings date
                                    daydiff if earningsDate else 0 ## distance (in days) from current earnings date
                                ]
                                for d2indx,d in enumerate(edvector):
                                    x2Matrix[sizeToMatrixIndexMapping[ftindx]][(dindx*2)+d2indx] = d
                                    
                            else:
                                edvector = [
                                    1 if earningsDate else 0, ## current earnings date is known; unknown being either missing, or current day is more than 180 days (~2 quarters) away from closest known earnings date
                                    1 if earningsDate and daydiff > 0 else 0, ## value is days until current (i.e. most recent) earnings date
                                    1 if earningsDate and daydiff < 0 else 0, ## value is days after current (i.e. most recent) earnings date
                                    abs(daydiff) if earningsDate else 0 ## distance (in days) from current earnings date
                                ]
                                for d2indx,d in enumerate(edvector):
                                    x4Matrix[sizeToMatrixIndexMapping[ftindx]][(index*4)+d2indx] = d
                    else:
                        # if earningsDateDataForm_vectorSize2:
                        #     vectorAsList = [0,0]*len(stockDataDictKeys)
                        # else:
                        #     vectorAsList = [0,0,0,0]*len(stockDataDictKeys)
                        ## matrix already filled with zeros
                        pass
                    vectorLength = len(stockDataDictKeys) * (2 if earningsDateDataForm_vectorSize2 else 4)

                elif compositeKey.startswith(indicatorsKey):
                    # vectorListType = InputVectorDataType.SERIES
                    if k == IndicatorTypeSimplified.ST:
                        if superTrendDataForm == DataFormType.VECTOR:
                            for dindx,(val, dir) in enumerate(indicatorDataDict[k]):
                                stvector = [
                                    val,
                                    1 if dir == 0 else 0 # (dir) 0 = SuperTrendDirection.UP
                                ]
                                for d2indx,d in enumerate(stvector):
                                    x2Matrix[sizeToMatrixIndexMapping[ftindx]][(dindx*2)+d2indx] = d
                            vectorLength = len(indicatorDataDict[k]) * 2
                        else: ## INTEGER
                            for dindx,(val, dir) in enumerate(indicatorDataDict[k]):
                                x1Matrix[(sizeToMatrixIndexMapping[ftindx]*x1)+dindx] = val * (-1 if dir == 1 else 1) # (dir) 1 = SuperTrendDirection.UP
                            vectorLength = len(indicatorDataDict[k])
                                    
                    else:
                        if extraType == FeatureExtraType.SINGLE:
                            for dindx, val in enumerate(indicatorDataDict[k]):
                                x1Matrix[(sizeToMatrixIndexMapping[ftindx]*x1)+dindx] = val[0]
                            vectorLength = len(indicatorDataDict[k])
                        else: ## multiple
                            for dindx, tpl in enumerate(indicatorDataDict[k]):
                                for d2indx,d in enumerate(tpl):
                                    if len(tpl) == 2:
                                        x2Matrix[sizeToMatrixIndexMapping[ftindx]][(dindx*2)+d2indx] = d
                                    elif len(tpl) == 3:
                                        x3Matrix[sizeToMatrixIndexMapping[ftindx]][(dindx*3)+d2indx] = d
                                    else:
                                        # raise ValueError(f'Unexpected tuple length for indicator {k}')
                                        raise ValueError('Unexpected tuple length for indicator')    
                            vectorLength = len(indicatorDataDict[k]) * len(tpl)

                ##############################################################################################################################
                ## non-daily, semi-repeated "instances"
                # elif k == 'financials':
                #     vectorListType = InputVectorDataType.SEMISERIES
                #     tags = flatten([v['tierTags'][t] for t in range(v['maxTierIndex'])]) ## combine all tags from tiers upto and including v['maxTierIndex']

                #     def createReportVector(report={}, blank=False):
                #         retvector = []

                #         ## quarter
                #         if blank:
                #             retvector += [0,0,0,0]
                #         else:
                #             retvector += _getCategoricalVector(report.quarter - 1, 4)
                        
                #         if includeDatesForFinancials:
                #             ## month for: end of quarter, filing
                #             if monthOfYearDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #                 if blank:
                #                     monthGen = lambda d: [0]
                #                 else:
                #                     monthGen = lambda d: [(d.month - 1)/12 - (0.5 if monthOfYearDataForm == DataFormType.INTEGER else 0)]
                #             elif monthOfYearDataForm == DataFormType.VECTOR:
                #                 if blank:
                #                     monthGen = lambda d: [0 for x in range(12)]
                #                 else:
                #                     monthGen = lambda d: _getCategoricalVector(d.month - 1, max=12)
                            
                #             ## ending month of quarter
                #             retvector += monthGen(_edgarformatd(report.period) if not blank else None)

                #             ## filing date
                #             ## include bit about how many days are in month? 28, 29, 30, 31
                #             if dayOfMonthDataForm in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #                 if blank:
                #                     dayGen = lambda d: [0]
                #                 else:
                #                     dayGen = lambda d: [(d.day - 1)/monthrange(d.year, d.month)[1] - (0.5 if dayOfMonthDataForm == DataFormType.INTEGER else 0)]
                #             elif dayOfMonthDataForm == DataFormType.VECTOR:
                #                 if blank:
                #                     dayGen = lambda d: [0 for x in range(31)]
                #                 else:
                #                     dayGen = lambda d: _getCategoricalVector(d.day - 1, max=31)
                #             filingDate = _edgarformatd(report.filed) if not blank else None
                #             retvector += dayGen(filingDate)
                #             retvector += monthGen(filingDate)
                #         if logstuff: print('intermiediateretvector',len(retvector))

                #         ## add values of each tag within the config (tiered) scope
                #         for k in tags:
                #             if k not in tags: continue
                #             if blank: 
                #                 retvector.extend([0,0]) ## for filling out the overall vector if date range resulted in less than max reports
                #             else:
                #                 try:
                #                     retvector.extend([
                #                         1,              ## is value present in report
                #                         shortc(report['nums'][k], 0)   ## actual value
                #                     ])
                #                 except KeyError:
                #                     retvector.extend([0, 0])
                        
                #         if logstuff: print('finalretvec',len(retvector), blank)
                        
                #         return retvector
                #     ## done createReportVector

                #     vectorAsList = [[],[]]
                #     try:
                #         reportNotFiledYetForCurrentPeriod = [1 if asDate(stockDataDictKeys[-1]).month - _edgarformatd(financialDataSet[-1].period).month > 3 else 0]
                #     except IndexError:
                #         reportNotFiledYetForCurrentPeriod = [0]

                #     reportVector = []
                #     # first index = report presence flag
                #     for m in range(maxQuarters(len(stockDataDictKeys)) - len(financialDataSet)):
                #         reportVector += [0] + createReportVector(blank=True)

                #     for r in financialDataSet:
                #         reportVector += [1] + createReportVector(r)

                #     if logstuff: 
                #         print('maxq', maxQuarters(len(stockDataDictKeys)))
                #         print('fdset', len(financialDataSet))
                #         print('reportvec',len(reportVector))

                #     vectorAsList[0] = reportNotFiledYetForCurrentPeriod
                #     vectorAsList[1] = reportVector


                ##############################################################################################################################
                # non-daily, single "instances"
                # elif k == 'exchange':
                #     vectorListType = InputVectorDataType.STATIC
                #     vectorAsList = _getCategoricalVector(exchange, lookupList=standardExchanges)

                # elif k == 'sector':
                #     vectorListType = InputVectorDataType.STATIC
                #     vectorAsList = _getCategoricalVector(sector, lookupList=sectorLookupList, topBuffer=3)

                elif k == 'companyAge':
                    # vectorListType = InputVectorDataType.STATIC
                    companyagedays = 0
                    if foundedDate:
                        # companyagedays = getTimedeltaInDays(stockDataDictKeys[-1], numpy.datetime64(f"{list(foundedDateDict.values()).join('-')}"))
                        # companyagedays = getTimedeltaInDays(
                        #     stockDataDictKeys[-1], 
                        #     numpy.datetime64(f"{foundedDateDict['year']}-{foundedDateDict['month']}-{foundedDateDict['day']}"))
                        companyagedays = getTimedeltaInDays(stockDataDictKeys[-1], foundedDate)

                        ## normalize
                        companyagedays /= 40 * 365

                        # vectorAsList = [
                        #     companyagedays,
                        #     # 1 if month else 0,  ## do we know month
                        #     # 1 if day else 0     ## do we know day
                        # ]
                    else:
                        # vectorAsList = [0,
                        #                 # 0,0
                        #                 ]
                        pass
                    
                    staticMatrix[sizeToMatrixIndexMapping[ftindx]] = companyagedays
                    vectorLength = 1

                elif k == 'ipoAge':
                    if ipoDate:
                        staticMatrix[sizeToMatrixIndexMapping[ftindx]] = getTimedeltaInDays(stockDataDictKeys[-1], ipoDate) / 40 / 365
                    vectorLength = 1

                elif k == 'etf':
                    if etfFlag:
                        staticMatrix[sizeToMatrixIndexMapping[ftindx]] = 1
                    vectorLength = 1


                ##############################################################################################################################


                if recurrentNetwork:
                    if k == 'financials':
                        pass
                    #     inpVecStats[InputVectorDataType.STATIC][compositeKey + InputVectorDataType.STATIC.value] = len(vectorAsList[0])
                    #     inpVecStats[InputVectorDataType.SEMISERIES][compositeKey] = len(vectorAsList[1])
                    #     staticarr += vectorAsList[0]
                    #     semiseriesarr += vectorAsList[1]
                    else:
                        rec_inpVecStats[featureVectorTypes[ftindx]][compositeKey] = vectorLength
                else:
                    seq_inpVecStats[compositeKey] = vectorLength
                    # retarr += vectorAsList


            ## construct series arrays from xmatrices
            staticSize = sum(list(rec_inpVecStats[inputVectorDataTypeNames[0]].values()))
            semiSeriesSize = sum(list(rec_inpVecStats[inputVectorDataTypeNames[1]].values()))
            seriesSize = sum(list(rec_inpVecStats[inputVectorDataTypeNames[2]].values()))
            # for indx, vectorType in enumerate(featureVectorTypes):
            #     if vectorType == inputVectorDataTypeNames[0]: ## static
            #         staticSize += arraySizeRequired[indx]
            #     elif vectorType == inputVectorDataTypeNames[1]: ## semi
            #         semiSeriesSize += arraySizeRequired[indx]
            #     elif vectorType == inputVectorDataTypeNames[2]: ## series
            #         seriesSize += arraySizeRequired[indx]
            staticarr = numpy.zeros(staticSize)
            semiseriesarr = numpy.zeros(semiSeriesSize)
            seriesarr = numpy.zeros(seriesSize)
            if logstuff:
                print('arr sizes', staticSize, semiSeriesSize, seriesSize)
                print('x1',list(x1Matrix))
                print('x2', x2Matrix)
                print('x3',x3Matrix)
                print('x4', x4Matrix)
                # try: print('x5',x5Matrix)
                # except UnboundLocalError: pass
                # try: print('x12',x12Matrix)
                # except UnboundLocalError: pass

            ## actual data required, so remap matrices to arrays
            
            ## factory line
            if getSplitStat:
                return seq_inpVecStats, rec_inpVecStats, staticArrays, semiSeriesArrays, seriesArrays
            ## END factory line
            else:
                staticIndex = 0
                for r in range(len(staticMatrix)):
                    if (r+1) in staticSizesRequiredCountsKeys:
                        for c in range(staticSizesRequiredCounts[r+1] * (r+1)):
                            staticarr[staticIndex] = staticMatrix[r][c]
                            staticIndex += 1
                
                ## TODO: semiseries

                seriesIndex = 0
                if recurrentNetwork:
                    ## flatten matrix in column order
                    for xindx in range(x1):
                        for indx, vectorType in enumerate(featureVectorTypes):
                            if vectorType == inputVectorDataTypeNames[2]: ## series
                                asize = arraySizeRequired[indx]
                                vsize = rec_inpVecStats[vectorType][featureTuples[indx][2]] # compositeKey
                                if asize == 1:
                                    seriesarr[seriesIndex] = x1Matrix[(sizeToMatrixIndexMapping[indx]*x1)+xindx]
                                    seriesIndex += 1
                                else:
                                    if asize == 2:
                                        matrix = x2Matrix
                                    elif asize == 3:
                                        matrix = x3Matrix
                                    elif asize == 4:
                                        matrix = x4Matrix
                                    elif asize == 5:
                                        matrix = x5Matrix
                                    elif asize == 12:
                                        matrix = x12Matrix
                                    for a in range(asize):
                                        seriesarr[seriesIndex] = matrix[sizeToMatrixIndexMapping[indx]][(xindx*asize)+a]
                                        seriesIndex += 1
                else:
                    ## TODO: sequential, this should all go into same array as static/semiseries stuff
                    for indx, vectorType in enumerate(featureVectorTypes):
                        if vectorType == inputVectorDataTypeNames[2]: ## series
                            asize = arraySizeRequired[indx]
                            vsize = rec_inpVecStats[vectorType][featureTuples[indx][2]] # compositeKey
                            if asize == 1:
                                for vindx in range(vsize):
                                    seriesarr[seriesIndex] = x1Matrix[(sizeToMatrixIndexMapping[indx]*x1)+vindx]
                                    seriesIndex += 1
                            else:
                                if asize == 2:
                                    matrix = x2Matrix
                                elif asize == 3:
                                    matrix = x3Matrix
                                elif asize == 4:
                                    matrix = x4Matrix
                                elif asize == 5:
                                    matrix = x5Matrix
                                elif asize == 12:
                                    matrix = x12Matrix
                                for xindx in range(x1):
                                    for a in range(asize):
                                        seriesarr[seriesIndex] = matrix[sizeToMatrixIndexMapping[indx]][(xindx*asize)+a]
                                        seriesIndex += 1

            #     if recurrentNetwork:
            #         ret = (numpy.array(staticarr), numpy.array(semiseriesarr), numpy.array(seriesarr))
            #     else:
            #         ret = numpy.array(retarr)
            #     return ret
            # return seq_inpVecStats, rec_inpVecStats, staticarr, semiseriesarr, seriesarr

        ## factory line
            staticArrays.append(staticarr)
            semiSeriesArrays.append(semiseriesarr)
            seriesArrays.append(seriesarr)
        
        return seq_inpVecStats, rec_inpVecStats, staticArrays, semiSeriesArrays, seriesArrays
        ## END factory line


@numba.njit
# (parallel=True)
def test(
    testvar
):
    print(testvar)
    # print(testvar['1999-01-010'])
    # print(testvar['1999-01-010']['open'])
    # print(list(testvar[1].keys())[-1])
    print(testvar['RSI'][2])
    print(testvar['RSI'][2][1])
    print(len(testvar['RSI'][2]))
    # print(list(SuperTrendDirection.__members__.values())[testvar['RSI'][2][1]] == SuperTrendDirection.UP)
    # print([k for k in SuperTrendDirection][testvar['RSI'][2][1]] == SuperTrendDirection.UP)
    # print(SuperTrendDirectionList[int(testvar['RSI'][2][1])] == SuperTrendDirection.UP)
    # print(numba.literal_unroll(SuperTrendDirection)[int(testvar['RSI'][2][1])] == SuperTrendDirection.UP)
    # print(numba.vectorize(SuperTrendDirection))


    test1 = lambda: [5]
    test2 = lambda: [2.4, 4]
    testl = [test1, test2]
    # testl.append(test2)
    print(testl[1]())
    # for t in testl:
    for tindx in range(len(testl)):
        print('t', tindx, test1(), test2())
        print(testl[tindx]())
    print(len(testl))
    return


if __name__ == '__main__':
    precedingRange=3
    # mockindicators = numba.typed.Dict.empty(
    #     key_type=numba.types.unicode_type,
    #     value_type=numba.types.float64[:, :]
    #     # value_type=numba.types.int64[:]
    # )
    # for k in [_ for _ in IndicatorTypeSimplified][:5]:
    #     # mockindicators[k.name] = numpy.array([[9, getIndex(SuperTrendDirection, SuperTrendDirection.UP)] for x in range(precedingRange)], dtype='f8')
    #     # mockindicators[k.name] = [numpy.array([9], dtype='f8') for x in range(precedingRange)]
    #     # mockindicators[k.name] = [[9] for x in range(precedingRange)]
    #     mockindicators[k.name] = numpy.array([[9] for x in range(precedingRange)], dtype='f8')
    #     # mockindicators[k.name] = numpy.zeros(3)
    # mockindicators[IndicatorTypeSimplified.DIS.name] = numpy.array([(3,3) for x in range(precedingRange)], dtype='f8')
    # # mockindicators[IndicatorTypeSimplified.BB] = numpy.array([(4,4,4) for x in range(precedingRange)], dtype='f8')
    # # mockindicators[IndicatorTypeSimplified.ST] = [(2,SuperTrendDirection.UP) for x in range(precedingRange)]

    # mockindicators = recdotdict({
    #         k: [9 for x in range(precedingRange)] for k in [_ for _ in IndicatorTypeSimplified][:5]
    #     })
    # mockindicators[IndicatorType.DIS] = [(3,3) for x in range(precedingRange)]
    # mockindicators[IndicatorType.BB] = [(4,4,4) for x in range(precedingRange)]
    # mockindicators[IndicatorType.ST] = [(2,SuperTrendDirection.UP) for x in range(precedingRange)]
    
    # ### convert to numbadict
    #     ## keys must be string literals (i.e. .name)
    #     ## numpy.array wraps values, with dtype='f8'
    #     ## internal lists can be tuples
    # retd = numba.typed.Dict.empty(
    #         key_type=numba.types.unicode_type,
    #         value_type=numba.types.float64[:, :]
    #     )
    # # retd = {}
    # for k,v in mockindicators.items():
    #     if k == IndicatorType.ST:
    #         v = [[s[0], getIndex(SuperTrendDirectionList, s[1])] for s in v]
    #     elif len(v) and not hasattr(v[0], '__len__'):
    #         ## all values must be within a sub-tuple/list
    #         v = [[s] for s in v]
    #     retd[k.name] = numpy.array(v, dtype='f8')
    # print('retd', retd)
    # ### end

    # test(retd)


    # print('outside', mockindicators)
    # test(mockindicators)
    ivf: InputVectorFactory = InputVectorFactory()

    # # print(_getCategoricalVector(2, 5, numpy.array(['5'], dtype='U')))
    # # print(_getCategoricalVector(0, 5))
    # print(ivf.getInputSize())
    # # # # print(ivf.getInputSize(200))
    # print(ivf.getStats())


    _,_,seriesSize = ivf.getInputSize()
    precrange = 3
    print(ivf._buildMockData(precrange))
    _,_,staticArr,_,seriesArr = ivf.build(**ivf._buildMockData(precrange), sector='Technology', exchange='NYSE', stockSplits=[], etfFlag=True)
    print('staticArr', staticArr)
    print('seriesArr', seriesArr)
    print(numpy.reshape(seriesArr, (precrange, seriesSize)))
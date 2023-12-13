import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, re, time
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Dict, List

from globalConfig import config as gconfig
from constants.enums import DataFormType, FeatureExtraType, IndicatorType, InputVectorDataType, SuperTrendDirection
from constants.values import standardExchanges, minGoogleDate, indicatorsKey
from utils.support import Singleton, flatten, recdotdict, _isoformatd, shortc, _edgarformatd, shortcdict
from utils.other import maxQuarters, normalizeValue
from structures.stockEarningsDateHandler import StockEarningsDateHandler
from managers.statsManager import StatsManager

# from managers.databaseManager import DatabaseManager
# dbm: DatabaseManager = DatabaseManager()
sm: StatsManager = StatsManager()
collectStats = True

loggedonce = False
warnedonce = False

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
                    tpls.append((k, v['extraType'], compositeKey))
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


    ## alt: https://www.fast.ai/2018/04/29/categorical-embeddings/
    def _getCategoricalVector(self, i, max=None, lookupList=None, topBuffer=0, bottomBuffer=0):
        ## integer input
        if max:
            if i >= max: raise ValueError
            endrange = max - i - 1
        ## string input
        if lookupList:
            try: i = lookupList.index(i) + 1 + bottomBuffer
            except ValueError: i = 0    ## not found = 0
            endrange = len(lookupList) - i + topBuffer

        return [0 for x in range(i)] + [1] + [0 for x in range(endrange)]

    def build(self,
              ## time series type data
              stockDataSet=None, vixData=None, financialDataSet=None, googleInterests: Dict[str,float]=None, stockSplits=None,
              indicators: Dict[IndicatorType, float]=None, earningsDateHandler: StockEarningsDateHandler=None,
              ## symbol/static type data
              foundedDate=None, ipoDate=None, sector=None, exchange=None, etfFlag=None,
              ## other
              getSplitStat=False, earningsDateNormalizationMax=None, **kwargs):
        global loggedonce
        global warnedonce
        if len(kwargs) and not warnedonce:
            warnedonce = True
            print('WARNING: input vector factory received unknown keyword arguments (', ', '.join(kwargs.keys()), ')')

        ## if loaded, should be using its own config; otherwise network is new and as such was initialized with gconfig
        if self.config.network.recurrent:
            inpVecStats = {e: {} for e in InputVectorDataType}
        else:
            inpVecStats = {}

        retarr = []
        seriesarr = []
        seriesmatrix = []
        semiseriesarr = []
        staticarr = []

        ## loop thru all features and sub-features incrementally adding them to the end of the vector
        # e.g. open FeatureExtraType.KEY stock_open
        for k, extraType, compositeKey in self.featureTuples:
            logstuff = False

            ##############################################################################################################################
            ## daily "instances"
            if extraType == FeatureExtraType.KEY:
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                vectorAsList = [d[k] for d in stockDataSet]
                if collectStats: sm.extraTypekeytime += time.time() - startt

            elif extraType == FeatureExtraType.VIXKEY:
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                vectorAsList = [(vixData[d.period_date])[k] for d in stockDataSet]
                if collectStats: sm.extraTypevixkeytime += time.time() - startt

            elif k == 'dayOfWeek':
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                # vectorAsList = [_isoformatd(d).weekday()/6 - 0.5 for d in stockDataSet]
                # if self.config.dataForm.dayOfWeek in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #     itemGen = lambda d: _isoformatd(d).weekday()/6 - (0.5 if self.config.dataForm.dayOfWeek == DataFormType.INTEGER else 0)
                # elif self.config.dataForm.dayOfWeek == DataFormType.VECTOR:
                #     itemGen = lambda d: self._getCategoricalVector(_isoformatd(d).weekday(), max=5)
                # vectorAsList = [itemGen(d) for d in stockDataSet]

                if self.config.dataForm.dayOfMonth in [DataFormType.INTEGER, DataFormType.NATURAL]:
                    vectorAsList = [_isoformatd(d).weekday()/6 - (0.5 if self.config.dataForm.dayOfWeek == DataFormType.INTEGER else 0) for d in stockDataSet]
                elif self.config.dataForm.dayOfMonth == DataFormType.VECTOR:
                    vectorAsList = [i for d in stockDataSet for i in self._getCategoricalVector(_isoformatd(d).weekday(), max=5)]

                if collectStats: sm.ktypedayofweektime += time.time() - startt

            elif k == 'dayOfMonth':
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                # # vectorAsList = [(dt.day - 1)/monthrange(dt.year, dt.month)[1] - 0.5 for dt in [_isoformatd(d) for d in stockDataSet]]

                # ## include bit about how many days are in month? 28, 29, 30, 31
                # if self.config.dataForm.dayOfMonth in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #     itemGen = lambda d: (d.day - 1)/monthrange(d.year, d.month)[1] - (0.5 if self.config.dataForm.dayOfMonth == DataFormType.INTEGER else 0)
                # elif self.config.dataForm.dayOfMonth == DataFormType.VECTOR:
                #     itemGen = lambda d: self._getCategoricalVector(d.day - 1, max=31)
                # vectorAsList = [itemGen(dt) for dt in [_isoformatd(d) for d in stockDataSet]]

                dts = [_isoformatd(d) for d in stockDataSet]
                if self.config.dataForm.dayOfMonth in [DataFormType.INTEGER, DataFormType.NATURAL]:
                    vectorAsList = [(d.day - 1)/monthrange(d.year, d.month)[1] - (0.5 if self.config.dataForm.dayOfMonth == DataFormType.INTEGER else 0) for d in dts]
                elif self.config.dataForm.dayOfMonth == DataFormType.VECTOR:
                    vectorAsList = [i for d in dts for i in self._getCategoricalVector(d.day - 1, max=31)]

                if collectStats: sm.ktypedayofmonthtime += time.time() - startt

            elif k == 'monthOfYear':
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                # vectorAsList = [(_isoformatd(d).month - 1)/12 - 0.5 for d in stockDataSet]

                # if self.config.dataForm.monthOfYear in [DataFormType.INTEGER, DataFormType.NATURAL]:
                #     itemGen = lambda d: (_isoformatd(d).month - 1)/12 - (0.5 if self.config.dataForm.monthOfYear == DataFormType.INTEGER else 0)
                # elif self.config.dataForm.monthOfYear == DataFormType.VECTOR:
                #     itemGen = lambda d: self._getCategoricalVector(_isoformatd(d).month - 1, max=12)
                # vectorAsList = [itemGen(d) for d in stockDataSet]

                if self.config.dataForm.dayOfMonth in [DataFormType.INTEGER, DataFormType.NATURAL]:
                    vectorAsList = [(_isoformatd(d).month - 1)/12 - (0.5 if self.config.dataForm.monthOfYear == DataFormType.INTEGER else 0) for d in stockDataSet]
                elif self.config.dataForm.dayOfMonth == DataFormType.VECTOR:
                    vectorAsList = [i for d in stockDataSet for i in self._getCategoricalVector(_isoformatd(d).month - 1, max=12)]

                if collectStats: sm.ktypemonthofyeartime += time.time() - startt

            elif k == 'googleInterests':
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                mindate = minGoogleDate.isoformat()
                vectorAsList = []
                for index,d in enumerate(stockDataSet):
                    giHasDate = d.period_date in googleInterests
                    vectorAsList.extend([
                        1 if d.period_date < mindate else 0,               ## date is before any Google data is available, 0 !=~ 0
                        1 if index > len(stockDataSet) - 4 else 0,  ## data is not available on date due to how recent it is, 0 !=~ 0
                        1 if not giHasDate else 0,                  ## data unknown, may have not been collected yet or due to lack of topic ID
                        googleInterests[d.period_date] if giHasDate and index <= len(stockDataSet) - 4 else 0
                        # googleInterests[d.period_date] if index <= len(stockDataSet) - 4 else 0
                    ])

                if collectStats: sm.ktypegoogleintereststime += time.time() - startt
            
            elif k == 'stockSplits':
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                # stockSplitDates = [s.period_date for s in stockSplits]
                ## zero center split ratio: 1:2 -> 2, 3:1 -> -3
                stockSplitDict = {s.date: ((max(s.split_from, s.split_to) / min(s.split_from, s.split_to)) - 1) * (1 if s.split_from < s.split_to else -1) for s in stockSplits}
                # vectorAsList = [*([1,stockSplitDict[d.period_date]] if d.period_date in stockSplitDict.keys() else [0,0]) for d in stockDataSet]
                # vectorAsList = [1 if d.period_date in stockSplitDict.keys() else 0 for d in stockDataSet]
                # vectorAsList += [stockSplitDict[d.period_date] if d.period_date in stockSplitDict.keys() else 0 for d in stockDataSet]
                vectorAsList = [(1 if splitBooleanAndNotRatio else stockSplitDict[d.period_date]) if d.period_date in stockSplitDict.keys() else 0 for d in stockDataSet for splitBooleanAndNotRatio in [True, False]]

                # seriesmatrix.append([1 if d.period_date in stockSplitDict.keys() else 0 for d in stockDataSet])
                # seriesmatrix.append([stockSplitDict[d.period_date] if d.period_date in stockSplitDict.keys() else 0 for d in stockDataSet])
                if collectStats: sm.ktypestocksplitstime += time.time() - startt

            elif k == 'earningsDate':
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                vectorAsList = []
                if earningsDateHandler:
                    for index,d in enumerate(stockDataSet):
                        earningsDate = earningsDateHandler.getNextEarningsDate(d.period_date)
                        if earningsDate:
                            daydiff = (date.fromisoformat(earningsDate) - date.fromisoformat(d.period_date)).days
                        
                        if self.config.dataForm.earningsDate.vectorSize2:
                            itlist = [
                                1 if earningsDate else 0, ## current earnings date is known; unknown being either missing, or current day is more than 180 days (~2 quarters) away from closest known earnings date
                                daydiff if earningsDate else 0 ## distance (in days) from current earnings date
                            ]
                        else:
                            itlist = [
                                1 if earningsDate else 0, ## current earnings date is known; unknown being either missing, or current day is more than 180 days (~2 quarters) away from closest known earnings date
                                1 if earningsDate and daydiff > 0 else 0, ## value is days until current (i.e. most recent) earnings date
                                1 if earningsDate and daydiff < 0 else 0, ## value is days after current (i.e. most recent) earnings date
                                abs(daydiff) if earningsDate else 0 ## distance (in days) from current earnings date
                            ]
                            
                            # 1 if earningsDate else 0, ## current earnings date is known; unknown being either missing, or current day is more than 180 days (~2 quarters) away from closest known earnings date
                            # 1 if earningsDate and daydiff > 0 else 0, ## value is days until current (i.e. most recent) earnings date
                            # abs(daydiff) if earningsDate else 0 ## distance (in days) from current earnings date

                        if earningsDateNormalizationMax:
                            itlist[-1] = normalizeValue(itlist[-1], earningsDateNormalizationMax)
                        vectorAsList.extend(itlist)
                else:
                    if self.config.dataForm.earningsDate.vectorSize2:
                        vectorAsList = [0,0]*len(stockDataSet)
                    else:
                        vectorAsList = [0,0,0,0]*len(stockDataSet)
                    # vectorAsList = [0,0,0]*len(stockDataSet)

                if collectStats: sm.ktypeearningsdatetime += time.time() - startt

            elif compositeKey.startswith(indicatorsKey):
                vectorListType = InputVectorDataType.SERIES
                if collectStats: startt = time.time()
                if k == IndicatorType.ST:
                    if self.config.dataForm.superTrend == DataFormType.VECTOR:
                        vectorAsList = []
                        for val, dir in indicators[k]:
                            vectorAsList.extend([
                                val,
                                1 if dir == SuperTrendDirection.UP else 0
                            ])
                    else: ## INTEGER
                        vectorAsList = [val * (-1 if dir == SuperTrendDirection.DOWN else 1) for val,dir in indicators[k]]
                else:
                    if extraType == FeatureExtraType.SINGLE:
                        vectorAsList = indicators[k]
                    else: ## multiple
                        vectorAsList = []
                        for tpl in indicators[k]:
                            vectorAsList.extend([*tpl])
                if collectStats: sm.indicatorskeytime += time.time() - startt


            ##############################################################################################################################
            ## non-daily, semi-repeated "instances"
            elif k == 'financials':
                vectorListType = InputVectorDataType.SEMISERIES
                if collectStats: startt = time.time()
                tags = flatten([v['tierTags'][t] for t in range(v['maxTierIndex'])]) ## combine all tags from tiers upto and including v['maxTierIndex']

                def createReportVector(report={}, blank=False):
                    retvector = []

                    ## quarter
                    if blank:
                        retvector += [0,0,0,0]
                    else:
                        retvector += self._getCategoricalVector(report.quarter - 1, 4)
                    
                    if self.config.feature.financials.includeDates:
                        ## month for: end of quarter, filing
                        if self.config.dataForm.monthOfYear in [DataFormType.INTEGER, DataFormType.NATURAL]:
                            if blank:
                                monthGen = lambda d: [0]
                            else:
                                monthGen = lambda d: [(d.month - 1)/12 - (0.5 if self.config.dataForm.monthOfYear == DataFormType.INTEGER else 0)]
                        elif self.config.dataForm.monthOfYear == DataFormType.VECTOR:
                            if blank:
                                monthGen = lambda d: [0 for x in range(12)]
                            else:
                                monthGen = lambda d: self._getCategoricalVector(d.month - 1, max=12)
                        
                        ## ending month of quarter
                        retvector += monthGen(_edgarformatd(report.period) if not blank else None)

                        ## filing date
                        ## include bit about how many days are in month? 28, 29, 30, 31
                        if self.config.dataForm.dayOfMonth in [DataFormType.INTEGER, DataFormType.NATURAL]:
                            if blank:
                                dayGen = lambda d: [0]
                            else:
                                dayGen = lambda d: [(d.day - 1)/monthrange(d.year, d.month)[1] - (0.5 if self.config.dataForm.dayOfMonth == DataFormType.INTEGER else 0)]
                        elif self.config.dataForm.dayOfMonth == DataFormType.VECTOR:
                            if blank:
                                dayGen = lambda d: [0 for x in range(31)]
                            else:
                                dayGen = lambda d: self._getCategoricalVector(d.day - 1, max=31)
                        filingDate = _edgarformatd(report.filed) if not blank else None
                        retvector += dayGen(filingDate)
                        retvector += monthGen(filingDate)
                    if logstuff: print('intermiediateretvector',len(retvector))

                    ## add values of each tag within the config (tiered) scope
                    for k in tags:
                        if k not in tags: continue
                        if blank: 
                            retvector.extend([0,0]) ## for filling out the overall vector if date range resulted in less than max reports
                        else:
                            try:
                                retvector.extend([
                                    1,              ## is value present in report
                                    shortc(report['nums'][k], 0)   ## actual value
                                ])
                            except KeyError:
                                retvector.extend([0, 0])
                    
                    if logstuff: print('finalretvec',len(retvector), blank)
                    
                    return retvector
                ## done createReportVector

                vectorAsList = [[],[]]
                try:
                    reportNotFiledYetForCurrentPeriod = [1 if _isoformatd(stockDataSet[-1]).month - _edgarformatd(financialDataSet[-1].period).month > 3 else 0]
                except IndexError:
                    reportNotFiledYetForCurrentPeriod = [0]

                reportVector = []
                # first index = report presence flag
                for m in range(maxQuarters(len(stockDataSet)) - len(financialDataSet)):
                    reportVector += [0] + createReportVector(blank=True)

                for r in financialDataSet:
                    reportVector += [1] + createReportVector(r)

                if logstuff: 
                    print('maxq', maxQuarters(len(stockDataSet)))
                    print('fdset', len(financialDataSet))
                    print('reportvec',len(reportVector))

                vectorAsList[0] = reportNotFiledYetForCurrentPeriod
                vectorAsList[1] = reportVector

                if collectStats: sm.ktypefinancialstime += time.time() - startt

            ##############################################################################################################################
            # non-daily, single "instances"
            elif k == 'exchange':
                vectorListType = InputVectorDataType.STATIC
                if collectStats: startt = time.time()
                # vectorAsList = self._getCategoricalVector(exchange, lookupList=self.dbm.getExchanges(), topBuffer=3)
                vectorAsList = self._getCategoricalVector(exchange, lookupList=standardExchanges)

                if collectStats: sm.ktypeexchangetime += time.time() - startt
            elif k == 'sector':
                vectorListType = InputVectorDataType.STATIC
                if collectStats: startt = time.time()
                vectorAsList = self._getCategoricalVector(sector, lookupList=self.dbm.getSectors(), topBuffer=3)

                if collectStats: sm.ktypesectortime += time.time() - startt
            elif k == 'companyAge':
                vectorListType = InputVectorDataType.STATIC
                if collectStats: startt = time.time()
                if foundedDate:
                    year = month = day = None
                    fdatesplit = foundedDate.split('-')
                    if len(fdatesplit) > 0:
                        year = int(fdatesplit[0])
                        if len(fdatesplit) > 1:
                            month = int(fdatesplit[1])
                            if len(fdatesplit) > 2:
                                day = int(fdatesplit[2])
                    
                    if not month: month = 1
                    if not day: day = 1

                    companyagedays = (_isoformatd(stockDataSet[-1]) - date(int(year), month, day)).days

                    ## normalize
                    companyagedays /= 40 * 365

                    vectorAsList = [
                        companyagedays,
                        1 if month else 0,  ## do we know month
                        1 if day else 0     ## do we know day
                    ]
                else:
                    vectorAsList = [0,0,0]

                if collectStats: sm.ktypecompanyagetime += time.time() - startt
            elif k == 'ipoAge':
                vectorListType = InputVectorDataType.STATIC
                if collectStats: startt = time.time()
                vectorAsList = [((_isoformatd(stockDataSet[-1]) - date.fromisoformat(ipoDate)).days) / 40 / 365] if ipoDate else [0]

                if collectStats: sm.ktypeipoagetime += time.time() - startt
            elif k == 'etf':
                vectorListType = InputVectorDataType.STATIC
                if collectStats: startt = time.time()
                vectorAsList = [1] if etfFlag else [0]

                if collectStats: sm.ktypeetftime += time.time() - startt

            ##############################################################################################################################

            # spcl.addl(compositeKey, vectorAsList)
            # inpVecStats.addStatFromList(compositeKey, vectorAsList)

            if collectStats: startt = time.time()
            if self.config.network.recurrent:
                if k == 'financials':
                    inpVecStats[InputVectorDataType.STATIC][compositeKey + InputVectorDataType.STATIC.value] = len(vectorAsList[0])
                    inpVecStats[InputVectorDataType.SEMISERIES][compositeKey] = len(vectorAsList[1])
                    staticarr += vectorAsList[0]
                    semiseriesarr += vectorAsList[1]
                else:
                    inpVecStats[vectorListType][compositeKey] = len(vectorAsList)
                    if vectorListType == InputVectorDataType.STATIC:
                        staticarr += vectorAsList
                    elif vectorListType == InputVectorDataType.SEMISERIES:
                        semiseriesarr += vectorAsList
                    else:
                        seriesmatrix.append(vectorAsList)
            else:
                inpVecStats[compositeKey] = len(vectorAsList)
                retarr += vectorAsList
            if collectStats: sm.inpVecStatsretarrtime += time.time() - startt
        
        # if not loggedonce and not getSplitStat:
        #     loggedonce = True
        #     print('Input vector split:')
        #     print(spcl.toString())
        if self.config.network.recurrent:
            steplength = []
            for r in seriesmatrix:
                steplength.append(int(len(r) / len(stockDataSet)))
            
            ## flatten matrix in column order
            # startt = time.time()
            for c in range(len(stockDataSet)):
                for r in range(len(seriesmatrix)):
                    stepl = steplength[r]
                    val = seriesmatrix[r][c*stepl:(c+1)*stepl]
                    seriesarr.extend(val)
            # print('loop time', time.time() - startt)
            # startt = time.time()
            # seriesarr = [seriesmatrix[r][c*steplength[r]:(c+1)*steplength[r]] for c in range(len(stockDataSet)) for r in range(len(seriesmatrix))]
            # seriesarr = flatten(seriesarr)
            # print('comp + flatten time', time.time() - startt) ## 3x slower than loop + extend method


        if getSplitStat:
            return recdotdict(inpVecStats)
        else:
            if collectStats: startt = time.time()
            if logstuff: print(len(retarr),len(financialDataSet))

            if self.config.network.recurrent:
                ret = (numpy.array(staticarr), numpy.array(semiseriesarr), numpy.array(seriesarr))
            else:
                ret = numpy.array(retarr)
            if collectStats: sm.finalnparraytime += time.time() - startt
            return ret


    def _buildMockData(self, precedingRange=1):
        mocklistdt = '1970-01-01'
        mockipodt = '1999-01-01'
        mockstockDataSet = [recdotdict({
            'period_date': mockipodt,
            'open': 5,
            'high': 5,
            'low': 5,
            'close': 5,
            'volume': 5
        }) for x in range(precedingRange)]
        mockvix = recdotdict({
            mockipodt: {
                'date': mockipodt,
                'open': 7,
                'high': 7,
                'low': 7,
                'close': 7
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
            mockipodt: 6 for x in range(precedingRange)
        })
        mockindicators = recdotdict({
            k: [9 for x in range(precedingRange)] for k in self.getIndicators()
        })
        mockindicators[IndicatorType.DIS] = [(3,3) for x in range(precedingRange)]
        mockindicators[IndicatorType.BB] = [(4,4,4) for x in range(precedingRange)]
        mockindicators[IndicatorType.ST] = [(2,SuperTrendDirection.UP) for x in range(precedingRange)]

        return { 'stockDataSet': mockstockDataSet, 'vixData': mockvix, 'financialDataSet': mockfinancialDataSet, 'googleInterests': mockginterests, 'foundedDate': mocklistdt, 'ipoDate': mockipodt, 'indicators': mockindicators }


    def getStats(self, precedingRange=1):
        if not self.stats or precedingRange != 1:
            self.stats = self.build(**self._buildMockData(precedingRange), sector='Technology', exchange='NYSE', stockSplits=[], etfFlag=False, getSplitStat=True)
        return self.stats

    def getInputSize(self, precedingRange=1):
        if self.config.network.recurrent:
            stats = self.getStats(precedingRange)
            return [sum(stats[t].values()) for t in InputVectorDataType]
        else:
            return sum(self.getStats(precedingRange).values())

    # def build(self, *args):
    #     return self._inputVector(*args)


if __name__ == '__main__':
    ivf: InputVectorFactory = InputVectorFactory()

    print(ivf.getInputSize())
    # print(ivf.getInputSize(200))
    print(ivf.getStats())

    _,_,seriesSize = ivf.getInputSize()
    precrange = 3
    _,_,seriesArr = ivf.build(**ivf._buildMockData(precrange), sector='Technology', exchange='NYSE', stockSplits=[], etfFlag=False)
    print(numpy.reshape(seriesArr, (precrange, seriesSize)))
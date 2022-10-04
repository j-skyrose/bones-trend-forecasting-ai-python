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

from globalConfig import config as gconfig
from constants.enums import DataFormType, FeatureExtraType, InputVectorDataType
from constants.values import interestColumn, standardExchanges
from utils.support import Singleton, flatten, recdotdict, _isoformatd, shortc, _edgarformatd
from utils.other import maxQuarters
from structures.stockDataHandler import StockDataHandler
from managers.statsManager import StatsManager

# from managers.databaseManager import DatabaseManager
# dbm: DatabaseManager = DatabaseManager()
sm: StatsManager = StatsManager()
collectStats = True

loggedonce = False

class InputVectorFactory(Singleton):

    def __init__(self, config=gconfig):
        self.config = config
        self.stats = None

        from managers.databaseManager import DatabaseManager
        self.dbm: DatabaseManager = DatabaseManager()

        pass

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

# class speclog:
#     def __init__(self) -> None:
#         self.runningtotal = 0
#         self.logstring = ''
#     def addl(self, string, list):
#         try: t = len(list)*len(list[0]) 
#         except TypeError: t = len(list)
#         except IndexError: t = 0
#         self.runningtotal += t
#         return string + ' ' + str(t) + ' ' + str(self.runningtotal) + '\n'
#     def toString(self):
#         return self.logstring

    def build(self, stockDataSet, vixData, financialDataSet, googleInterests, foundedDate, ipoDate, sector, exchange, stockSplits, etfFlag, getSplitStat=False):
        global loggedonce
        if gconfig.network.recurrent:
            inpVecStats = {e: {} for e in InputVectorDataType}
        else:
            inpVecStats = {}
        # spcl = speclog()

        retarr = []
        seriesarr = []
        semiseriesarr = []
        staticarr = []
        ## loop thru all feature keys recursively and incrementally add them to the end of the vector
        for kprime, vprime in self.config.feature.items():
            for k,v in vprime.items() if 'enabled' not in vprime.keys() else [(kprime, vprime)]:
                if not v['enabled']: continue
                extraType = v['extraType']
                vectorAsList = []
                compositeKey = k ## concat kprime with k for features that consist of multiple sub-features

                logstuff = False
                # if k in [
                #     'dayOfWeek',
                #     'dayOfMonth',
                #     'monthOfYear',
                #     'googleInterests',
                #     # 'financials',
                #     'exchange',
                #     'sector',
                #     'companyAge',
                #     'ipoAge'
                # ]: continue

                # if extraType in [
                #     'key',
                #     'vixkey',
                # ]: continue

                ##############################################################################################################################
                ## daily "instances"
                if extraType == FeatureExtraType.KEY:
                    vectorListType = InputVectorDataType.SERIES
                    if collectStats: startt = time.time()
                    vectorAsList = [d[k] for d in stockDataSet]
                    compositeKey = kprime + k
                    if collectStats: sm.extraTypekeytime += time.time() - startt

                elif extraType == FeatureExtraType.VIXKEY:
                    vectorListType = InputVectorDataType.SERIES
                    if collectStats: startt = time.time()
                    vectorAsList = [(vixData[d.date])[k] for d in stockDataSet]
                    compositeKey = kprime + k
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
                    vectorAsList = [googleInterests.at[_isoformatd(d), interestColumn] for d in stockDataSet]
                    if collectStats: sm.ktypegoogleintereststime += time.time() - startt
                
                elif k == 'stockSplits':
                    vectorListType = InputVectorDataType.SERIES
                    if collectStats: startt = time.time()
                    # stockSplitDates = [s.date for s in stockSplits]
                    ## zero center split ratio: 1:2 -> 2, 3:1 -> -3
                    stockSplitDict = {s.date: ((max(s.split_from, s.split_to) / min(s.split_from, s.split_to)) - 1) * (1 if s.split_from < s.split_to else -1) for s in stockSplits}
                    # vectorAsList = [*([1,stockSplitDict[d.date]] if d.date in stockSplitDict.keys() else [0,0]) for d in stockDataSet]
                    # vectorAsList = [1 if d.date in stockSplitDict.keys() else 0 for d in stockDataSet]
                    # vectorAsList += [stockSplitDict[d.date] if d.date in stockSplitDict.keys() else 0 for d in stockDataSet]
                    vectorAsList = [(1 if splitBooleanAndNotRatio else stockSplitDict[d.date]) if d.date in stockSplitDict.keys() else 0 for d in stockDataSet for splitBooleanAndNotRatio in [True, False]]
                    if collectStats: sm.ktypestocksplitstime += time.time() - startt


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
                        year, *datesplit = foundedDate.split('-')
                        if len(datesplit) > 0:
                            month = int(datesplit[0])
                            if type(datesplit) is list and len(datesplit) > 1:
                                day = int(datesplit[1])
                        
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
                if gconfig.network.recurrent:
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
                            seriesarr += vectorAsList
                else:
                    inpVecStats[compositeKey] = len(vectorAsList)
                    retarr += vectorAsList
                if collectStats: sm.inpVecStatsretarrtime += time.time() - startt
        
        # if not loggedonce and not getSplitStat:
        #     loggedonce = True
        #     print('Input vector split:')
        #     print(spcl.toString())

        if getSplitStat:
            return recdotdict(inpVecStats)
        else:
            if collectStats: startt = time.time()
            if logstuff: print(len(retarr),len(financialDataSet))

            if gconfig.network.recurrent:
                ret = (numpy.array(staticarr), numpy.array(semiseriesarr), numpy.array(seriesarr))
            else:
                ret = numpy.array(retarr)
            if collectStats: sm.finalnparraytime += time.time() - startt
            return ret



    def getStats(self, precedingRange=1):
        if not self.stats or precedingRange != 1:
            mocklistdt = '1970-01-01'
            mockipodt = '1999-01-01'
            mockstockDataSet = [recdotdict({
                'date': mockipodt,
                'open': 0,
                'high': 0,
                'low': 0,
                'close': 0,
                'volume': 0
            }) for x in range(precedingRange)]
            mockvix = recdotdict({
                mockipodt: {
                    'date': mockipodt,
                    'open': 0,
                    'high': 0,
                    'low': 0,
                    'close': 0
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
            mockginterests = {} ## todo

            self.stats = self.build(mockstockDataSet, mockvix, mockfinancialDataSet, mockginterests, mocklistdt, mockipodt, 'Technology', 'NYSE', [], False, getSplitStat=True)

        return self.stats

    def getInputSize(self, precedingRange=1):
        if gconfig.network.recurrent:
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
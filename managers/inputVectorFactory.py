import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import numpy, re
from calendar import monthrange
from datetime import date, datetime, timedelta

from globalConfig import config as gconfig
from constants.enums import DataFormType
from constants.values import interestColumn
from utils.support import Singleton, flatten, recdotdict, _isoformatd, shortc, _edgarformatd
from utils.other import maxQuarters
from structures.stockDataHandler import StockDataHandler

# from managers.databaseManager import DatabaseManager
# dbm: DatabaseManager = DatabaseManager()

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

    def build(self, stockDataSet, vixRef, financialDataSet, googleInterests, foundedDate, ipoDate, sector, exchange, getSplitStat=False):
        global loggedonce
        ivs = {}
        # spcl = speclog()

        retarr = []
        for kprime, vprime in self.config.feature.items():
            for k,v in vprime.items() if 'enabled' not in vprime.keys() else [(kprime, vprime)]:
                if not v['enabled']: continue
                extype = v['extype']
                vlist = []
                fk = k

                ##############################################################################################################################
                ## daily "instances"
                if extype == 'key':
                    vlist = [d[k] for d in stockDataSet]
                    fk = kprime + k

                elif extype == 'vixkey':
                    vlist = [(vixRef.data[d.date])[k] for d in stockDataSet]
                    fk = kprime + k

                elif k == 'dayOfWeek':
                    # vlist = [_isoformatd(d).weekday()/6 - 0.5 for d in stockDataSet]
                    if self.config.dataForm.dayOfWeek in [DataFormType.INTEGER, DataFormType.NATURAL]:
                        itemGen = lambda d: _isoformatd(d).weekday()/6 - (0.5 if self.config.dataForm.dayOfWeek == DataFormType.INTEGER else 0)
                    elif self.config.dataForm.dayOfWeek == DataFormType.VECTOR:
                        itemGen = lambda d: self._getCategoricalVector(_isoformatd(d).weekday(), max=5)
                    vlist = [itemGen(d) for d in stockDataSet]

                elif k == 'dayOfMonth':
                    # vlist = [(dt.day - 1)/monthrange(dt.year, dt.month)[1] - 0.5 for dt in [_isoformatd(d) for d in stockDataSet]]
                    ## include bit about how many days are in month? 28, 29, 30, 31
                    if self.config.dataForm.dayOfMonth in [DataFormType.INTEGER, DataFormType.NATURAL]:
                        itemGen = lambda d: (d.day - 1)/monthrange(d.year, d.month)[1] - (0.5 if self.config.dataForm.dayOfMonth == DataFormType.INTEGER else 0)
                    elif self.config.dataForm.dayOfMonth == DataFormType.VECTOR:
                        itemGen = lambda d: self._getCategoricalVector(d.day - 1, max=31)
                    vlist = [itemGen(dt) for dt in [_isoformatd(d) for d in stockDataSet]]

                elif k == 'monthOfYear':
                    # vlist = [(_isoformatd(d).month - 1)/12 - 0.5 for d in stockDataSet]
                    if self.config.dataForm.monthOfYear in [DataFormType.INTEGER, DataFormType.NATURAL]:
                        itemGen = lambda d: (_isoformatd(d).month - 1)/12 - (0.5 if self.config.dataForm.monthOfYear == DataFormType.INTEGER else 0)
                    elif self.config.dataForm.monthOfYear == DataFormType.VECTOR:
                        itemGen = lambda d: self._getCategoricalVector(_isoformatd(d).month - 1, max=12)
                    vlist = [itemGen(d) for d in stockDataSet]

                elif k == 'googleInterests':
                    vlist = [googleInterests.at[_isoformatd(d), interestColumn] for d in stockDataSet]

                ##############################################################################################################################
                ## non-daily, semi-repeated "instances"
                elif k == 'financials':
                    tags = flatten([v['tierTags'][t] for t in range(v['maxTierIndex'])]) ## combine all tags from tiers upto and including v['maxTierIndex']

                    def createReportVector(report={}, blank=False):
                        retvector = []

                        ## quarter
                        if blank:
                            retvector += [0,0,0,0]
                        else:
                            retvector += self._getCategoricalVector(report.quarter, 4)
                        
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
                        filingDate = _edgarformatd(report.filing) if not blank else None
                        retvector += dayGen(filingDate)
                        retvector += monthGen(filingDate)

                        ## add values of each tag within the config (tiered) scope
                        for k in tags:
                            if k not in tags: continue
                            if blank: retvector.extend([0,0]) ## for filling out the overall vector if date range resulted in less than max reports
                            try:
                                retvector.extend([
                                    1,              ## is value present in report
                                    shortc(report['values'][k], 0)   ## actual value
                                ])
                            except KeyError:
                                retvector.extend([0, 0])
                        
                        return retvector
                    ## done createReportVector

                    reportNotFiledYetForCurrentPeriod = [1 if _isoformatd(stockDataSet[-1]).month - _edgarformatd(financialDataSet[-1].period).month > 3 else 0]
                    reportPresenceVector = [1 for x in range(len(financialDataSet))]
                    reportVector = []
                    for m in range(maxQuarters(len(stockDataSet)) - len(reportPresenceVector)):
                        reportPresenceVector = [0] + reportPresenceVector
                        reportVector += createReportVector(blank=True)

                    for r in financialDataSet:
                        reportVector += createReportVector(r)

                    vlist = reportNotFiledYetForCurrentPeriod + reportPresenceVector + reportVector

                ##############################################################################################################################
                ## non-daily, single "instances"
                elif k == 'exchange':
                    vlist = self._getCategoricalVector(exchange, lookupList=self.dbm.getExchanges(), topBuffer=3)
                elif k == 'sector':
                    vlist = self._getCategoricalVector(sector, lookupList=self.dbm.getSectors(), topBuffer=3)
                elif k == 'companyAge':
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

                        vlist = [
                            companyagedays,
                            1 if month else 0,  ## do we know month
                            1 if day else 0     ## do we know day
                        ]
                    else:
                        vlist = [0,0,0]
                elif k == 'ipoAge':
                    vlist = [((_isoformatd(stockDataSet[-1]) - date.fromisoformat(ipoDate)).days) / 40 / 365] if ipoDate else [0]

                ##############################################################################################################################

                # spcl.addl(fk, vlist)
                # ivs.addStatFromList(fk, vlist)
                vlist = flatten(vlist)
                ivs[fk] = len(vlist)
                retarr += vlist
        
        # if not loggedonce and not getSplitStat:
        #     loggedonce = True
        #     print('Input vector split:')
        #     print(spcl.toString())

        if getSplitStat:
            return recdotdict(ivs)
        else:
            return numpy.array(retarr)


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
                'data': {
                    mockipodt: {
                        'date': mockipodt,
                        'open': 0,
                        'high': 0,
                        'low': 0,
                        'close': 0
                    } for x in range(precedingRange)
                }
            })
            mockfinancialDataSet = [recdotdict({
                'period': '20120112',
                'filing': '20090606',
                'quarter': 2,
                'values': {
                    'Assets': 9000,
                    'Liabilities': 250,
                    'StockholdersEquity': 8750
                }
            })]
            mockginterests = {} ## todo

            self.stats = self.build(mockstockDataSet, mockvix, mockfinancialDataSet, mockginterests, mocklistdt, mockipodt, 'Technology', 'NYSE', getSplitStat=True)

        return self.stats

    def getInputSize(self, precedingRange=1):
        return sum(self.getStats(precedingRange).values())

    # def build(self, *args):
    #     return self._inputVector(*args)


if __name__ == '__main__':
    ivf: InputVectorFactory = InputVectorFactory()

    print(ivf.getInputSize())
    # print(ivf.getInputSize(200))
    print(ivf.getStats())
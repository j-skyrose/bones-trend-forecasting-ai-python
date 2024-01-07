import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from enum import Enum
from typing import Any, Dict, List

from constants.enums import ChangeType, SeriesType, AccuracyType
from managers._generatedDatabaseExtras.databaseRowObjects import networksSnakeCaseTableColumns, networksCamelCaseTableColumns, networkTrainingConfigSnakeCaseTableColumns, networkTrainingConfigCamelCaseTableColumns
from structures.normalizationColumnObj import NormalizationColumnObj
from structures.normalizationDataHandler import NormalizationDataHandler
from utils.dbSupport import convertToCamelCase, isNormalizationColumn
from utils.support import recdotdict

class NetworkStats:

    def __init__(self, id, precedingRange=None, **kwargs):
        ''' kwargs: network_training_config columns '''
        self.id = id
        self.precedingRange = precedingRange
        self.normalizationData: NormalizationDataHandler = NormalizationDataHandler()
        self.overallAccuracy = 0
        self.negativeAccuracy = 0
        self.positiveAccuracy = 0
        self.epochs = 0

        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def importFrom(cls, statsObj):
        c = cls(statsObj.id)
        ## adding to attribute in-place results in it applying to the class statically (i.e. all instances have all the columns)
        ## probably due to __setattr__ override        
        normalizationData = NormalizationDataHandler() 
        for k,v in statsObj.items():
            if k in ['factory', 'config']: continue
            if isNormalizationColumn(k):
                # c.normalizationData.append(NormalizationColumnObj(k, v))
                normalizationData.append(k, v)
            else:
                k = convertToCamelCase(k)
                if not hasattr(c, k) or (hasattr(c, k) and not c[k]):
                    setattr(c, k, v)
        setattr(c, 'normalizationData', normalizationData)
        return c


    ## makes the object subscriptable
    def __getitem__(self, key):
        try:
            if isNormalizationColumn(key):
                return self.normalizationData.getValue(key)
            return getattr(self, key)
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, name: str, value: Any) -> None:
        enumType = None
        if name == 'seriesType':
            enumType = SeriesType
        elif name == 'accuracyType':
            enumType = AccuracyType
        elif name == 'changeType':
            enumType = ChangeType     

        if enumType:
            value = enumType[value.upper()] if type(value) is str else value

        super(NetworkStats, self).__setattr__(name, value)

    def _getTableData(self, sccolumns, cccolumns, camelCase, dbInsertReady) -> Dict:
        retdict = recdotdict({})
        for sc, cc in zip(sccolumns, cccolumns):
            if isNormalizationColumn(sc):
                val = self.normalizationData.getValue(sc, orNone=True)
            elif hasattr(self, cc):
                val = self[cc].name if dbInsertReady and issubclass(self[cc].__class__, Enum) else self[cc]
            else:
                val = None
            retdict[cc if camelCase else sc] = val
        return retdict

    def getNetworksTableData(self, camelCase=False, dbInsertReady=False):
        return self._getTableData(networksSnakeCaseTableColumns, networksCamelCaseTableColumns, camelCase, dbInsertReady)
    
    def getNetworkTrainingConfigTableData(self, camelCase=False, dbInsertReady=False):
        return self._getTableData(networkTrainingConfigSnakeCaseTableColumns, networkTrainingConfigCamelCaseTableColumns, camelCase, dbInsertReady)

if __name__ == '__main__':
    ## testing
    n = NetworkStats(2, 2, seriesType=SeriesType.DAILY)
    print(n.id, n.seriesType)
    n.setMax('test', 3)
    print(n.testMax)
    n.accuracyType = 'COMBINED'
    print(n.accuracyType)

    print(n.getNormalizationInfo())

    n = NetworkStats.importFrom(recdotdict({'id': 2, 'overallAccuracy': 5}))
    print(n.overallAccuracy, n.accuracyType)
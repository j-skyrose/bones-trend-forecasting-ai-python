import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import copy
from typing import List

from constants.enums import NormalizationGroupings
from managers._generatedDatabaseExtras.databaseRowObjects import networkTrainingConfigSnakeCaseTableColumns
from structures.normalizationColumnObj import NormalizationColumnObj
from utils.dbSupport import isNormalizationColumn

class NormalizationDataHandler:
    
    def __init__(self, ncolumnObjs=[]):
        ## TODO: ncolumnObjs must be deep copied otherwise it can accumulate values across multiple initializations of this class for some reason, especially during network stats initialization via .fromSave for all networks in neural network manager
        self._normalizationData: List[NormalizationColumnObj] = copy.deepcopy(ncolumnObjs)
        # self._normalizationData: List[NormalizationColumnObj] = ncolumnObjs
    
    def __iter__(self):
        return self._normalizationData.__iter__()
    
    def __bool__(self):
        return len(self._normalizationData) > 0
    
    def __len__(self):
        return len(self._normalizationData)
    
    def append(self, k, v=None):
        if type(k) == NormalizationColumnObj:
            self._normalizationData.append(k)
        else:
            self._normalizationData.append(NormalizationColumnObj(k, v))

    @classmethod
    def buildFromDBColumns(cls, columns=None):
        nameExtractor = lambda x: x.name
        if not columns:
            columns = networkTrainingConfigSnakeCaseTableColumns
            nameExtractor = lambda x: x
        data = [NormalizationColumnObj(nameExtractor(c)) for c in columns if isNormalizationColumn(nameExtractor(c))]
        return cls(data)

    def get(self, key, orNone=False):
        if type(key) == NormalizationGroupings:
            results = [nc for nc in self._normalizationData if nc.normalizationGrouping == key]
            if len(results) == 0:
                if orNone: return []
                raise ValueError(f'Nothing found for key {key}')
            return NormalizationDataHandler(results)
        else:
            results = [nc for nc in self._normalizationData if (
                nc.camelCaseRawColumnName == key or nc.columnArgName == key or nc.columnName == key or nc.rawColumnName == key
            )]
            if len(results) == 0:
                if orNone: return None
                raise ValueError(f'Nothing found for key {key}')
            if len(results) > 1: raise OverflowError(f'Too many results for key {key}')
            return results[0]

    def getValue(self, key, orNone=False):
        cobj = self.get(key, orNone)
        if cobj: return cobj.value
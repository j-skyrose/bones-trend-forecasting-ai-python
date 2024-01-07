import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from utils.dbSupport import convertToCamelCase, parseNormalizationColumn

class NormalizationColumnObj:
    
    def __init__(self, rawColumnName: str, value=None):
        self.value = value

        ## e.g. highest_historical_volume_weighted_average
        self.rawColumnName = rawColumnName.lower()
        ## e.g. highestHistoricalVolumeWeightedAverage
        self.camelCaseRawColumnName = convertToCamelCase(self.rawColumnName)
        ## e.g. volume_weighted_average
        self.normalizationGrouping, self.columnName = parseNormalizationColumn(rawColumnName)
        ## e.g. volumeWeightedAverage
        self.columnArgName = convertToCamelCase(self.columnName)

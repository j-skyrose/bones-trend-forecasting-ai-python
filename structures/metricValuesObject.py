import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.enums import MetricType
from utils.support import shortc

def mapMetricNameToType(name):
    name = name.lower()
    if 'accuracy' in name:
        return MetricType.ACCURACY
    elif 'true' in name or 'false' in name:
        return MetricType.SUM
    else:
        return name
    # else:
    #     raise ValueError(f'Unaccounted for metric type: {name}')

class MetricValuesObject:

    def __init__(self, name, current, last, metricType=None) -> None:
        self.name = name
        self.current = current
        self.last = last
        self.type = shortc(metricType, mapMetricNameToType(name))

import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from typing import Dict, List, Tuple

## 7 day block of Google interest data
class WeekBlock:
    # data: Dict[str,float] = {}

    def __init__(self, kvPairs:List[Tuple[str,float]]) -> None:
        self.data: Dict[str,float] = {}
        kvPairs.sort(key=lambda a: a[0])
        for k,v in kvPairs:
            self.data[k] = v

    def __eq__(self, __o: object) -> bool:
        if type(__o) != WeekBlock: return False
        for s,o in zip(self.data.keys(), __o.data.keys()):
            if s != o: return False
        return True

    def multiplyBy(self, mult):
        for k in self.data.keys():
            self.data[k] *= mult
    def sum(self):
        return sum([v for v in self.data.values()])
    def isPartial(self):
        return len(self.data) != 7
    def getStartDate(self):
        return list(self.data.keys())[0]
    def getEndDate(self):
        return list(self.data.keys())[-1]

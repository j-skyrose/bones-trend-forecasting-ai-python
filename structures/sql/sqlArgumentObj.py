import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.enums import OperatorDict

class SQLArgumentObj:
    def __init__(self, value, modifier: OperatorDict=OperatorDict.EQUAL):
        self.value = value
        self.modifier = modifier

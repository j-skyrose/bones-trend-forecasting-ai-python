import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from constants.enums import Direction

class SQLOrderObj:
    def __init__(self, column, modifier: Direction=Direction.ASCENDING):
        self.column = column
        self.modifier = modifier

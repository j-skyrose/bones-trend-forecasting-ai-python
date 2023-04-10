import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

class SkipsObj:
    def __init__(self, stocks=False, financials=False, splits=False, technicalIndicators=False, googleInterests=False, instances=False, sets=False):
        self.stocks = stocks
        self.financials = financials
        self.splits = splits
        self.technicalIndicators = technicalIndicators
        self.googleInterests = googleInterests
        self.instances = instances
        self.sets = sets
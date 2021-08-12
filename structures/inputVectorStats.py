import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"


### defunct, absorbed in inputVectorFactory

class InputVectorStats:
    def __init__(self):
        self.stats = {}
    
    def addStat(self, label, value):
        self.stats[label] = value

    def addStatFromList(self, label, lst):
        self.addStat(label, len(lst))
    
    def getKey(self, index):
        return list(self.stats.keys())[index]

    def getStat(self, key=None, index=None):
        if key:
            return self.stats[key]
        elif index:
            return self.stats[self.getKey(index)]

    def getLength(self):
        return len(self.stats.keys())
    
    def getTotalLength(self):
        return sum(self.stats.values())

    def toString(self):
        rstr = ''
        for k in self.stats.keys():
            rstr += k + ': ' + str(self.stats[k]) + '\n'
        return rstr[:-1]
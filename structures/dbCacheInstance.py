import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from utils.support import compressObj, urlSafeHash

class DBCacheInstance:
    def __init__(self, fileTag, queryStatement, cacheStamp, value):
        self.filetag = fileTag
        self.queryStatement = queryStatement
        self.stampZip = compressObj(cacheStamp)
        self.value = value

    def test(self, q, st):
        return q == self.queryStatement and self.stampZip == compressObj(st)

    def getUniqueHash(self):
        return urlSafeHash(self.queryStatement)


if __name__ == '__main__':
    d = DBCacheInstance('2', 'select *', 
    # 'davefredtreydedddddddddd36346ydgsg3f23', 
    {'dave':'d'},
    2)
    print(d.queryHash)
    print(d.test({'dave':'d'}))

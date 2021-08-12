import zlib, base64, hashlib, json

def urlsafeHash(string):
    return base64.urlsafe_b64encode(hashlib.md5(string.encode()).digest()).decode('utf-8').replace('=','')

def compressValidationObj(vobj):
    return zlib.compress((vobj if type(vobj) == str else json.dumps(vobj)).encode())

class DBCacheInstance:
    def __init__(self, filetag, queryStatement, validationObj, returnValue):
        self.filetag = filetag
        self.queryStatement = queryStatement
        self.validationZip = compressValidationObj(validationObj)
        self.returnValue = returnValue

    def test(self, q, v):
        return q == self.queryStatement and self.validationZip == compressValidationObj(v)

    def getQueryHash(self):
        return urlsafeHash(self.queryStatement)


if __name__ == '__main__':
    d = DBCacheInstance('2', 'select *', 
    # 'davefredtreydedddddddddd36346ydgsg3f23', 
    {'dave':'d'},
    2)
    print(d.queryHash)
    print(d.test({'dave':'d'}))

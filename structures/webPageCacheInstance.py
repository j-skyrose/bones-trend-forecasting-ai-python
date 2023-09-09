import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from utils.support import compressObj, urlSafeHash

class WebPageCacheInstance:
    def __init__(self, url, content, cacheStamp, params={}, postData=None, headers={}):
        self.fileTag = self.__convertURL(url)
        self.params = compressObj(params)
        self.postData = compressObj(postData)
        self.headers = compressObj(headers)
        self.cacheStamp = self.__convertCacheStamp(cacheStamp)
        self.value = content

    def __convertURL(self, url):
        return url.split('://')[-1].replace('www.', '').replace('.com', '').split('.')[0].replace('/','-')
    
    def __convertCacheStamp(self, stamp):
        return urlSafeHash(str(stamp))

    def test(self, url, cacheStamp, **kwargs):
        return self.fileTag == self.__convertURL(url) and self.cacheStamp == self.__convertCacheStamp(cacheStamp) and all([getattr(self, k) == compressObj(v) for k,v in kwargs.items()])
        # print(self.__convertURL(url))
        # res = self.fileTag == self.__convertURL(url) 
        # print(res)
        # print([getattr(self, k) for k,v in kwargs.items()])
        # print([compressObj(v) for k,v in kwargs.items()])
        # res2 = all([getattr(self, k) == compressObj(v) for k,v in kwargs.items()])
        # print(res2)
        # print(self.__convertCacheStamp(cacheStamp), self.cacheStamp)
        # res3 = self.__convertCacheStamp(cacheStamp) == self.cacheStamp
        # print(res3)
        # return res and res2 and res3

    def getUniqueHash(self):
        return urlSafeHash(str(self.params + self.postData + self.headers))

if __name__ == '__main__':
    d = WebPageCacheInstance(
        'https://www.marketwatch.com/tools/screener/short-interest',
        'test',
        1,
        params={'test': 3},
        postData={'arg1': 'argggg'},
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
    )
    print(d.test('https://www.marketwatch.com/tools/screener/short-interest', params={'none':4}))
    print(d.getUniqueHash())

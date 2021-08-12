
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm
from managers.databaseManager import DatabaseManager
from utils.support import DotDict, Singleton, recdotdict


edgarPath = os.path.join(path, 'data/financial_dumps/edgar')
edgarFiles = ['pre', 'sub', 'tag', 'num']
dbm: DatabaseManager = DatabaseManager()


class _QuarterObj(DotDict):
    def __init__(self, id, dirpath):
        self.id = id
        self.path = dirpath

        for ef in edgarFiles:
            with open(os.path.join(self.path, ef + '.txt'), 'r') as f:
                self[ef] = []

                keys = [k.replace('\n','') for k in f.readline().split('\t')]
                for line in f:
                    obj = recdotdict({})
                    vals = [v.replace('\n','') for v in line.split('\t')]
                    for i in range(len(keys)):
                        obj[keys[i]] = vals[i]

                    self[ef].append(obj)


# class FinancialsLoader(Singleton):
#     def __init__(self):
def loadEDGARFinancialDumps():
    loadedQuarters = dbm.getLoadedQuarters()
    # print('Already loaded quarters', loadedQuarters)

    c= 0
    for root, dirs, files in os.walk(edgarPath):
        if len(dirs) > 0:
            dirs.reverse()
            # for d in tqdm.tqdm(dirs, desc='Loading quarters'):
            for d in dirs:
                if d not in loadedQuarters:
                    print('Loading', d)
                    # availableQuarters[d] = _QuarterObj(d, os.path.join(edgarPath, d))
                    qobj = _QuarterObj(d, os.path.join(edgarPath, d))
                    dbm.insertEDGARFinancialDump(d, qobj.sub, qobj.tag, qobj.num)
                else:
                    print('Skipping',d)
                
                # if c > 1:
                #     break
                # c += 1    





if __name__ == '__main__':
    # fl = FinancialsLoader()
    # print(fl.availableQuarters.keys())
    # print(fl.availableQuarters['2009q3'].data.keys())
    # print(len(fl.availableQuarters['2009q3'].data['sub']))

    ## check uniqueness of asdh from sub file
    # adshs = []
    # for q in tqdm.tqdm(fl.availableQuarters.values(), desc='Searching adshs'):
    #     found = False
    #     for r in q.sub:
    #         if r.adsh not in adshs:
    #             adshs.append(r.adsh)
    #         else:
    #             print('duplicate adsh found:', r.adsh)
    #             found=True
    #             break
    #     if found:
    #         break
    # print(len(adshs), 'unique adshs found')

    loadEDGARFinancialDumps()
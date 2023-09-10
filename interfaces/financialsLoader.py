
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, requests, zipfile, io

from managers.configManager import StaticConfigManager
from managers.databaseManager import DatabaseManager
from utils.support import DotDict, Singleton, recdotdict


edgarPath = StaticConfigManager().get('edgardumps', required=True)
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

    print('Inserting new quarters')
    dbm.dbc.execute(f'''INSERT OR IGNORE INTO vwtb_edgar_quarters 
        SELECT exchange, symbol, period, CASE fp WHEN 'Q1' THEN 1 WHEN 'Q2' THEN 2 WHEN 'Q3' then 3 WHEN 'FY' then 4 END AS quarter, filed 
        FROM {dbm.getTableString("dump_edgar_sub")} s JOIN {dbm.getTableString("dump_edgar_num")} n ON s.adsh = n.adsh 
        WHERE exchange IS NOT NULL AND symbol IS NOT NULL AND n.version LIKE \'%us-gaap%\'
        AND exchange||symbol NOT IN ('NYSEARD', 'NYSECIB', 'NASDAQFWP', 'NASDAQGLPG', 'NYSEPTR', 'NYSESSL', 'NYSETLK', 'NYSEYPF')''' ## tickers that have extremely partial reports, or ones that are causing problems for normalization filters
    )

    print('Migrating num data to vwtb')
    ## may need some optimizing, could take almost 2 hours to run
    dbm.dbc.execute(f'''INSERT OR IGNORE INTO vwtb_edgar_financial_nums
        SELECT DISTINCT s.exchange, s.symbol, n.tag, n.ddate, n.qtrs, n.uom, n.value, n.duplicate 
            FROM {dbm.getTableString("dump_edgar_num")} n JOIN {dbm.getTableString("dump_edgar_sub")} s, {dbm.getTableString("dump_edgar_tag")} t ON n.adsh = s.adsh AND n.tag = t.tag AND n.version = t.version
            WHERE n.coreg='' AND t.custom = 0 AND t.abstract = 0 AND t.version LIKE \'%us-gaap%\''''
    )




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

    ## download quarters
    # url = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/2021q1.zip"
    url = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/"
    loadedQuarters = dbm.getLoadedQuarters()
    lastloadedyear, lastloadedquarter = loadedQuarters[-1].split('q')

    while True:
    # while False:
        lastloadedyear = int(lastloadedyear)
        lastloadedquarter = int(lastloadedquarter)
        lastloadedquarter += 1
        if lastloadedquarter > 4:
            lastloadedquarter = 1
            lastloadedyear += 1
        lastloadedyear = str(lastloadedyear)
        lastloadedquarter = str(lastloadedquarter)

        yearquarter = 'q'.join([lastloadedyear, lastloadedquarter])

        # if yearquarter == '2021q1' or yearquarter == '2021q2': break

        print('Requesting', yearquarter)
        response = requests.get(url + yearquarter + '.zip')
        if response.status_code != 200:
            print(response.status_code)
            print(response.json)
            print(yearquarter, 'not available (yet)')
            break

        with zipfile.ZipFile(io.BytesIO(response.content)) as thezip:
            thezip.extractall(os.path.join(edgarPath, yearquarter))
        
        print('Downloaded', yearquarter)


    loadEDGARFinancialDumps()
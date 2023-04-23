
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import optparse, tqdm

from globalConfig import config as gconfig
from constants.enums import IndicatorType, OutputClass
from constants.values import indicatorsKey
from managers.databaseManager import DatabaseManager
from managers.dataManager import DataManager
from managers.inputVectorFactory import InputVectorFactory
from structures.dataPointInstance import DataPointInstance
from structures.skipsObj import SkipsObj
from utils.other import getInstancesByClass
from utils.vectorSimilarity import euclideanSimilarity

dbm: DatabaseManager = DatabaseManager()

'''
Determines the Euclidean similarity between input vectors for all negative instances of each ticker, writes resulting (sum) to DB
Input vector must only contain positive numbers, negatives may slightly change how accurate the similarity calculation is
Can be interuptted and resumed, and should be able to handle new stock data addition to existing calculated values
'''
def determineSimilarities():
    
    ## remove unnecessary/redundant features
    ## only keep EMA200, since all are based on stock data, which is already included...and to not break stuff by having no indicators
    cf = gconfig
    for ind in IndicatorType.getActuals():
        cf.feature[indicatorsKey][ind].enabled = False
    cf.feature[indicatorsKey][IndicatorType.EMA200].enabled = True

    cf.feature.dayOfWeek.enabled = False
    cf.feature.dayOfMonth.enabled = False
    cf.feature.monthOfYear.enabled = False

    props = {
        'precedingRange': 60,
        'followingRange': 10,
        'threshold': 0.05
    }

    dm: DataManager = DataManager.forAnalysis(
        skips=SkipsObj(sets=True),
        saveSkips=True,
        skipAllDataInitialization=True,
        **props,
        maxPageSize=1,
        # exchanges=['NASDAQ'],

        inputVectorFactory=InputVectorFactory(cf),
        verbose=0.5
    )

    ci: DataPointInstance
    ri: DataPointInstance
    keyboardinterrupted = False
    similarities = []
    similaritiesSum = []
    maxpage = dm.getSymbolListPageCount()
    for i in tqdm.tqdm(range(330, maxpage), desc='Chunks'):
        ## only iterating one SDH at a time
        dm.initializeAllDataForPage(i+1)
        ticker = list(dm.stockDataHandlers.keys())[0]
        neginstances = getInstancesByClass(dm.stockDataInstances.values())[1]
        
        ## prepare get/insert arguments
        def prepareArgs(indx=None):
            return {
                'exchange': ticker.exchange,
                'symbol': ticker.symbol,
                'dtype': dm.seriesType,
                'dt': dm.stockDataHandlers[ticker].data[indx].date if indx is not None else None,
                'vclass': OutputClass.NEGATIVE,
                **props
            }

        similaritiesSum = []
        ## load already calculated sums from DB
        dbsums = dbm.getVectorSimilarity(**prepareArgs())
        for dbsum in dbsums:
            similaritiesSum.append(dbsum.value)
        if len(dbsums) > 0: print(f'Loaded {len(dbsums)} values')

        ## skip if everything already calculated
        startindex = len(dbsums)
        if startindex == len(neginstances): continue

        try:
            ## loop calculating by column, then adding to running row sums for each
            for cindx in tqdm.tqdm(range(startindex, len(neginstances)), desc='Columns', leave=False):
                ci = neginstances[cindx]
                vector = ci.getInputVector()[2] ## series portion

                ## calculate similarites for each row
                similarities = []
                for rindx in tqdm.tqdm(range(0, cindx), desc='Rows', leave=False):
                    ri = neginstances[rindx]
                    similarities.append(euclideanSimilarity(vector, ri.getInputVector()[2]))

                ## add similarites to running sums
                for sindx in range(len(similarities)):
                    similaritiesSum[sindx] += similarities[sindx]
                
                ## sum similarities for current index
                similaritiesSum.append(sum(similarities))
        except KeyboardInterrupt:
            keyboardinterrupted = True

        dbm.startBatch()
        for vsindx in range(len(similaritiesSum)):
            dbm.insertVectorSimilarity(*prepareArgs(vsindx).values(), similaritiesSum[vsindx], upsert=True)
        dbm.commitBatch()

        if keyboardinterrupted: break


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-f', '--function',
        action='store', dest='function', default=None
        )
    options, args = parser.parse_args()

    if options.function:
        kwargs = {}
        for arg in args:
            key, val = arg.split('=')
            kwargs[key] = val.lower() == 'true' if val.lower() in ['true', 'false'] else val
        locals()[options.function](**kwargs)
    else:
        determineSimilarities()
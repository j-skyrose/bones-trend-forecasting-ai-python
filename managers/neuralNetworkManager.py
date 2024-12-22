import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"


import tqdm, time, dill
from managers.databaseManager import DatabaseManager
from utils.support import Singleton, recdotdict
from constants.enums import SeriesType

from structures.neuralNetworkInstance import NeuralNetworkInstance

dbm: DatabaseManager = DatabaseManager()

class NeuralNetworkManager(Singleton):
    savePath = os.path.join(path, 'data/network_saves')

    def __init__(self):
        self.networks = {}
        for x in dbm.getNetworks():
            factoryConfig = dill.loads(x.config)
            metrics = dbm.getNetworkMetrics_basic(x.id)
            self.networks[str(x.id)] = NeuralNetworkInstance.fromSave(x.factory, factoryConfig, os.path.join(self.savePath, str(x.id)), x, metrics)

    def createNetworkInstance(self, *args, **kwargs):
        id = str(int(time.time()))
        r = self.networks[id] = NeuralNetworkInstance.new(id, *args, **kwargs)
        return r

    def save(self, k, dryrun=False):
        key = k if type(k) == str else k.properties.id
        n = self.networks[key]
        nSavePath = os.path.join(self.savePath, key)
        if not dryrun: dbm.startBatch()
        dbm.pushNeuralNetwork(n, dryrun=dryrun)
        if not dryrun:
            n.save(nSavePath)
            dbm.commitBatch()
        else:
            print(f'"saving" to {nSavePath}')
        print('done saving network', key)

    def get(self, arg) -> NeuralNetworkInstance:
        if type(arg) == NeuralNetworkInstance: return arg
        return self.networks[str(arg)]

    def getAllNetworksBy(self, changeThreshold=0.0, precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, epochs=0):
        retnns = []
        for nn in self.networks.values():
            nnst = nn.stats
            if nnst.changeThreshold >= changeThreshold and \
                nnst.precedingRange >= precedingRange and \
                nnst.followingRange >= followingRange and \
                nnst.seriesType == seriesType and \
                nnst.epochs >= epochs:
                    retnns.append(nn)
        return retnns


if __name__ == '__main__':
    nm = NeuralNetworkManager()
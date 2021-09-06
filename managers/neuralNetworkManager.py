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
from constants.enums import AccuracyType, SeriesType

from structures.neuralNetworkInstance import NeuralNetworkInstance

dbm: DatabaseManager = DatabaseManager()

class NeuralNetworkManager(Singleton):
    savePath = os.path.join(path, 'data/network_saves')

    def __init__(self):
        self.networks = {
            str(x.id): NeuralNetworkInstance.fromSave(x.factory, dill.loads(x.config), os.path.join(self.savePath, str(x.id)), x)
                for x in dbm.getNetworks()
        }

    def createNetworkInstance(self, *args, **kwargs):
        print('Creating NN', args, kwargs)
        id = str(int(time.time()))
        r = self.networks[id] = NeuralNetworkInstance.new(id, *args, **kwargs)
        return r

    def save(self, k):
        key = k if type(k) == str else k.stats.id
        n = self.networks[key]
        n.save(os.path.join(self.savePath, key))
        dbm.pushNeuralNetwork(n)
        print('done saving network', key)

    def get(self, id) -> NeuralNetworkInstance:
        return self.networks[str(id)]

    def getAllNetworksBy(self, accuracyType=AccuracyType.NEGATIVE, negativeAccuracy=0.0, changeThreshold=0.0, precedingRange=0, followingRange=0, seriesType=SeriesType.DAILY, epochs=0):
        retnns = []
        for nn in self.networks.values():
            nnst = nn.stats
            if nnst.accuracyType == accuracyType and \
                nnst.negativeAccuracy >= negativeAccuracy and \
                nnst.changeThreshold >= changeThreshold and \
                nnst.precedingRange >= precedingRange and \
                nnst.followingRange >= followingRange and \
                nnst.seriesType == seriesType and \
                nnst.epochs >= epochs:
                    retnns.append(nn)
        return retnns


if __name__ == '__main__':
    nm = NeuralNetworkManager()
    # print(AccuracyType.COMBINED)
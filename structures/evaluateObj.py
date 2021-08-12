import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tensorflow as tf
from utils.support import recdotdict
from constants.enums import AccuracyType, LossAccuracy

class EvaluateObj:
    # LossAccuracy.LOSS = None
    # LossAccuracy.ACCURACY = None
    
    def __init__(self, loss, accuracy):
        self[LossAccuracy.LOSS] = loss
        self[LossAccuracy.ACCURACY] = accuracy

    def __setitem__(self, key: LossAccuracy, value):
        return setattr(self, key.name, value)

    def __getitem__(self, key: LossAccuracy):
        return getattr(self, key.name)
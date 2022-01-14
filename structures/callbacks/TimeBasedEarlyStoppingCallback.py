import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time
from tensorflow import keras

class TimeBasedEarlyStopping(keras.callbacks.Callback):
    def __init__(self, stopTime=None, timeDuration=None):
        super(TimeBasedEarlyStopping, self).__init__()
        self.stopTime = stopTime
        self.timeDuration = timeDuration
    
    def on_train_begin(self, logs=None):
        self.startTime = time.time()

    def on_epoch_end(self, epoch, logs=None):
        if (self.stopTime and time.time() > self.stopTime) or (self.timeDuration and time.time() - self.startTime > self.timeDuration):
            self.stopped_epoch = epoch
            self.model.stop_training = True
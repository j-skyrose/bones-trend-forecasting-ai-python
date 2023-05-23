import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from tensorflow import keras

class DeviationFromBasedEarlyStopping(keras.callbacks.Callback):
    def __init__(self, minEpochs=1, validation_accuracy=None):
        super(DeviationFromBasedEarlyStopping, self).__init__()
        self.minEpochs = minEpochs

        if validation_accuracy is not None:
            self.key = 'val_accuracy'
            self.base = validation_accuracy

    def on_epoch_end(self, epoch, logs=None):
        if epoch < self.minEpochs - 1: return

        if not logs:
            print('No logs given, breaking...')
            self.model.stop_training = True
        
        if hasattr(self, 'key') and logs[self.key] != self.base:
            self.model.stop_training = True

import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import gc
from keras.callbacks import EarlyStopping

class EarlyStoppingWithCustomValidation(EarlyStopping):
    def __init__(self, network=None, batchSize=None, custom_validation_data=None, custom_validation_data_values=[], **kwargs):
        super().__init__(**kwargs)
        self.network = network
        self.batchSize = batchSize
        if type(custom_validation_data) is list:
            self.custom_validation_data = custom_validation_data
            if type(custom_validation_data_values) is not list:
                raise ValueError('Data was list but values was not')
            self.custom_validation_data_values = custom_validation_data_values
        else:
            self.custom_validation_data = [custom_validation_data]
            self.custom_validation_data_values = [custom_validation_data_values]

    def on_epoch_end(self, epoch, logs=None):
        gc.collect()

        # print('epoch end in',logs)
        if self.custom_validation_data:
            if not logs:
                logs = {}
            else:
                logs['val_loss'] = 0
                logs['val_accuracy'] = 0
            for d, dval in zip(self.custom_validation_data, self.custom_validation_data_values):
                results = self.network.model.evaluate(d[0], d[1], batch_size=self.batchSize, verbose=0)
                # print(results)
                logs['val_loss'] += results[0] * dval
                logs['val_accuracy'] += results[1] * dval

        # print('epoch end out',logs)
        if self.verbose > 0: print(self.monitor, ':', logs.get(self.monitor))

        super().on_epoch_end(epoch, logs)
        if self.wait >= self.patience and epoch > 0 and self.restore_best_weights and self.best_weights is not None and self.verbose > 0: ## from super.on_epoch_end
            print('Best', self.monitor, ':', self.best)
        

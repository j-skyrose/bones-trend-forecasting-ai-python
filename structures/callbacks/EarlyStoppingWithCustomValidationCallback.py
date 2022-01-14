import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import gc, numpy
from keras.callbacks import EarlyStopping

class EarlyStoppingWithCustomValidation(EarlyStopping):
    def __init__(self, network=None, batchSize=None, custom_validation_data=None, custom_validation_data_values=[], override_stops_on_value=None, **kwargs):
        super().__init__(**kwargs)
        self.network = network
        self.batchSize = batchSize
        self.override_stops_on_value = override_stops_on_value
        self.override_running_increment = 0
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
        if self.verbose > 0: print('Custom', self.monitor, ':', logs.get(self.monitor))

        ## prevent early stopping on no improvement if value is stuck on the same as what got configured
        ## hack: default to 0 and increase by smallest possible value so latest epoch is considered best until a non-expected value appears
        if self.override_stops_on_value:
            if logs.get(self.monitor) == self.override_stops_on_value:
                self.override_running_increment += numpy.nextafter(numpy.float32(0), numpy.float32(1))
                logs[self.monitor] = 0 + self.override_running_increment

        super().on_epoch_end(epoch, logs)
        if self.wait >= self.patience and epoch > 0 and self.restore_best_weights and self.best_weights is not None and self.verbose > 0: ## from super.on_epoch_end
            print('Best custom', self.monitor, ':', self.best)
        

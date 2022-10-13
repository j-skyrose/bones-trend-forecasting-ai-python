import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from utils.support import Singleton
import configparser
configFilepath = os.path.join(path, 'config.ini')

class ConfigManager(Singleton):
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(configFilepath)

    def get(self, arg1, arg2=None):
        if (arg2):
            return self.config[arg1][arg2]
        else:
            return self.config['DEFAULT'][arg1]

    def set(self, arg1, arg2, arg3=None):
        if arg3 is not None:
            self.config[arg1][arg2] = str(arg3)
        else:
            self.config['DEFAULT'][arg1] = str(arg2)

    def save(self):
        with open(configFilepath, 'w') as cf:
            self.config.write(cf)

# ci = ConfigManager()

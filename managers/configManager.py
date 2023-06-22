import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import warnings
from configobj import ConfigObj

from constants.values import defaultConfigFileSection
from utils.support import Singleton, shortc

## see below for actual classes
class _ConfigManager():
    def __init__(self, configFilepath=None, static: bool=True):
        if not configFilepath: raise ValueError('Missing config path')

        self.filepath = configFilepath
        self.static = static
        self.config = ConfigObj(self.filepath, create_empty=(not self.static))

    def get(self, arg1, arg2=None, defaultValue=None):
        try:
            if (arg2):
                return self.config[arg1][arg2]
            else:
                return self.config[defaultConfigFileSection][arg1]
        except KeyError as e:
            if arg2 is not None and arg1 == e.args[0]:
                if self.static: ## savedState auto-creates anything missing
                    raise KeyError(f'\'{arg1}\' section is missing from the config')
            
            autoval = shortc(defaultValue, "")
            warnings.warn(f'\'{shortc(arg2, arg1)}\' config value missing from \'{arg1 if arg2 else defaultConfigFileSection}\' section, defaulting to \'{autoval}\'')
            self.set(
                arg1 if arg2 else defaultConfigFileSection,
                shortc(arg2, arg1),
                autoval
            )
            return autoval

    def set(self, arg1, arg2, arg3=None):
        if arg3 is not None:
            self.config[arg1][arg2] = str(arg3)
        else:
            self.config[defaultConfigFileSection][arg1] = str(arg2)

    def save(self):
        self.config.write()


class StaticConfigManager(Singleton, _ConfigManager):
    filepath = os.path.join(path, 'sp2StaticConfig.ini')

    def __init__(self):
        _ConfigManager.__init__(self, self.filepath)

class SavedStateManager(Singleton, _ConfigManager):
    filepath = os.path.join(path, 'sp2SavedState.ini')

    def __init__(self):
        _ConfigManager.__init__(self, self.filepath, static=False)


if __name__ == '__main__':
    c = StaticConfigManager()
    p = c.get('primarydatabase')
    print(p)
    print(os.path.exists(p))
    p = c.get('dumpdatabase')
    print(p)
    print(os.path.exists(p))

    c2 = SavedStateManager()
    print(c2.get('fmp', 'remaining'))
    # c2.set('fmp', 'remaining', 10)
    c2.save()

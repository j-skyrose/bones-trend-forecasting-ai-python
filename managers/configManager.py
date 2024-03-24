import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import validate
from configobj import ConfigObj

from constants.enums import LimitType
from constants.values import defaultConfigFileSection
from utils.support import Singleton, shortc

## see below for actual classes
class _ConfigManager():
    def __init__(self, configFilepath=None, configSpec=None, static: bool=True):
        if not configFilepath: raise ValueError('Missing config path')

        self.filepath = configFilepath
        self.static = static
        self.config = ConfigObj(self.filepath, configspec=configSpec, create_empty=(not self.static))

        initialComment = self.config.initial_comment

        validated = self.config.validate(validate.Validator(), preserve_errors=True, copy=True)
        if validated != True:
            raise ValueError(validated)
        
        ## values can be cleared/overridden by validation
        self.config.initial_comment = initialComment

    def get(self, arg1, arg2=None, required=False, default=None):
        section = arg1 if arg2 else defaultConfigFileSection
        key = arg2 if arg2 else arg1
        try: 
            self.config[section][key]
        except KeyError as e:
            if not required:
                self.set(section, key, default)
            else: raise e
        
        retval = self.config[section][key]

        if required and type(retval) is str and len(retval) == 0:
            raise ValueError(f'{section}:{key} is required but has no value')

        if key == 'limitType': retval = LimitType[retval.upper()]
        return retval

    def set(self, arg1, arg2, arg3=None):
        if arg3 is not None:
            try: self.config[arg1]
            except KeyError: self.config[arg1] = {}
            self.config[arg1][arg2] = str(arg3)
        else:
            self.config[defaultConfigFileSection][arg1] = str(arg2)

    def save(self):
        self.config.write()

staticConfigSpec = f'''
[DEFAULT]
__many__ = string(default=None)
[__many__]
__many__ = string(default=None)
url = string(default=None)
apikey = string(default=None)
priority = integer(1, default=100)
limit = integer(default=-1)
limittype = option({",".join([stype.name for stype in LimitType])}, default={LimitType.NONE.name})
'''
class StaticConfigManager(Singleton, _ConfigManager):
    filepath = os.path.join(path, 'sp2StaticConfig.ini')

    def __init__(self):
        _ConfigManager.__init__(self, self.filepath, staticConfigSpec.split('\n'))

savedStateSpec = '''
[__many__]
remaining = integer(default=-1)
updated = string(default="1970-01-01")
[update]
lastupdateddate = string(default="1970-01-01")
laststockindex = integer(default=-1)
totaladded = integer(0, default=0)
updated = string(default="1970-01-01")
[google]
lastprocessedrowid = integer(default=-1)
'''
class SavedStateManager(Singleton, _ConfigManager):
    filepath = os.path.join(path, 'sp2SavedState.ini')

    def __init__(self):
        _ConfigManager.__init__(self, self.filepath, savedStateSpec.split('\n'), static=False)


if __name__ == '__main__':
    c = StaticConfigManager()
    p = c.get('propertiesdatabase')
    print(p)
    print(os.path.exists(p))
    p = c.get('dumpdatabase')
    print(p)
    print(os.path.exists(p))

    c2 = SavedStateManager()
    print(c2.get('fmp', 'remaining'))
    # c2.set('fmp', 'remaining', 10)
    c2.save()

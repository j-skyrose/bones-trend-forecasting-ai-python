import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from managers.base.persistentManagerBase import PersistentManagerBase
from structures.optionsDataServer import odServerPort, odServerAuthKey, OptionsDataManagerProxy
from utils.support import shortcdict

class _PersistentOptionsDataManager(PersistentManagerBase):

    def __init__(self, **kwargs):
        super().__init__(OptionsDataManagerProxy, odServerPort, odServerAuthKey, 
                         serverFilepath='structures/optionsDataServer.py',
                         usingServerCallbacksAndKWArgs=[
                             ('addSymbols', {
                                'symbolList': shortcdict(kwargs, 'symbolList', [])
                             })
                            ],
                         **kwargs)

def PersistentOptionsDataManagerFactory(**kwargs) -> OptionsDataManagerProxy:
    ## ensures code completion displays the methods of the proxy class itself
    return _PersistentOptionsDataManager(**kwargs)

if __name__ == '__main__':
    odm = PersistentOptionsDataManagerFactory()
    odh = odm.get('AMAT')
    print(odm.getDay('AMAT', 'O:AMAT230915C00167500', '2023-08-22'))
    print(odm.getDay('AMAT', 'O:AMAT230915C00167500', '2023-08-22'))
    print(odm.getDay('AMAT', 'O:AMAT230915C00172500', '2023-08-31'))
    
    odh = odm.get('ABNB')
    print(odm.getDay('ABNB', 'O:ABNB231020C00125000', '2023-10-08'))
    print(odm.getDay('ABNB', 'O:ABNB231020C00125000', '2023-10-11'))
        

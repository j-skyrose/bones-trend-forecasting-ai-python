import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

from managers.base.persistentManagerBase import PersistentManagerBase
from structures.databaseConnectionServer import DatabaseConnectionManagerProxy, dbcServerPort, dbcServerAuthKey

class _PersistentDatabaseConnectionManager(PersistentManagerBase):

    def __init__(self, **kwargs):
        super().__init__(DatabaseConnectionManagerProxy, dbcServerPort, dbcServerAuthKey, 
                         serverFilepath='structures/databaseConnectionServer.py',
                         usingServerCallbacksAndKWArgs=[],
                         **kwargs
                        )

def PersistentDatabaseConnectionManagerFactory(**kwargs) -> DatabaseConnectionManagerProxy:
    ## ensures code completion displays the methods of the proxy class itself
    return _PersistentDatabaseConnectionManager(**kwargs)

if __name__ == '__main__':
    dbc = PersistentDatabaseConnectionManagerFactory()

    print(dbc.execute('SELECT * FROM networks'))

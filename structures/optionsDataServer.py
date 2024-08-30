import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import atexit, optparse
from multiprocessing.managers import SyncManager

from constants.enums import OptionType
from managers.optionsDataManager import OptionsDataManager
from utils.support import repackKWArgs

odServerPort = 5069
odServerAuthKey = b'OptionsProxy01'

## global persistent
odm: OptionsDataManager = None
initializeManager = lambda: OptionsDataManager()

class OptionsDataManagerProxy(object):
    def __init__(self, runningOnMainProcess=False, pid='', originatingScript='') -> None:
        self.pid = pid
        self.originatingScript = originatingScript
        self.runningOnMainProcess = runningOnMainProcess
        ## if running on Main process, meaning not as a proxy-server then there will be no caching that can be re-used by later processes/runs
        if self.runningOnMainProcess:
            global odm
            odm = initializeManager()

    def addSymbols(self, symbolList):
        if not self.runningOnMainProcess: print(f"Adding symbols: {symbolList[:15]}{'...' if len(symbolList)>15 else ''}")
        global odm
        odm.addSymbols(symbolList)

    def get(self, symbol):
        '''gets OptionDataHandler for given symbol\n\nNOTE: should not generally be used as changes to it will not be saved server-side'''
        if not self.runningOnMainProcess: print(f'Getting handler for {symbol}')
        global odm
        return odm._get(symbol)

    def getTickers(self, symbol, expiringWeekDate=None, strike=None, strikeAbove=None, strikeBelow=None, contractType:OptionType=None):
        '''gets all options tickers for the given symbol that meet the expiry week and strike parameters'''
        kwargs = repackKWArgs(locals())
        if not self.runningOnMainProcess: print(f'Getting tickers for {symbol} with kwargs {kwargs}')
        global odm
        return odm.getTickers(**kwargs)
    
    def getDay(self, symbol, ticker, dt):
        '''gets prices object at given date'''
        if not self.runningOnMainProcess: print(f'Getting day {dt} for {symbol}:{ticker}')
        global odm
        return odm.data[symbol].getDay(ticker, dt)
    
    def getOptionsContractKeys(self, symbol, asStrings=True):
        if not self.runningOnMainProcess: print(f'Getting options contract keys for {symbol}')
        global odm
        return odm.data[symbol].getOptionsContractKeys(asStrings)

class OptionsDataServer(object):
    def __init__(self, port):
        self.port = port
        atexit.register(self.close)
        global odm
        odm = initializeManager()

    def close(self):
        global odm
        print('Shutting down')
        print(f'Had {len(odm.data.keys())} tickers')
        print(f'Had total {sum([odh.getInitializedTickerCount() for odh in odm.data.values()])} options tickers with data')

    # Run the server
    def run(self):
        class myManager(SyncManager): pass  
        myManager.register('OptionsDataManagerProxy', OptionsDataManagerProxy)
        mgr = myManager(address=('', self.port), authkey=odServerAuthKey)
        server = mgr.get_server()
        server.serve_forever()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-s', '--server-start',
        action='store_true', dest='serverstart'
    )
    options, args = parser.parse_args()

    if options.serverstart:
        print('Starting Options Data server')
        odmsrv = OptionsDataServer(odServerPort)
        print('Press <ctrl>-c to stop')
        odmsrv.run()
    else:
        pass      

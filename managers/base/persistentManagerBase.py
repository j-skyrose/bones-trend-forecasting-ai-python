import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import time, subprocess
from multiprocessing.managers import BaseManager

class PersistentManagerBase(object):

    def __init__(self, proxyClass, serverPort, serverAuthKey, serverFilepath=None, usingServerCallbacksAndKWArgs=[], runServer=True, **initkwargs):
        proxyName = proxyClass.__name__
        if runServer:
            class myManager(BaseManager): pass
            myManager.register(proxyName)
            self.manager = myManager(address=('localhost', serverPort), authkey=serverAuthKey)

            ## connect to server; starting it if it is not currently running
            serverStarted = False
            connectedToServer = False
            for retry in range(3):
                try:
                    self.manager.connect()
                    connectedToServer = True
                except ConnectionRefusedError:
                    if not serverStarted:
                        ## with VSCode python debugger, this new process window will still close despite the /k parameter
                        subprocess.Popen(
                            ['start', 'cmd', '/k', 'python', os.path.join(path, serverFilepath), '--server-start'],
                            shell=True,
                            creationflags=subprocess.CREATE_NEW_CONSOLE
                        )
                        serverStarted = True
                    time.sleep(1)

        if not runServer or not connectedToServer: 
            print(f'WARNING: Unable to start/find server, defaulting to same-process {proxyName}')
            self.proxy = proxyClass(runningOnMainProcess=True, **initkwargs)
        else:
            self.proxy = getattr(self.manager, proxyName)(
                pid=os.getpid(),
                originatingScript=sys.argv[0]
            )
            for funcName, kwargs in usingServerCallbacksAndKWArgs:
                getattr(self.proxy, funcName)(**kwargs)

    def __new__(cls, **initkwargs):
        ## make singleton
        it = cls.__dict__.get("__it__")
        if it is None:
            cls.__it__ = it = object.__new__(cls)
            it.__init__(**initkwargs)
        return it.proxy

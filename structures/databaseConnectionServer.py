import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import atexit, optparse, threading
from collections.abc import Iterable
from datetime import datetime
from multiprocessing.managers import SyncManager
from queue import Queue
from sqlite3 import Connection, Cursor
from typing import Dict, Tuple

from constants.values import backslash
from utils.dbSupport import expandSQLStatementArguments, generateCompleteDBConnectionAndCursor
from utils.support import condenseWhitespace, shortc

dbcServerPort = 5070
dbcServerAuthKey = b'DBCProxy01'

_single = '_single'
_many = '_many'
_begin = '_begin'
_commit = '_commit'
_rollback = '_rollback'
_end = '_end'
def _queueTupleFactory(etype=None, sql='', params=(), q=None, pid='', originatingScript='') -> Tuple[str, str, Iterable, Queue, str, str]:
    return (etype, sql, params, q, pid, originatingScript)

## global persistent
initializeDBCs = lambda: generateCompleteDBConnectionAndCursor()
dbconnect: Connection = None
dbcursor: Cursor = None
executionQueue: Queue = None
queryCache: Dict = None

class DatabaseConnectionManagerProxy(object):
    def __init__(self, runningOnMainProcess=False, pid='', originatingScript='') -> None:
        self.pid = pid
        self.originatingScript = originatingScript
        self.batchQueue: Queue = None
        self.lastrowid = None
        self.runningOnMainProcess = runningOnMainProcess
        ## if running on Main process, meaning not as a proxy-server then all methods should perform without any threading/queues as there should be no chance of race conditions with other running processes
        if self.runningOnMainProcess:
            global dbconnect, dbcursor
            dbconnect, dbcursor = initializeDBCs()

    def _queueTupleFactory(self, etype=None, sql='', params=(), q=None):
        return _queueTupleFactory(etype, sql, params, q, self.pid, self.originatingScript)
    
    def getLastRowId(self):
        if not self.runningOnMainProcess:
            return self.lastrowid
        else:
            global dbcursor
            return dbcursor.lastrowid

    def clearQueryCache(self):
        global queryCache
        queryCache.clear()

    def startBatch(self):
        self.commit()
        self.batchQueue = Queue()
        executionQueue.put(self._queueTupleFactory(_begin, 'BEGIN', q=self.batchQueue))
    def commitBatch(self):
        if not self.batchQueue:
            print('WARNING: no batch was started')
        else:
            self.batchQueue.put(self._queueTupleFactory(_commit, 'COMMIT'))
            self.batchQueue = None
    def rollbackBatch(self):
        if not self.batchQueue:
            print('WARNING: no batch was started')
        else:
            self.batchQueue.put(self._queueTupleFactory(_rollback, 'ROLLBACK'))
            self.batchQueue = None

    def commit(self):
        if not self.runningOnMainProcess:
            if self.batchQueue:
                self.commitBatch()
            else:
                global executionQueue
                executionQueue.put(self._queueTupleFactory(_commit, 'COMMIT'))
        else:
            global dbconnect
            dbconnect.commit()

    def execute(self, sql: str, parameters = (), /):
        isSelect = sql.lower().startswith('select')
        if not self.runningOnMainProcess:
            global queryCache
            ckey = condenseWhitespace(expandSQLStatementArguments(sql.lower(), parameters))
            try:
                return queryCache[ckey]
            except KeyError:
                # print(f'Queuing: {sql[:100]}{"..." if len(sql) > 100 else ""}')
                global executionQueue
                putq = shortc(self.batchQueue, executionQueue)
                resq = Queue()
                putq.put(self._queueTupleFactory(_single, sql, parameters, resq))
                ret = []
                while True:
                    rec = resq.get()
                    if type(rec) == tuple and rec[0] == _end:
                        self.lastrowid = rec[1]
                        break
                    elif isinstance(rec, Exception): raise rec
                    ret.extend(rec)
                
                ## caching only if SELECT of a non-dump or -computed DB table
                if isSelect and all(not ckey.endswith(suffix) and not f'{suffix} ' in ckey for suffix in ['_c', '_d']):
                    queryCache[ckey] = ret
                else:
                    ## was some insert/update, invalidating previous caches
                    self.clearQueryCache()
                return ret
        else:
            global dbcursor
            resc = dbcursor.execute(sql, parameters)
            self.lastrowid = dbcursor.lastrowid
            if isSelect:
                return resc.fetchall()

    def executemany(self, sql: str, parameters: Iterable, /):
        if not self.runningOnMainProcess: 
            # print(f'Queuing many: {sql[:100]}{"..." if len(sql) > 100 else ""}')
            global executionQueue
            putq = shortc(self.batchQueue, executionQueue)
            resq = Queue()
            putq.put(self._queueTupleFactory(_many, sql, parameters, resq))

            rec = resq.get()
            if type(rec) == tuple and rec[0] == _end:
                self.lastrowid = rec[1]
            elif isinstance(rec, Exception): raise rec
        else:
            global dbcursor
            dbcursor.executemany(sql, parameters)
            self.lastrowid = dbcursor.lastrowid

class DatabaseConnectionServer(object):
    def __init__(self, port):
        atexit.register(self.close)
        self.port = port

        global dbconnect, dbcursor, executionQueue, queryCache
        dbconnect, dbcursor = initializeDBCs()
        executionQueue = Queue()
        queryCache = {}

    def close(self):
        print('Shutting down')

    def _serveExecutionQueue(self):
        global dbconnect, dbcursor, executionQueue, queryCache
        batchQueue: Queue = None
        while True:
            etype, sql, parameters, q, pid, originatingScript = shortc(batchQueue, executionQueue).get()
            def llog(msg):
                print(f"{datetime.now().isoformat(timespec='seconds')} | {originatingScript.split(backslash)[-1].split('/')[-1].replace('.py','')}({pid}) | {msg}")

            if etype == _begin:
                llog('Starting batch')
                batchQueue = q
                dbcursor.execute(sql)
            elif etype == _commit:
                if batchQueue:
                    llog('Committing batch')
                    dbcursor.execute(sql)
                    batchQueue = None
                else:
                    llog('Committing')
                    dbconnect.commit()
            elif etype == _rollback:
                llog('Rolling back batch')
                dbcursor.execute(sql)
                batchQueue = None
            elif etype == _single:
                llog(f'Executing: {sql[:100]}{"..." if len(sql) > 100 else ""}')
                try:
                    dbcursor.execute(sql, parameters)
                    if q:
                        q.put(dbcursor.fetchall())
                        q.put((_end, dbcursor.lastrowid))
                except Exception as e:
                    llog(f'Raising exception {e}')
                    q.put(e)

            elif etype == _many:
                llog(f'Executing many: {sql[:100]}{"..." if len(sql) > 100 else ""}')
                try:
                    dbcursor.executemany(sql, parameters)
                    q.put((_end, dbcursor.lastrowid))
                except Exception as e:
                    llog(f'Raising exception {e}')
                    q.put(e)

                ## was some insert/update, invalidating previous caches
                queryCache.clear()

    # Run the server
    def run(self):
        class myManager(SyncManager): pass  
        myManager.register('DatabaseConnectionManagerProxy', DatabaseConnectionManagerProxy)
        mgr = myManager(address=('', self.port), authkey=dbcServerAuthKey)

        ## start execution queue handler
        qserver = threading.Thread(target=self._serveExecutionQueue)
        qserver.daemon = True
        qserver.start()

        ## start accepting connections
        server = mgr.get_server()
        server.serve_forever()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-s', '--server-start',
        action='store_true', dest='serverstart'
    )
    options, args = parser.parse_args()

    if options.serverstart:
        print(f'Starting Database connection server with PID {os.getpid()}')
        dbcsrv = DatabaseConnectionServer(dbcServerPort)
        print('Press <ctrl>-c to stop')
        dbcsrv.run()
    else:
        pass

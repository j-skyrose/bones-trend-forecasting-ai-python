
interestColumn = 'interest'


apiList = ['polygon', 'fmp', 'alphavantage']

## symbols that are for testing, too high to be usable, or contain weird extreme data spikes
testingSymbols = [('NASDAQ', 'ZAZZT'),('NASDAQ', 'ZBZZT'),('NASDAQ', 'ZCZZT'),('NASDAQ', 'ZJZZT'),('NASDAQ', 'ZWZZT'),('NASDAQ', 'ZXZZT'),('NYSE','NTEST.G'),('BATS','ZTEST')]
extremeSymbols = [('NYSE','BRK.A'),('NASDAQ','AGEN'),('NASDAQ','MTBCP')]
## multiple IPOs, reassignment, old historical data only, etc. Possibly still usable with some review/changes
damagedSymbols = [('NYSE', 'SMI'),('NYSE', 'HIVE'),('NASDAQ', 'BKCH'),('NASDAQ', 'ATAI'),('NYSE', 'INST'),('NYSE', 'S'),('NASDAQ', 'SMRT'),('NYSE', 'NE'),('NASDAQ', 'CPAAU'),('NASDAQ', 'AMCIU'),('NASDAQ', 'EVLMC'),('NASDAQ', 'RILYZ'),('NASDAQ', 'OXLCO'),('NASDAQ', 'AGBAU'),('NASDAQ', 'EVSTC'),('NASDAQ', 'ACT'),('NASDAQ','SIFI'),('NASDAQ','AMCI'),('NASDAQ','IMRN'),('NASDAQ','IMRNW'),('NYSE MKT','HLTH')]

unusableSymbols = testingSymbols + extremeSymbols + damagedSymbols



months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
foundedSynonyms = ['inception', 'founded', 'formed', 'incorporated']


## normalization
stockOffset = 0
vixOffset = 0
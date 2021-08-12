
interestColumn = 'interest'


apiList = ['polygon', 'fmp', 'alphavantage']

## symbols that are for testing, too high to be usable, or contain weird extreme data spikes
testingSymbols = [('NASDAQ', 'ZAZZT'),('NASDAQ', 'ZBZZT'),('NASDAQ', 'ZCZZT'),('NASDAQ', 'ZJZZT'),('NASDAQ', 'ZWZZT'),('NASDAQ', 'ZXZZT'),('NYSE','NTEST.G'),('BATS','ZTEST')]
unusableSymbols = [('NYSE','BRK.A'),('NASDAQ','AGEN'),('NASDAQ','MTBCP')]


months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
foundedSynonyms = ['inception', 'founded', 'formed', 'incorporated']


## normalization
stockOffset = 0
vixOffset = 0

## for backward compatibility only, new ivFactories will not use
interestColumn = 'interest'


apiList = ['polygon', 'fmp', 'alphavantage']
standardExchanges = ['BATS','NASDAQ','NYSE','NYSE ARCA','NYSE MKT', 'TSX', 'NEO'
# 'LSE'
]

## symbols that are for testing, too high to be usable, or contain weird extreme data spikes
testingSymbols = [('NASDAQ', 'ZAZZT'),('NASDAQ', 'ZBZZT'),('NASDAQ', 'ZCZZT'),('NASDAQ', 'ZJZZT'),('NASDAQ', 'ZWZZT'),('NASDAQ', 'ZXZZT'),('NYSE','NTEST.G'),('BATS','ZTEST')]
extremeSymbols = [('NYSE','BRK.A'),('NASDAQ','AGEN'),('NASDAQ','MTBCP')]
## multiple IPOs, reassignment, old historical data only, etc. Possibly still usable with some review/changes
damagedSymbols = [('NYSE', 'SMI'),('NYSE', 'HIVE'),('NASDAQ', 'BKCH'),('NASDAQ', 'ATAI'),('NYSE', 'INST'),('NYSE', 'S'),('NASDAQ', 'SMRT'),('NYSE', 'NE'),('NASDAQ', 'CPAAU'),('NASDAQ', 'AMCIU'),('NASDAQ', 'EVLMC'),('NASDAQ', 'RILYZ'),('NASDAQ', 'OXLCO'),('NASDAQ', 'AGBAU'),('NASDAQ', 'EVSTC'),('NASDAQ', 'ACT'),('NASDAQ','SIFI'),('NASDAQ','AMCI'),('NASDAQ','IMRN'),('NASDAQ','IMRNW'),('NYSE MKT','HLTH'),('NASDAQ','CPAA'),('NYSE','CBO'),('NASDAQ','AMCIW'),('NYSE','CTRA'),('NASDAQ','CPAAW'),('NASDAQ','SAMAU'),('NASDAQ','ROSEU'),('NYSE','LLL'),('NASDAQ','EVGBC'),('NASDAQ','INAQ'),('NASDAQ','ALACU'),('NYSE ARCA','FLAG'),('NYSE','CIVI'),('NYSE','CBL'),('NYSE ARCA','OILU'),('NYSE','HTZ'),('NYSE ARCA','GBUY'),('NASDAQ','BEAT'),('NASDAQ','SG'),('NASDAQ','LFACU'),('NYSE','CTV'),('NASDAQ','SAMA'),('NASDAQ','ROSE'),('NASDAQ','ROSEW'),('NASDAQ','RILYG'),('NYSE','HHS'),('NYSE','HCP'),('NASDAQ','SAMAW')]

unusableSymbols = testingSymbols + extremeSymbols + damagedSymbols



months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
foundedSynonyms = ['inception', 'founded', 'formed', 'incorporated']


## normalization
stockOffset = 0
vixOffset = 0


## No Commission Scotia stocks
tseEquity = ['XSP','VFV','ESG','HXS','XQQ','QQC.F','XIU','HXT','XIC','SITC','SITI','SITU','VEF','XEU','EAAI','EAGB','EARK','EAUT','HBGD','CDZ','DXC','CUD','DXU','CYH','DXR','QQCC','SRIC','SRIU','MWMN','DXET','SRII','CEW','VRE','XIT','XMA','XST','XUT','XHC','CGR','COW','CWW','DXF','DXN','CPD','DXP','CJP','CWO','DXEM','XEC','XCH','XID','XCS']
batsEquity = ['OMFL','OMFS','IEFA','FINX','HERO','PRNT','PSI','WCLD','HLAL','MILN','NACP','PAWZ','IXC','IXP','IAT','VCR','VDC','VDE','VIS','MRGR','FLQM','HSCZ','SIZE','VLUE']
tseBalanced = ['XGRO','FIE','XBAL','VCNS','XCNS','XINC']
batsBalanced = ['AOA','AOM']
tseFixedIncome = ['CHB','CSD','DXO','CBO','DXV','VCB','XCB','SRIB','CLF','HBB','SITB','XQB']
batsFixedIncome = ['TLT']
tseCommodity = ['CGL','CGL.C','HUC','HUN','HUZ','SVR']
tseNoCommissionSymbols = tseEquity + tseBalanced + tseFixedIncome + tseCommodity
batsNoCommissionSymbols = batsEquity + batsBalanced + batsFixedIncome
noCommissionSymbols = tseNoCommissionSymbols + batsNoCommissionSymbols
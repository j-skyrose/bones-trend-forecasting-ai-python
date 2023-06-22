from datetime import date

normalizationColumnPrefix = 'highest'
defaultConfigFileSection = 'DEFAULT'
indicatorsKey = 'indicators'
## for backward compatibility only, new ivFactories will not use
interestColumn = 'interest'


minGoogleDate = date(2004,1,1)

apiList = ['polygon', 'fmp', 'alphavantage']
standardExchanges = ['BATS','NASDAQ','NYSE','NYSE ARCA','NYSE MKT', 'TSX', 'NEO'
# 'LSE'
]
canadaExchanges = ['TSX', 'NEO']
usExchanges = ['BATS','NASDAQ','NYSE','NYSE ARCA','NYSE MKT']

## symbols that are for testing, too high to be usable, or contain weird extreme data spikes
testingSymbols = [
    ('BATS','ZTEST'),('BATS','ZBZX'),
    ('LSE','TE10'),
    ('NASDAQ', 'ZAZZT'),('NASDAQ', 'ZBZZT'),('NASDAQ', 'ZCZZT'),('NASDAQ', 'ZJZZT'),('NASDAQ', 'ZWZZT'),('NASDAQ', 'ZXZZT'),('NASDAQ','ZVZZC'),('NASDAQ','ZXYZ.A'),('NASDAQ', 'ZJZZT'),
    ('NYSE','CTEST'),('NYSE','MTEST'),('NYSE','NTEST'),('NYSE','NTEST.A'),('NYSE','NTEST.B'),('NYSE','NTEST.C'),('NYSE','NTEST.G'),('NYSE','NTEST.H'),('NYSE','NTEST.I'),('NYSE','NTEST.J'),('NYSE','NTEST.K'),('NYSE','NTEST.L'),('NYSE','NTEST.M'),('NYSE','NTEST.N'),('NYSE','NTEST.O'),('NYSE','NTEST.P'),('NYSE','NTEST.Q'),('NYSE','NTEST.Y'),('NYSE','NTEST.Z'),('NYSE','CBO'),('NYSE','CBX'),('NYSE','IPOY'),('NYSE','IPOZ'),
    ('NYSE ARCA','ZZZ'),('NYSE ARCA','PTEST'),('NYSE ARCA','PTEST.W'),('NYSE ARCA','PTEST.X'),('NYSE ARCA','PTEST.Y'),('NYSE ARCA','IGZ'),('NYSE ARCA','ZVV'),
    ('NYSE MKT','ATEST'),('NYSE MKT','ATEST.A'),('NYSE MKT','ATEST.B'),('NYSE MKT','ATEST.C'),('NYSE MKT','ATEST.G'),('NYSE MKT','ATEST.H'),('NYSE MKT','ATEST.L'),
    ('NEO','YYZ.A'),('NEO','YYZ.DB.A'),('NEO','YYZ.M'),('NEO','YYZ.Q'),('NEO','YYZ.T'),('NEO','YYZ.X'),
    ('TSXV','TEST')
]
extremeSymbols = [('NYSE','BRK.A'),('NASDAQ','AGEN'),('NASDAQ','MTBCP')]
## multiple IPOs, reassignment, old historical data only, etc. Possibly still usable with some review/changes
damagedSymbols = [('NYSE', 'SMI'),('NYSE', 'HIVE'),('NASDAQ', 'BKCH'),('NASDAQ', 'ATAI'),('NYSE', 'INST'),('NYSE', 'S'),('NASDAQ', 'SMRT'),('NYSE', 'NE'),('NASDAQ', 'CPAAU'),('NASDAQ', 'AMCIU'),('NASDAQ', 'EVLMC'),('NASDAQ', 'RILYZ'),('NASDAQ', 'OXLCO'),('NASDAQ', 'AGBAU'),('NASDAQ', 'EVSTC'),('NASDAQ', 'ACT'),('NASDAQ','SIFI'),('NASDAQ','AMCI'),('NASDAQ','IMRN'),('NASDAQ','IMRNW'),('NYSE MKT','HLTH'),('NASDAQ','CPAA'),('NYSE','CBO'),('NASDAQ','AMCIW'),('NYSE','CTRA'),('NASDAQ','CPAAW'),('NASDAQ','SAMAU'),('NASDAQ','ROSEU'),('NYSE','LLL'),('NASDAQ','EVGBC'),('NASDAQ','INAQ'),('NASDAQ','ALACU'),('NYSE ARCA','FLAG'),('NYSE','CIVI'),('NYSE','CBL'),('NYSE ARCA','OILU'),('NYSE','HTZ'),('NYSE ARCA','GBUY'),('NASDAQ','BEAT'),('NASDAQ','SG'),('NASDAQ','LFACU'),('NYSE','CTV'),('NASDAQ','SAMA'),('NASDAQ','ROSE'),('NASDAQ','ROSEW'),('NASDAQ','RILYG'),('NYSE','HHS'),('NYSE','HCP'),('NASDAQ','SAMAW'),('NASDAQ','NHIC'),('NASDAQ','NHICW'),('NASDAQ','LFACW'),('NASDAQ','BRACU'),('NASDAQ','SES'),('NYSE ARCA','SEA'),('NYSE','RESI'),('NASDAQ','AMTD'),('NASDAQ','LFAC'),('NYSE','OBE'),('NASDAQ','MCACU'),('NASDAQ','BRACR'),('NASDAQ','BRAC'),('NYSE ARCA','RTL'),('BATS','GDVD'),('NASDAQ','ASNS'),('NYSE','KCAC.WS'),('NYSE','DO'),('NYSE','CBX'),('NASDAQ','WTRE'),('NYSE','EE'),('NYSE','AFGE'),('NYSE','ALUS'),('NYSE','BTU'),('NYSE','BUR'),('NYSE','CLA'),('NYSE','CRC'),('NYSE','DNB'),('NYSE','EBR.B'),('NYSE','GSAH'),('NYSE','IPV.U'),('NYSE','JIH.U'),('NYSE','NAV-D'),('NYSE','ONE'),('NYSE','PFH'),('NYSE','RICE'),('NYSE','WSO.B'),('NYSE','ALUS.U'),('NYSE','CBO.P.A'),('NYSE','CCAC.U'),('NYSE','CTA.P.A'),('NYSE','GLEO.U'),('NYSE','GSAH.U'),('NYSE','IPOB.U'),('NYSE','ISG'),('NYSE','JPM.P.D'),('NYSE','KIM.P.J'),('NYSE','LHC'),('NYSE','LHC.WS'),('NYSE','LOAK.U'),('NYSE','PKD'),('NYSE','PSA.P.D'),('NYSE','RNR.P.E'),('NYSE','SFTW.U'),('NYSE','SLG.P.I'),('NYSE','SMTA'),('NYSE','SOAC.U'),('NYSE','SPG.P.J'),('NYSE','STT.P.G'),('NYSE','WFC.P.Y'),('NYSE','AAC'),('NYSE','BRPM'),('NYSE','CHK'),('NYSE','FPAC'),('NYSE','FPAC.WS'),('NYSE','GIG'),('NYSE','GTX'),('NYSE','KCAC'),('NYSE','SPAQ'),('NYSE','SPAQ.WS'),('NYSE','SPN'),('NYSE','VAL'),('NASDAQ','ADV'),('NASDAQ','ADVWW'),('NASDAQ','AMEH'),('NASDAQ','AMYT'),('NASDAQ','ANDA'),('NASDAQ','ANDAW'),('NASDAQ','ARKO'),('NASDAQ','ARKOW'),('NASDAQ','ARRY'),('NASDAQ','BCDA'),('NASDAQ','BRLIU'),('NASDAQ','CHNA'),('NASDAQ','CMCTP'),('NASDAQ','CMLS'),('NASDAQ','CTSO'),('NASDAQ','DDMXU'),('NASDAQ','EDTXU'),('NASDAQ','ENVB'),('NASDAQ','FUSN'),('NASDAQ','GOEV'),('NASDAQ','GRNQ'),('NASDAQ','HX'),('NASDAQ','HYAC'),('NASDAQ','HYACU'),('NASDAQ','HYACW'),('NASDAQ','JAMF'),('NASDAQ','LCA'),('NASDAQ','LCAHU'),('NASDAQ','LCAHW'),('NASDAQ','LKCO'),('NASDAQ','MCBS'),('NASDAQ','MDGSW'),('NASDAQ','MNCLU'),('NASDAQ','MUDSU'),('NASDAQ','NEPH'),('NASDAQ','NHICU'),('NASDAQ','NMRD'),('NASDAQ','OPESU'),('NASDAQ','OPRX'),('NASDAQ','OPT'),('NASDAQ','PFHD'),('NASDAQ','POWW'),('NASDAQ','RILYL'),('NASDAQ','SBT'),('NASDAQ','SPRO'),('NASDAQ','TH'),('NASDAQ','THCAU'),('NASDAQ','TOTAR'),('NASDAQ','TTCFW'),('NASDAQ','TZACU'),('NYSE MKT','AAMC'),('BATS','AVDR'),('NYSE ARCA','AWAY'),('NYSE ARCA','CAPE'),('NYSE MKT','CHAQ.U'),('NYSE ARCA','CHIC'),('NYSE ARCA','DPK'),('NYSE ARCA','EEB'),('BATS','EURZ'),('BATS','EVIX'),('NYSE ARCA','GASL'),('NYSE ARCA','GASX'),('NASDAQ','GRSHU'),('BATS','GTIP'),('NYSE ARCA','HAO'),('BATS','HYXU'),('NYSE MKT','ID'),('NYSE ARCA','IGZ'),('NASDAQ','INTL'),('NYSE ARCA','MIDZ'),('NYSE MKT','NES'),('NASDAQ','NIHD'),('NASDAQ','PAAC'),('NASDAQ','PAACR'),('NASDAQ','PAACW'),('NYSE ARCA','PLTM'),('NASDAQ','POPM'),('NASDAQ','PRTHU'),('NASDAQ','ROCC'),('NASDAQ','RTIX'),('NASDAQ','RUBI'),('NYSE ARCA','RUSS'),('NASDAQ','SVA'),('NYSE ARCA','TAO'),('NASDAQ','TKGZY'),('NYSE MKT','VNRX'),('NASDAQ','WRLSU'),('NASDAQ','XOG'),('NASDAQ','ADRA'),('NASDAQ','BCAC'),('NASDAQ','BCACU'),('NASDAQ','BCACW'),('NYSE MKT','BTX'),('NASDAQ','BVNSC'),('NASDAQ','DDMX'),('NASDAQ','DDMXW'),('NASDAQ','DISHV'),('NASDAQ','DNJR'),('NASDAQ','DWIN'),('NASDAQ','EDTX'),('NASDAQ','EDTXW'),('NASDAQ','FSBC'),('NASDAQ','GPOR'),('NASDAQ','IVFVC'),('NASDAQ','KBLMU'),('NASDAQ','KMPH'),('NASDAQ','MMDMU'),('NASDAQ','MUDS'),('NASDAQ','MUDSW'),('NASDAQ','NEWTZ'),('NASDAQ','PVAL'),('NASDAQ','PXUS'),('NASDAQ','TWLV'),('NASDAQ','TWLVW'),('NASDAQ','VTIQ'),('NASDAQ','VTIQU'),('NASDAQ','VTIQW'),('NYSE ARCA','WTIU'),('NASDAQ','LALT'),('NYSE','FG'),('NYSE ARCA','PPEM'),('NASDAQ','ISRL'),('NASDAQ','IIVI'),('NASDAQ','GRCYU'),('NASDAQ','INFR'),('NYSE ARCA','WTID'),('NASDAQ','TBIO'),('NYSE','GEN'),('NYSE','BTE'),('NYSE ARCA','DIVY')
# had weird start values but second day on was normal
# ,('TSX','HBGD') TSX	HBGD	DAILY	2018-06-21	75.27	75.27	74.82	74.82	6751	0
# ,('TSX','XMA') TSX	XMA	DAILY	2005-12-23	82.12	82.6	82	82.4	308672	0

,('TSX','FHE'),('TSX','FURY'),('TSX','FLBA'),('TSX','EQX'),('TSX','ULV.U'),('TSX','FHC.F'),('TSX','GLXY'),('NYSE ARCA','PRME'),('TSX','ADW.B'),('TSX','CXB'),('TSX','ASND'),('NYSE','PRH'),('NASDAQ','ESSCU'),('TSX','MDNA'),('TSX','MIN'),('TSX','OLA'),('TSX','BCT'),('NYSE','SDRL'),('BATS','GSD'),('NASDAQ','ACAC'),('TSX','AT'),('TSX','UMI.B'),('TSX','FF'),('NASDAQ','AXAS'),('TSX','ESM'),('TSX','CTS'),('TSX','LABS'),('TSX','ITE'),('TSX','IVQ'),('TSX','CFF'),('TSX','VLNS'),('NYSE','EMPW'),('TSX','XLY'),('TSX','HUT'),('TSX','SBT.U'),('NYSE MKT','CVU'),('TSX','GURU'),('TSX','IMV'),('NASDAQ','ACACW'),('TSX','GRN'),('TSX','SSL'),('TSX','ASP'),('TSX','PXG.U'),('NASDAQ','CXDC'),('TSX','TNX'),('TSX','NXE'),('TSX','FEC'),('TSX','LN'),('TSX','AR'),('TSX','FAF'),('TSX','FTRP'),('NASDAQ','EMCG'),('TSX','E'),('NASDAQ','CBMB'),('TSX','BTB.UN'),('TSX','NCU'),('TSX','PAT'),('TSX','PYF.B'),('TSX','AVNT'),('TSX','SCL'),('TSX','JAG'),('TSX','GLO'),('TSX','CNT'),('TSX','BRAG'),('NASDAQ','XONE'),('TSX','HUM'),('NYSE','MNK'),('TSX','RUE.U'),('NASDAQ','GNRS'),('NYSE','AMID'),('TSX','HEXO'),('NYSE','NEE-R'),('TSX','NHK'),('TSX','PYR'),('NASDAQ','MCAC'),('NASDAQ','TLF'),('NASDAQ','IDXG'),('NASDAQ','MCACR'),('TSX','ARIS'),('TSX','VLE'),('TSX','EGLX'),('NYSE','POL'),('TSX','VIVO'),('TSX','DN'),('NYSE','RBC'),('TSX','ACB'),('NASDAQ','ACACU'),('TSX','PRV.UN'),('TSX','NCF'),('TSX','PRN'),('NASDAQ','TCCO'),('TSX','CEF.U'),('NYSE ARCA','RENW'),('NASDAQ','GNRSW'),('NASDAQ','INAQW'),('NYSE ARCA','GRI')

## AUTO-WRITTEN - DO NOT REMOVE OR CHANGE THIS OR NEXT TWO LINES
,('NASDAQ','LANDP'),('NYSE','FI'),('NYSE','OPP.R.W'),('NASDAQ','GAINL'),('NYSE','NEE.P.Q'),('NASDAQ','INAQU')
#####
]

unusableSymbols = testingSymbols + extremeSymbols + damagedSymbols



months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
foundedSynonyms = ['inception', 'founded', 'formed', 'incorporated']


## normalization
stockOffset = 0
vixOffset = 0


## No Commission Scotia stocks
tseEquity = ['XSP','VFV','ESG','HXS','XQQ','QQC.F','XIU','HXT','XIC','VEF','XEU','HBGD','CDZ','DXC','CUD','DXU','CYH','DXR','QQCC','DXET','CEW','VRE','XIT','XMA','XST','XUT','XHC','CGR','COW','CWW','DXF','DXN','CPD','DXP','DXEM','XEC','XCH','XID','XCS']
neoEquity = ['SITC','SITI','SITU','EAAI','EAGB','EARK','EAUT','SRIC','SRIU','MWMN','SRII','CJP','CWO']
batsEquity = ['OMFL','OMFS','IEFA','FINX','HERO','PRNT','PSI','WCLD','HLAL','MILN','NACP','PAWZ','IXC','IXP','IAT','VCR','VDC','VDE','VIS','MRGR','FLQM','HSCZ','SIZE','VLUE']
tseBalanced = ['XGRO','FIE','XBAL','VCNS','XCNS','XINC']
batsBalanced = ['AOA','AOM']
tseFixedIncome = ['CHB','CSD','DXO','CBO','DXV','VCB','XCB','CLF','HBB','XQB']
neoFixedIncome = ['SRIB','SITB']
batsFixedIncome = ['TLT']
tseCommodity = ['CGL','CGL.C','HUC','HUN','HUZ','SVR']
tseNoCommissionSymbols = tseEquity + tseBalanced + tseFixedIncome + tseCommodity
tseNoCommissionTickers = [('TSX', s) for s in tseNoCommissionSymbols]
neoNoCommissionSymbols = neoEquity + neoFixedIncome
neoNoCommissionTickers = [('NEO', s) for s in neoNoCommissionSymbols]
batsNoCommissionSymbols = batsEquity + batsBalanced + batsFixedIncome
batsNoCommissionTickers = [('BATS', s) for s in batsNoCommissionSymbols]
noCommissionSymbols = tseNoCommissionSymbols + neoNoCommissionSymbols + batsNoCommissionSymbols
noCommissionTickers = tseNoCommissionTickers + neoNoCommissionTickers + batsNoCommissionTickers
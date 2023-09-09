from datetime import datetime

## TABLE: exchanges ######################################
exchangesSnakeCaseTableColumns = ['code', 'name']
exchangesCamelCaseTableColumns = ['code', 'name']
class ExchangesRow():
	def __init__(self, codeValue: str, nameValue: str):
		self.code = codeValue
		self.name = nameValue

## TABLE: exchange_aliases ######################################
exchangeAliasesSnakeCaseTableColumns = ['exchange', 'alias', 'api']
exchangeAliasesCamelCaseTableColumns = ['exchange', 'alias', 'api']
class ExchangeAliasesRow():
	def __init__(self, exchangeValue: str, aliasValue: str, apiValue: str):
		self.exchange = exchangeValue
		self.alias = aliasValue
		self.api = apiValue

## TABLE: asset_types ######################################
assetTypesSnakeCaseTableColumns = ['type', 'description']
assetTypesCamelCaseTableColumns = ['type', 'description']
class AssetTypesRow():
	def __init__(self, typeValue: str, descriptionValue: str):
		self.type = typeValue
		self.description = descriptionValue

## TABLE: sqlite_sequence ######################################
sqliteSequenceSnakeCaseTableColumns = ['name', 'seq']
sqliteSequenceCamelCaseTableColumns = ['name', 'seq']
class SqliteSequenceRow():
	def __init__(self, nameValue, seqValue):
		self.name = nameValue
		self.seq = seqValue

## TABLE: cboe_volatility_index ######################################
cboeVolatilityIndexSnakeCaseTableColumns = ['date', 'open', 'high', 'low', 'close', 'artificial']
cboeVolatilityIndexCamelCaseTableColumns = ['date', 'open', 'high', 'low', 'close', 'artificial']
class CboeVolatilityIndexRow():
	def __init__(self, dateValue: str, openValue: float, highValue: float, lowValue: float, closeValue: float, artificialValue: bool):
		self.date = dateValue
		self.open = openValue
		self.high = highValue
		self.low = lowValue
		self.close = closeValue
		self.artificial = artificialValue

## TABLE: symbols ######################################
symbolsSnakeCaseTableColumns = ['exchange', 'symbol', 'name', 'asset_type', 'api_alphavantage', 'api_polygon', 'google_topic_id', 'sector', 'industry', 'founded', 'api_fmp', 'api_neo']
symbolsCamelCaseTableColumns = ['exchange', 'symbol', 'name', 'assetType', 'apiAlphavantage', 'apiPolygon', 'googleTopicId', 'sector', 'industry', 'founded', 'apiFmp', 'apiNeo']
class SymbolsRow():
	def __init__(self, exchangeValue: str, symbolValue: str, nameValue: str, assetTypeValue: str, apiAlphavantageValue: int, apiPolygonValue: int, googleTopicIdValue: str, sectorValue: int, industryValue: str, foundedValue: str, apiFmpValue: int, apiNeoValue: int):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.name = nameValue
		self.assetType = assetTypeValue
		self.apiAlphavantage = apiAlphavantageValue
		self.apiPolygon = apiPolygonValue
		self.googleTopicId = googleTopicIdValue
		self.sector = sectorValue
		self.industry = industryValue
		self.founded = foundedValue
		self.apiFmp = apiFmpValue
		self.apiNeo = apiNeoValue

## TABLE: sectors ######################################
sectorsSnakeCaseTableColumns = ['sector', 'icb_industry', 'gics_sector']
sectorsCamelCaseTableColumns = ['sector', 'icbIndustry', 'gicsSector']
class SectorsRow():
	def __init__(self, sectorValue: str, icbIndustryValue: str, gicsSectorValue: str):
		self.sector = sectorValue
		self.icbIndustry = icbIndustryValue
		self.gicsSector = gicsSectorValue

## TABLE: input_vector_factories ######################################
inputVectorFactoriesSnakeCaseTableColumns = ['id', 'factory', 'config']
inputVectorFactoriesCamelCaseTableColumns = ['id', 'factory', 'config']
class InputVectorFactoriesRow():
	def __init__(self, idValue: int, factoryValue: bytes, configValue: bytes):
		self.id = idValue
		self.factory = factoryValue
		self.config = configValue

## TABLE: edgar_sub_balance_status ######################################
edgarSubBalanceStatusSnakeCaseTableColumns = ['adsh', 'ddate', 'status']
edgarSubBalanceStatusCamelCaseTableColumns = ['adsh', 'ddate', 'status']
class EdgarSubBalanceStatusRow():
	def __init__(self, adshValue: str, ddateValue: str, statusValue: float):
		self.adsh = adshValue
		self.ddate = ddateValue
		self.status = statusValue

## TABLE: vwtb_edgar_quarters ######################################
vwtbEdgarQuartersSnakeCaseTableColumns = ['exchange', 'symbol', 'period', 'quarter', 'filed']
vwtbEdgarQuartersCamelCaseTableColumns = ['exchange', 'symbol', 'period', 'quarter', 'filed']
class VwtbEdgarQuartersRow():
	def __init__(self, exchangeValue: str, symbolValue: str, periodValue: str, quarterValue: int, filedValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.period = periodValue
		self.quarter = quarterValue
		self.filed = filedValue

## TABLE: vwtb_edgar_financial_nums ######################################
vwtbEdgarFinancialNumsSnakeCaseTableColumns = ['exchange', 'symbol', 'tag', 'ddate', 'qtrs', 'uom', 'value', 'duplicate']
vwtbEdgarFinancialNumsCamelCaseTableColumns = ['exchange', 'symbol', 'tag', 'ddate', 'qtrs', 'uom', 'value', 'duplicate']
class VwtbEdgarFinancialNumsRow():
	def __init__(self, exchangeValue: str, symbolValue: str, tagValue: str, ddateValue: str, qtrsValue: int, uomValue: str, valueValue: int, duplicateValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.tag = tagValue
		self.ddate = ddateValue
		self.qtrs = qtrsValue
		self.uom = uomValue
		self.value = valueValue
		self.duplicate = duplicateValue

## TABLE: sqlite_stat1 ######################################
sqliteStat1SnakeCaseTableColumns = ['tbl', 'idx', 'stat']
sqliteStat1CamelCaseTableColumns = ['tbl', 'idx', 'stat']
class SqliteStat1Row():
	def __init__(self, tblValue, idxValue, statValue):
		self.tbl = tblValue
		self.idx = idxValue
		self.stat = statValue

## TABLE: network_accuracies ######################################
networkAccuraciesSnakeCaseTableColumns = ['network_id', 'accuracy_type', 'subtype1', 'subtype2', 'sum', 'count']
networkAccuraciesCamelCaseTableColumns = ['networkId', 'accuracyType', 'subtype1', 'subtype2', 'sum', 'count']
class NetworkAccuraciesRow():
	def __init__(self, networkIdValue: int, accuracyTypeValue: str, subtype1Value: str, subtype2Value: str, sumValue: float, countValue: int):
		self.networkId = networkIdValue
		self.accuracyType = accuracyTypeValue
		self.subtype1 = subtype1Value
		self.subtype2 = subtype2Value
		self.sum = sumValue
		self.count = countValue

## TABLE: ticker_splits ######################################
tickerSplitsSnakeCaseTableColumns = ['network_id', 'set_count', 'ticker_count', 'pickled_split']
tickerSplitsCamelCaseTableColumns = ['networkId', 'setCount', 'tickerCount', 'pickledSplit']
class TickerSplitsRow():
	def __init__(self, networkIdValue: int, setCountValue: int, tickerCountValue: int, pickledSplitValue: bytes):
		self.networkId = networkIdValue
		self.setCount = setCountValue
		self.tickerCount = tickerCountValue
		self.pickledSplit = pickledSplitValue

## TABLE: asset_subtypes ######################################
assetSubtypesSnakeCaseTableColumns = ['asset_type', 'sub_type']
assetSubtypesCamelCaseTableColumns = ['assetType', 'subType']
class AssetSubtypesRow():
	def __init__(self, assetTypeValue: str, subTypeValue: str):
		self.assetType = assetTypeValue
		self.subType = subTypeValue

## TABLE: status_key ######################################
statusKeySnakeCaseTableColumns = ['status', 'description']
statusKeyCamelCaseTableColumns = ['status', 'description']
class StatusKeyRow():
	def __init__(self, statusValue: int, descriptionValue: str):
		self.status = statusValue
		self.description = descriptionValue

## TABLE: historical_data ######################################
historicalDataSnakeCaseTableColumns = ['exchange', 'symbol', 'series_type', 'period_date', 'open', 'high', 'low', 'close', 'volume', 'artificial']
historicalDataCamelCaseTableColumns = ['exchange', 'symbol', 'seriesType', 'periodDate', 'open', 'high', 'low', 'close', 'volume', 'artificial']
class HistoricalDataRow():
	def __init__(self, exchangeValue: str, symbolValue: str, seriesTypeValue: str, periodDateValue: str, openValue: float, highValue: float, lowValue: float, closeValue: float, volumeValue: float, artificialValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.seriesType = seriesTypeValue
		self.periodDate = periodDateValue
		self.open = openValue
		self.high = highValue
		self.low = lowValue
		self.close = closeValue
		self.volume = volumeValue
		self.artificial = artificialValue

## TABLE: last_updates ######################################
lastUpdatesSnakeCaseTableColumns = ['exchange', 'symbol', 'type', 'api', 'date']
lastUpdatesCamelCaseTableColumns = ['exchange', 'symbol', 'type', 'api', 'date']
class LastUpdatesRow():
	def __init__(self, exchangeValue: str, symbolValue: str, typeValue: str, apiValue: str, dateValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.type = typeValue
		self.api = apiValue
		self.date = dateValue

## TABLE: google_interests ######################################
googleInterestsSnakeCaseTableColumns = ['exchange', 'symbol', 'date', 'relative_interest']
googleInterestsCamelCaseTableColumns = ['exchange', 'symbol', 'date', 'relativeInterest']
class GoogleInterestsRow():
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, relativeInterestValue: int):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.relativeInterest = relativeInterestValue

## TABLE: historical_calculated_technical_indicator_data ######################################
historicalCalculatedTechnicalIndicatorDataSnakeCaseTableColumns = ['exchange', 'symbol', 'date_type', 'date', 'indicator', 'period', 'value']
historicalCalculatedTechnicalIndicatorDataCamelCaseTableColumns = ['exchange', 'symbol', 'dateType', 'date', 'indicator', 'period', 'value']
class HistoricalCalculatedTechnicalIndicatorDataRow():
	def __init__(self, exchangeValue: str, symbolValue: str, dateTypeValue: str, dateValue: str, indicatorValue: str, periodValue: float, valueValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.dateType = dateTypeValue
		self.date = dateValue
		self.indicator = indicatorValue
		self.period = periodValue
		self.value = valueValue

## TABLE: historical_vector_similarity_data ######################################
historicalVectorSimilarityDataSnakeCaseTableColumns = ['exchange', 'symbol', 'date_type', 'date', 'vector_class', 'preceding_range', 'following_range', 'change_threshold', 'value']
historicalVectorSimilarityDataCamelCaseTableColumns = ['exchange', 'symbol', 'dateType', 'date', 'vectorClass', 'precedingRange', 'followingRange', 'changeThreshold', 'value']
class HistoricalVectorSimilarityDataRow():
	def __init__(self, exchangeValue: str, symbolValue: str, dateTypeValue: str, dateValue: str, vectorClassValue: str, precedingRangeValue: float, followingRangeValue: float, changeThresholdValue: float, valueValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.dateType = dateTypeValue
		self.date = dateValue
		self.vectorClass = vectorClassValue
		self.precedingRange = precedingRangeValue
		self.followingRange = followingRangeValue
		self.changeThreshold = changeThresholdValue
		self.value = valueValue

## TABLE: networks_temp ######################################
networksTempSnakeCaseTableColumns = ['id', 'factoryId', 'accuracyType', 'overallAccuracy', 'negativeAccuracy', 'positiveAccuracy', 'changeThreshold', 'precedingRange', 'followingRange', 'seriesType', 'highMax', 'volumeMax', 'epochs']
networksTempCamelCaseTableColumns = ['id', 'factoryId', 'accuracyType', 'overallAccuracy', 'negativeAccuracy', 'positiveAccuracy', 'changeThreshold', 'precedingRange', 'followingRange', 'seriesType', 'highMax', 'volumeMax', 'epochs']
class NetworksTempRow():
	def __init__(self, idValue: int, factoryIdValue: int, accuracyTypeValue: str, overallAccuracyValue: int, negativeAccuracyValue: int, positiveAccuracyValue: int, changeThresholdValue: int, precedingRangeValue: int, followingRangeValue: int, seriesTypeValue: str, highMaxValue: int, volumeMaxValue: int, epochsValue: int):
		self.id = idValue
		self.factoryId = factoryIdValue
		self.accuracyType = accuracyTypeValue
		self.overallAccuracy = overallAccuracyValue
		self.negativeAccuracy = negativeAccuracyValue
		self.positiveAccuracy = positiveAccuracyValue
		self.changeThreshold = changeThresholdValue
		self.precedingRange = precedingRangeValue
		self.followingRange = followingRangeValue
		self.seriesType = seriesTypeValue
		self.highMax = highMaxValue
		self.volumeMax = volumeMaxValue
		self.epochs = epochsValue

## TABLE: networks ######################################
networksSnakeCaseTableColumns = ['id', 'factory_id', 'accuracy_type', 'overall_accuracy', 'negative_accuracy', 'positive_accuracy', 'epochs']
networksCamelCaseTableColumns = ['id', 'factoryId', 'accuracyType', 'overallAccuracy', 'negativeAccuracy', 'positiveAccuracy', 'epochs']
class NetworksRow():
	def __init__(self, idValue: int, factoryIdValue: int, accuracyTypeValue: str, overallAccuracyValue: float, negativeAccuracyValue: float, positiveAccuracyValue: float, epochsValue: int):
		self.id = idValue
		self.factoryId = factoryIdValue
		self.accuracyType = accuracyTypeValue
		self.overallAccuracy = overallAccuracyValue
		self.negativeAccuracy = negativeAccuracyValue
		self.positiveAccuracy = positiveAccuracyValue
		self.epochs = epochsValue

## TABLE: network_training_config ######################################
networkTrainingConfigSnakeCaseTableColumns = ['id', 'preceding_range', 'following_range', 'change_value', 'change_type', 'series_type', 'highest_historical_high', 'highest_historical_volume', 'minimum_historical_close_allowed']
networkTrainingConfigCamelCaseTableColumns = ['id', 'precedingRange', 'followingRange', 'changeValue', 'changeType', 'seriesType', 'highestHistoricalHigh', 'highestHistoricalVolume', 'minimumHistoricalCloseAllowed']
class NetworkTrainingConfigRow():
	def __init__(self, idValue: int, precedingRangeValue: int, followingRangeValue: int, changeValueValue: int, changeTypeValue: str, seriesTypeValue: str, highestHistoricalHighValue: float, highestHistoricalVolumeValue: float, minimumHistoricalCloseAllowedValue: float):
		self.id = idValue
		self.precedingRange = precedingRangeValue
		self.followingRange = followingRangeValue
		self.changeValue = changeValueValue
		self.changeType = changeTypeValue
		self.seriesType = seriesTypeValue
		self.highestHistoricalHigh = highestHistoricalHighValue
		self.highestHistoricalVolume = highestHistoricalVolumeValue
		self.minimumHistoricalCloseAllowed = minimumHistoricalCloseAllowedValue

## TABLE: historical_data_minute ######################################
historicalDataMinuteSnakeCaseTableColumns = ['exchange', 'symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume_weighted_average', 'volume', 'transactions', 'artificial']
historicalDataMinuteCamelCaseTableColumns = ['exchange', 'symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volumeWeightedAverage', 'volume', 'transactions', 'artificial']
class HistoricalDataMinuteRow():
	def __init__(self, exchangeValue: str, symbolValue: str, timestampValue: datetime, openValue: float, highValue: float, lowValue: float, closeValue: float, volumeWeightedAverageValue: float, volumeValue: float, transactionsValue: float, artificialValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.timestamp = timestampValue
		self.open = openValue
		self.high = highValue
		self.low = lowValue
		self.close = closeValue
		self.volumeWeightedAverage = volumeWeightedAverageValue
		self.volume = volumeValue
		self.transactions = transactionsValue
		self.artificial = artificialValue

## TABLE: accuracy_last_updates ######################################
accuracyLastUpdatesSnakeCaseTableColumns = ['network_id', 'accuracy_type', 'data_count', 'min_date', 'last_exchange', 'last_symbol']
accuracyLastUpdatesCamelCaseTableColumns = ['networkId', 'accuracyType', 'dataCount', 'minDate', 'lastExchange', 'lastSymbol']
class AccuracyLastUpdatesRow():
	def __init__(self, networkIdValue: int, accuracyTypeValue: int, dataCountValue: int, minDateValue: int, lastExchangeValue: int, lastSymbolValue: int):
		self.networkId = networkIdValue
		self.accuracyType = accuracyTypeValue
		self.dataCount = dataCountValue
		self.minDate = minDateValue
		self.lastExchange = lastExchangeValue
		self.lastSymbol = lastSymbolValue

## TABLE: earnings_dates ######################################
earningsDatesSnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'earnings_date']
earningsDatesCamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'earningsDate']
class EarningsDatesRow():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, earningsDateValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue

## TABLE: staging_symbol_info ######################################
stagingSymbolInfoSnakeCaseTableColumns = ['exchange', 'symbol', 'migrated', 'founded', 'ipo', 'sector', 'polygon_sector', 'fmp_sector', 'alphavantage_sector', 'polygon_industry', 'fmp_industry', 'alphavantage_industry', 'polygon_description', 'fmp_description', 'alphavantage_description', 'polygon_ipo', 'fmp_ipo', 'alphavantage_assettype', 'fmp_isetf']
stagingSymbolInfoCamelCaseTableColumns = ['exchange', 'symbol', 'migrated', 'founded', 'ipo', 'sector', 'polygonSector', 'fmpSector', 'alphavantageSector', 'polygonIndustry', 'fmpIndustry', 'alphavantageIndustry', 'polygonDescription', 'fmpDescription', 'alphavantageDescription', 'polygonIpo', 'fmpIpo', 'alphavantageAssettype', 'fmpIsetf']
class StagingSymbolInfoRow():
	def __init__(self, exchangeValue: str, symbolValue: str, migratedValue: bool, foundedValue: str, ipoValue: str, sectorValue: str, polygonSectorValue: str, fmpSectorValue: str, alphavantageSectorValue: str, polygonIndustryValue: str, fmpIndustryValue: str, alphavantageIndustryValue: str, polygonDescriptionValue: str, fmpDescriptionValue: str, alphavantageDescriptionValue: str, polygonIpoValue: str, fmpIpoValue: str, alphavantageAssettypeValue: str, fmpIsetfValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.migrated = migratedValue
		self.founded = foundedValue
		self.ipo = ipoValue
		self.sector = sectorValue
		self.polygonSector = polygonSectorValue
		self.fmpSector = fmpSectorValue
		self.alphavantageSector = alphavantageSectorValue
		self.polygonIndustry = polygonIndustryValue
		self.fmpIndustry = fmpIndustryValue
		self.alphavantageIndustry = alphavantageIndustryValue
		self.polygonDescription = polygonDescriptionValue
		self.fmpDescription = fmpDescriptionValue
		self.alphavantageDescription = alphavantageDescriptionValue
		self.polygonIpo = polygonIpoValue
		self.fmpIpo = fmpIpoValue
		self.alphavantageAssettype = alphavantageAssettypeValue
		self.fmpIsetf = fmpIsetfValue

## TABLE: dump_symbol_info ######################################
dumpSymbolInfoSnakeCaseTableColumns = ['exchange', 'symbol', 'alphavantage', 'fmp', 'polygon', 'polygon_logo', 'polygon_listdate', 'polygon_cik', 'polygon_bloomberg', 'polygon_figi', 'polygon_lei', 'polygon_sic', 'polygon_country', 'polygon_industry', 'polygon_sector', 'polygon_marketcap', 'polygon_employees', 'polygon_phone', 'polygon_ceo', 'polygon_url', 'polygon_description', 'polygon_name', 'polygon_exchangeSymbol', 'polygon_hq_address', 'polygon_hq_state', 'polygon_hq_country', 'polygon_type', 'polygon_updated', 'polygon_tags', 'polygon_similar', 'polygon_active']
dumpSymbolInfoCamelCaseTableColumns = ['exchange', 'symbol', 'alphavantage', 'fmp', 'polygon', 'polygonLogo', 'polygonListdate', 'polygonCik', 'polygonBloomberg', 'polygonFigi', 'polygonLei', 'polygonSic', 'polygonCountry', 'polygonIndustry', 'polygonSector', 'polygonMarketcap', 'polygonEmployees', 'polygonPhone', 'polygonCeo', 'polygonUrl', 'polygonDescription', 'polygonName', 'polygonExchangeSymbol', 'polygonHqAddress', 'polygonHqState', 'polygonHqCountry', 'polygonType', 'polygonUpdated', 'polygonTags', 'polygonSimilar', 'polygonActive']
class DumpSymbolInfoRow():
	def __init__(self, exchangeValue: str, symbolValue: str, alphavantageValue: int, fmpValue: int, polygonValue: int, polygonLogoValue: str, polygonListdateValue: str, polygonCikValue: str, polygonBloombergValue: str, polygonFigiValue: str, polygonLeiValue: str, polygonSicValue: str, polygonCountryValue: str, polygonIndustryValue: str, polygonSectorValue: str, polygonMarketcapValue: str, polygonEmployeesValue: str, polygonPhoneValue: str, polygonCeoValue: str, polygonUrlValue: str, polygonDescriptionValue: str, polygonNameValue: str, polygonExchangeSymbolValue: str, polygonHqAddressValue: str, polygonHqStateValue: str, polygonHqCountryValue: str, polygonTypeValue: str, polygonUpdatedValue: str, polygonTagsValue: str, polygonSimilarValue: str, polygonActiveValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.alphavantage = alphavantageValue
		self.fmp = fmpValue
		self.polygon = polygonValue
		self.polygonLogo = polygonLogoValue
		self.polygonListdate = polygonListdateValue
		self.polygonCik = polygonCikValue
		self.polygonBloomberg = polygonBloombergValue
		self.polygonFigi = polygonFigiValue
		self.polygonLei = polygonLeiValue
		self.polygonSic = polygonSicValue
		self.polygonCountry = polygonCountryValue
		self.polygonIndustry = polygonIndustryValue
		self.polygonSector = polygonSectorValue
		self.polygonMarketcap = polygonMarketcapValue
		self.polygonEmployees = polygonEmployeesValue
		self.polygonPhone = polygonPhoneValue
		self.polygonCeo = polygonCeoValue
		self.polygonUrl = polygonUrlValue
		self.polygonDescription = polygonDescriptionValue
		self.polygonName = polygonNameValue
		self.polygonExchangeSymbol = polygonExchangeSymbolValue
		self.polygonHqAddress = polygonHqAddressValue
		self.polygonHqState = polygonHqStateValue
		self.polygonHqCountry = polygonHqCountryValue
		self.polygonType = polygonTypeValue
		self.polygonUpdated = polygonUpdatedValue
		self.polygonTags = polygonTagsValue
		self.polygonSimilar = polygonSimilarValue
		self.polygonActive = polygonActiveValue

## TABLE: dump_edgar_tag ######################################
dumpEdgarTagSnakeCaseTableColumns = ['tag', 'version', 'custom', 'abstract', 'datatype', 'iord', 'crdr', 'tlabel', 'doc']
dumpEdgarTagCamelCaseTableColumns = ['tag', 'version', 'custom', 'abstract', 'datatype', 'iord', 'crdr', 'tlabel', 'doc']
class DumpEdgarTagRow():
	def __init__(self, tagValue: str, versionValue: str, customValue: bool, abstractValue: bool, datatypeValue: str, iordValue: str, crdrValue: str, tlabelValue: str, docValue: str):
		self.tag = tagValue
		self.version = versionValue
		self.custom = customValue
		self.abstract = abstractValue
		self.datatype = datatypeValue
		self.iord = iordValue
		self.crdr = crdrValue
		self.tlabel = tlabelValue
		self.doc = docValue

## TABLE: dump_edgar_sub ######################################
dumpEdgarSubSnakeCaseTableColumns = ['exchange', 'symbol', 'adsh', 'cik', 'name', 'sic', 'countryba', 'stprba', 'cityba', 'zipba', 'bas1', 'bas2', 'baph', 'countryma', 'stprma', 'cityma', 'zipma', 'mas1', 'mas2', 'countryinc', 'stprinc', 'ein', 'former', 'changed', 'afs', 'wksi', 'fye', 'form', 'period', 'fy', 'fp', 'filed', 'accepted', 'prevrpt', 'detail', 'instance', 'nciks', 'aciks']
dumpEdgarSubCamelCaseTableColumns = ['exchange', 'symbol', 'adsh', 'cik', 'name', 'sic', 'countryba', 'stprba', 'cityba', 'zipba', 'bas1', 'bas2', 'baph', 'countryma', 'stprma', 'cityma', 'zipma', 'mas1', 'mas2', 'countryinc', 'stprinc', 'ein', 'former', 'changed', 'afs', 'wksi', 'fye', 'form', 'period', 'fy', 'fp', 'filed', 'accepted', 'prevrpt', 'detail', 'instance', 'nciks', 'aciks']
class DumpEdgarSubRow():
	def __init__(self, exchangeValue: str, symbolValue: str, adshValue: str, cikValue: str, nameValue: str, sicValue: str, countrybaValue: str, stprbaValue: str, citybaValue: str, zipbaValue: str, bas1Value: str, bas2Value: str, baphValue: str, countrymaValue: str, stprmaValue: str, citymaValue: str, zipmaValue: str, mas1Value: str, mas2Value: str, countryincValue: str, stprincValue: str, einValue: str, formerValue: str, changedValue: str, afsValue: str, wksiValue: bool, fyeValue: str, formValue: str, periodValue: str, fyValue: str, fpValue: str, filedValue: str, acceptedValue: str, prevrptValue: bool, detailValue: bool, instanceValue: str, nciksValue: str, aciksValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.adsh = adshValue
		self.cik = cikValue
		self.name = nameValue
		self.sic = sicValue
		self.countryba = countrybaValue
		self.stprba = stprbaValue
		self.cityba = citybaValue
		self.zipba = zipbaValue
		self.bas1 = bas1Value
		self.bas2 = bas2Value
		self.baph = baphValue
		self.countryma = countrymaValue
		self.stprma = stprmaValue
		self.cityma = citymaValue
		self.zipma = zipmaValue
		self.mas1 = mas1Value
		self.mas2 = mas2Value
		self.countryinc = countryincValue
		self.stprinc = stprincValue
		self.ein = einValue
		self.former = formerValue
		self.changed = changedValue
		self.afs = afsValue
		self.wksi = wksiValue
		self.fye = fyeValue
		self.form = formValue
		self.period = periodValue
		self.fy = fyValue
		self.fp = fpValue
		self.filed = filedValue
		self.accepted = acceptedValue
		self.prevrpt = prevrptValue
		self.detail = detailValue
		self.instance = instanceValue
		self.nciks = nciksValue
		self.aciks = aciksValue

## TABLE: dump_edgar_loaded ######################################
dumpEdgarLoadedSnakeCaseTableColumns = ['type', 'period']
dumpEdgarLoadedCamelCaseTableColumns = ['type', 'period']
class DumpEdgarLoadedRow():
	def __init__(self, typeValue: str, periodValue: str):
		self.type = typeValue
		self.period = periodValue

## TABLE: dump_edgar_num ######################################
dumpEdgarNumSnakeCaseTableColumns = ['adsh', 'tag', 'version', 'coreg', 'ddate', 'qtrs', 'uom', 'value', 'footnote', 'duplicate']
dumpEdgarNumCamelCaseTableColumns = ['adsh', 'tag', 'version', 'coreg', 'ddate', 'qtrs', 'uom', 'value', 'footnote', 'duplicate']
class DumpEdgarNumRow():
	def __init__(self, adshValue: str, tagValue: str, versionValue: str, coregValue: str, ddateValue: str, qtrsValue: str, uomValue: str, valueValue: float, footnoteValue: str, duplicateValue: bool):
		self.adsh = adshValue
		self.tag = tagValue
		self.version = versionValue
		self.coreg = coregValue
		self.ddate = ddateValue
		self.qtrs = qtrsValue
		self.uom = uomValue
		self.value = valueValue
		self.footnote = footnoteValue
		self.duplicate = duplicateValue

## TABLE: sqlite_stat1 ######################################
sqliteStat1SnakeCaseTableColumns = ['tbl', 'idx', 'stat']
sqliteStat1CamelCaseTableColumns = ['tbl', 'idx', 'stat']
class SqliteStat1Row():
	def __init__(self, tblValue, idxValue, statValue):
		self.tbl = tblValue
		self.idx = idxValue
		self.stat = statValue

## TABLE: dump_stock_splits_polygon ######################################
dumpStockSplitsPolygonSnakeCaseTableColumns = ['exchange', 'symbol', 'date', 'split_from', 'split_to']
dumpStockSplitsPolygonCamelCaseTableColumns = ['exchange', 'symbol', 'date', 'splitFrom', 'splitTo']
class DumpStockSplitsPolygonRow():
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, splitFromValue: float, splitToValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.splitFrom = splitFromValue
		self.splitTo = splitToValue

## TABLE: google_interests_raw ######################################
googleInterestsRawSnakeCaseTableColumns = ['exchange', 'symbol', 'date', 'type', 'stream', 'relative_interest', 'artificial']
googleInterestsRawCamelCaseTableColumns = ['exchange', 'symbol', 'date', 'type', 'stream', 'relativeInterest', 'artificial']
class GoogleInterestsRawRow():
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, typeValue: str, streamValue: int, relativeInterestValue: int, artificialValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.type = typeValue
		self.stream = streamValue
		self.relativeInterest = relativeInterestValue
		self.artificial = artificialValue

## TABLE: staging_financials ######################################
stagingFinancialsSnakeCaseTableColumns = ['exchange', 'symbol', 'period', 'calendarDate', 'polygon_reportPeriod', 'polygon_updated', 'polygon_dateKey', 'polygon_accumulatedOtherComprehensiveIncome', 'polygon_assets', 'polygon_assetsAverage', 'polygon_assetsCurrent', 'polygon_assetsNonCurrent', 'polygon_assetTurnover', 'polygon_bookValuePerShare', 'polygon_capitalExpenditure', 'polygon_cashAndEquivalents', 'polygon_cashAndEquivalentsUSD', 'polygon_costOfRevenue', 'polygon_consolidatedIncome', 'polygon_currentRatio', 'polygon_debtToEquityRatio', 'polygon_debt', 'polygon_debtCurrent', 'polygon_debtNonCurrent', 'polygon_debtUSD', 'polygon_deferredRevenue', 'polygon_depreciationAmortizationAndAccretion', 'polygon_deposits', 'polygon_dividendYield', 'polygon_dividendsPerBasicCommonShare', 'polygon_earningBeforeInterestTaxes', 'polygon_earningsBeforeInterestTaxesDepreciationAmortization', 'polygon_EBITDAMargin', 'polygon_earningsBeforeInterestTaxesDepreciationAmortizationUSD', 'polygon_earningBeforeInterestTaxesUSD', 'polygon_earningsBeforeTax', 'polygon_earningsPerBasicShare', 'polygon_earningsPerDilutedShare', 'polygon_earningsPerBasicShareUSD', 'polygon_shareholdersEquity', 'polygon_averageEquity', 'polygon_shareholdersEquityUSD', 'polygon_enterpriseValue', 'polygon_enterpriseValueOverEBIT', 'polygon_enterpriseValueOverEBITDA', 'polygon_freeCashFlow', 'polygon_freeCashFlowPerShare', 'polygon_foreignCurrencyUSDExchangeRate', 'polygon_grossProfit', 'polygon_grossMargin', 'polygon_goodwillAndIntangibleAssets', 'polygon_interestExpense', 'polygon_investedCapital', 'polygon_investedCapitalAverage', 'polygon_inventory', 'polygon_investments', 'polygon_investmentsCurrent', 'polygon_investmentsNonCurrent', 'polygon_totalLiabilities', 'polygon_currentLiabilities', 'polygon_liabilitiesNonCurrent', 'polygon_marketCapitalization', 'polygon_netCashFlow', 'polygon_netCashFlowBusinessAcquisitionsDisposals', 'polygon_issuanceEquityShares', 'polygon_issuanceDebtSecurities', 'polygon_paymentDividendsOtherCashDistributions', 'polygon_netCashFlowFromFinancing', 'polygon_netCashFlowFromInvesting', 'polygon_netCashFlowInvestmentAcquisitionsDisposals', 'polygon_netCashFlowFromOperations', 'polygon_effectOfExchangeRateChangesOnCash', 'polygon_netIncome', 'polygon_netIncomeCommonStock', 'polygon_netIncomeCommonStockUSD', 'polygon_netLossIncomeFromDiscontinuedOperations', 'polygon_netIncomeToNonControllingInterests', 'polygon_profitMargin', 'polygon_operatingExpenses', 'polygon_operatingIncome', 'polygon_tradeAndNonTradePayables', 'polygon_payoutRatio', 'polygon_priceToBookValue', 'polygon_priceEarnings', 'polygon_priceToEarningsRatio', 'polygon_propertyPlantEquipmentNet', 'polygon_preferredDividendsIncomeStatementImpact', 'polygon_sharePriceAdjustedClose', 'polygon_priceSales', 'polygon_priceToSalesRatio', 'polygon_tradeAndNonTradeReceivables', 'polygon_accumulatedRetainedEarningsDeficit', 'polygon_revenues', 'polygon_revenuesUSD', 'polygon_researchAndDevelopmentExpense', 'polygon_returnOnAverageAssets', 'polygon_returnOnAverageEquity', 'polygon_returnOnInvestedCapital', 'polygon_returnOnSales', 'polygon_shareBasedCompensation', 'polygon_sellingGeneralAndAdministrativeExpense', 'polygon_shareFactor', 'polygon_shares', 'polygon_weightedAverageShares', 'polygon_salesPerShare', 'polygon_tangibleAssetValue', 'polygon_taxAssets', 'polygon_incomeTaxExpense', 'polygon_taxLiabilities', 'polygon_tangibleAssetsBookValuePerShare', 'polygon_workingCapital', 'polygon_weightedAverageSharesDiluted', 'fmp', 'alphavantage', 'polygon', 'alphavantage_fiscalDateEnding', 'alphavantage_reportedCurrency', 'alphavantage_grossProfit', 'alphavantage_totalRevenue', 'alphavantage_costOfRevenue', 'alphavantage_costofGoodsAndServicesSold', 'alphavantage_operatingIncome', 'alphavantage_sellingGeneralAndAdministrative', 'alphavantage_researchAndDevelopment', 'alphavantage_operatingExpenses', 'alphavantage_investmentIncomeNet', 'alphavantage_netInterestIncome', 'alphavantage_interestIncome', 'alphavantage_interestExpense', 'alphavantage_nonInterestIncome', 'alphavantage_otherNonOperatingIncome', 'alphavantage_depreciation', 'alphavantage_depreciationAndAmortization', 'alphavantage_incomeBeforeTax', 'alphavantage_incomeTaxExpense', 'alphavantage_interestAndDebtExpense', 'alphavantage_netIncomeFromContinuingOperations', 'alphavantage_comprehensiveIncomeNetOfTax', 'alphavantage_ebit', 'alphavantage_ebitda', 'alphavantage_netIncome', 'alphavantage_totalAssets', 'alphavantage_totalCurrentAssets', 'alphavantage_cashAndCashEquivalentsAtCarryingValue', 'alphavantage_cashAndShortTermInvestments', 'alphavantage_inventory', 'alphavantage_currentNetReceivables', 'alphavantage_totalNonCurrentAssets', 'alphavantage_propertyPlantEquipment', 'alphavantage_accumulatedDepreciationAmortizationPPE', 'alphavantage_intangibleAssets', 'alphavantage_intangibleAssetsExcludingGoodwill', 'alphavantage_goodwill', 'alphavantage_investments', 'alphavantage_longTermInvestments', 'alphavantage_shortTermInvestments', 'alphavantage_otherCurrentAssets', 'alphavantage_otherNonCurrrentAssets', 'alphavantage_totalLiabilities', 'alphavantage_totalCurrentLiabilities', 'alphavantage_currentAccountsPayable', 'alphavantage_deferredRevenue', 'alphavantage_currentDebt', 'alphavantage_shortTermDebt', 'alphavantage_totalNonCurrentLiabilities', 'alphavantage_capitalLeaseObligations', 'alphavantage_longTermDebt', 'alphavantage_currentLongTermDebt', 'alphavantage_longTermDebtNoncurrent', 'alphavantage_shortLongTermDebtTotal', 'alphavantage_otherCurrentLiabilities', 'alphavantage_otherNonCurrentLiabilities', 'alphavantage_totalShareholderEquity', 'alphavantage_treasuryStock', 'alphavantage_retainedEarnings', 'alphavantage_commonStock', 'alphavantage_commonStockSharesOutstanding', 'alphavantage_operatingCashflow', 'alphavantage_paymentsForOperatingActivities', 'alphavantage_proceedsFromOperatingActivities', 'alphavantage_changeInOperatingLiabilities', 'alphavantage_changeInOperatingAssets', 'alphavantage_depreciationDepletionAndAmortization', 'alphavantage_capitalExpenditures', 'alphavantage_changeInReceivables', 'alphavantage_changeInInventory', 'alphavantage_profitLoss', 'alphavantage_cashflowFromInvestment', 'alphavantage_cashflowFromFinancing', 'alphavantage_proceedsFromRepaymentsOfShortTermDebt', 'alphavantage_paymentsForRepurchaseOfCommonStock', 'alphavantage_paymentsForRepurchaseOfEquity', 'alphavantage_paymentsForRepurchaseOfPreferredStock', 'alphavantage_dividendPayout', 'alphavantage_dividendPayoutCommonStock', 'alphavantage_dividendPayoutPreferredStock', 'alphavantage_proceedsFromIssuanceOfCommonStock', 'alphavantage_proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet', 'alphavantage_proceedsFromIssuanceOfPreferredStock', 'alphavantage_proceedsFromRepurchaseOfEquity', 'alphavantage_proceedsFromSaleOfTreasuryStock', 'alphavantage_changeInCashAndCashEquivalents', 'alphavantage_changeInExchangeRate', 'polygon_logo', 'polygon_listdate', 'polygon_cik', 'polygon_bloomberg', 'polygon_figi', 'polygon_lei', 'polygon_sic', 'polygon_country', 'polygon_industry', 'polygon_sector', 'polygon_marketcap', 'polygon_employees', 'polygon_phone', 'polygon_ceo', 'polygon_url', 'polygon_description', 'polygon_name', 'polygon_exchangeSymbol', 'polygon_hq_address', 'polygon_hq_state', 'polygon_hq_country', 'polygon_type', 'polygon_tags', 'polygon_similar', 'polygon_active']
stagingFinancialsCamelCaseTableColumns = ['exchange', 'symbol', 'period', 'calendarDate', 'polygonReportPeriod', 'polygonUpdated', 'polygonDateKey', 'polygonAccumulatedOtherComprehensiveIncome', 'polygonAssets', 'polygonAssetsAverage', 'polygonAssetsCurrent', 'polygonAssetsNonCurrent', 'polygonAssetTurnover', 'polygonBookValuePerShare', 'polygonCapitalExpenditure', 'polygonCashAndEquivalents', 'polygonCashAndEquivalentsUSD', 'polygonCostOfRevenue', 'polygonConsolidatedIncome', 'polygonCurrentRatio', 'polygonDebtToEquityRatio', 'polygonDebt', 'polygonDebtCurrent', 'polygonDebtNonCurrent', 'polygonDebtUSD', 'polygonDeferredRevenue', 'polygonDepreciationAmortizationAndAccretion', 'polygonDeposits', 'polygonDividendYield', 'polygonDividendsPerBasicCommonShare', 'polygonEarningBeforeInterestTaxes', 'polygonEarningsBeforeInterestTaxesDepreciationAmortization', 'polygonEBITDAMargin', 'polygonEarningsBeforeInterestTaxesDepreciationAmortizationUSD', 'polygonEarningBeforeInterestTaxesUSD', 'polygonEarningsBeforeTax', 'polygonEarningsPerBasicShare', 'polygonEarningsPerDilutedShare', 'polygonEarningsPerBasicShareUSD', 'polygonShareholdersEquity', 'polygonAverageEquity', 'polygonShareholdersEquityUSD', 'polygonEnterpriseValue', 'polygonEnterpriseValueOverEBIT', 'polygonEnterpriseValueOverEBITDA', 'polygonFreeCashFlow', 'polygonFreeCashFlowPerShare', 'polygonForeignCurrencyUSDExchangeRate', 'polygonGrossProfit', 'polygonGrossMargin', 'polygonGoodwillAndIntangibleAssets', 'polygonInterestExpense', 'polygonInvestedCapital', 'polygonInvestedCapitalAverage', 'polygonInventory', 'polygonInvestments', 'polygonInvestmentsCurrent', 'polygonInvestmentsNonCurrent', 'polygonTotalLiabilities', 'polygonCurrentLiabilities', 'polygonLiabilitiesNonCurrent', 'polygonMarketCapitalization', 'polygonNetCashFlow', 'polygonNetCashFlowBusinessAcquisitionsDisposals', 'polygonIssuanceEquityShares', 'polygonIssuanceDebtSecurities', 'polygonPaymentDividendsOtherCashDistributions', 'polygonNetCashFlowFromFinancing', 'polygonNetCashFlowFromInvesting', 'polygonNetCashFlowInvestmentAcquisitionsDisposals', 'polygonNetCashFlowFromOperations', 'polygonEffectOfExchangeRateChangesOnCash', 'polygonNetIncome', 'polygonNetIncomeCommonStock', 'polygonNetIncomeCommonStockUSD', 'polygonNetLossIncomeFromDiscontinuedOperations', 'polygonNetIncomeToNonControllingInterests', 'polygonProfitMargin', 'polygonOperatingExpenses', 'polygonOperatingIncome', 'polygonTradeAndNonTradePayables', 'polygonPayoutRatio', 'polygonPriceToBookValue', 'polygonPriceEarnings', 'polygonPriceToEarningsRatio', 'polygonPropertyPlantEquipmentNet', 'polygonPreferredDividendsIncomeStatementImpact', 'polygonSharePriceAdjustedClose', 'polygonPriceSales', 'polygonPriceToSalesRatio', 'polygonTradeAndNonTradeReceivables', 'polygonAccumulatedRetainedEarningsDeficit', 'polygonRevenues', 'polygonRevenuesUSD', 'polygonResearchAndDevelopmentExpense', 'polygonReturnOnAverageAssets', 'polygonReturnOnAverageEquity', 'polygonReturnOnInvestedCapital', 'polygonReturnOnSales', 'polygonShareBasedCompensation', 'polygonSellingGeneralAndAdministrativeExpense', 'polygonShareFactor', 'polygonShares', 'polygonWeightedAverageShares', 'polygonSalesPerShare', 'polygonTangibleAssetValue', 'polygonTaxAssets', 'polygonIncomeTaxExpense', 'polygonTaxLiabilities', 'polygonTangibleAssetsBookValuePerShare', 'polygonWorkingCapital', 'polygonWeightedAverageSharesDiluted', 'fmp', 'alphavantage', 'polygon', 'alphavantageFiscalDateEnding', 'alphavantageReportedCurrency', 'alphavantageGrossProfit', 'alphavantageTotalRevenue', 'alphavantageCostOfRevenue', 'alphavantageCostofGoodsAndServicesSold', 'alphavantageOperatingIncome', 'alphavantageSellingGeneralAndAdministrative', 'alphavantageResearchAndDevelopment', 'alphavantageOperatingExpenses', 'alphavantageInvestmentIncomeNet', 'alphavantageNetInterestIncome', 'alphavantageInterestIncome', 'alphavantageInterestExpense', 'alphavantageNonInterestIncome', 'alphavantageOtherNonOperatingIncome', 'alphavantageDepreciation', 'alphavantageDepreciationAndAmortization', 'alphavantageIncomeBeforeTax', 'alphavantageIncomeTaxExpense', 'alphavantageInterestAndDebtExpense', 'alphavantageNetIncomeFromContinuingOperations', 'alphavantageComprehensiveIncomeNetOfTax', 'alphavantageEbit', 'alphavantageEbitda', 'alphavantageNetIncome', 'alphavantageTotalAssets', 'alphavantageTotalCurrentAssets', 'alphavantageCashAndCashEquivalentsAtCarryingValue', 'alphavantageCashAndShortTermInvestments', 'alphavantageInventory', 'alphavantageCurrentNetReceivables', 'alphavantageTotalNonCurrentAssets', 'alphavantagePropertyPlantEquipment', 'alphavantageAccumulatedDepreciationAmortizationPPE', 'alphavantageIntangibleAssets', 'alphavantageIntangibleAssetsExcludingGoodwill', 'alphavantageGoodwill', 'alphavantageInvestments', 'alphavantageLongTermInvestments', 'alphavantageShortTermInvestments', 'alphavantageOtherCurrentAssets', 'alphavantageOtherNonCurrrentAssets', 'alphavantageTotalLiabilities', 'alphavantageTotalCurrentLiabilities', 'alphavantageCurrentAccountsPayable', 'alphavantageDeferredRevenue', 'alphavantageCurrentDebt', 'alphavantageShortTermDebt', 'alphavantageTotalNonCurrentLiabilities', 'alphavantageCapitalLeaseObligations', 'alphavantageLongTermDebt', 'alphavantageCurrentLongTermDebt', 'alphavantageLongTermDebtNoncurrent', 'alphavantageShortLongTermDebtTotal', 'alphavantageOtherCurrentLiabilities', 'alphavantageOtherNonCurrentLiabilities', 'alphavantageTotalShareholderEquity', 'alphavantageTreasuryStock', 'alphavantageRetainedEarnings', 'alphavantageCommonStock', 'alphavantageCommonStockSharesOutstanding', 'alphavantageOperatingCashflow', 'alphavantagePaymentsForOperatingActivities', 'alphavantageProceedsFromOperatingActivities', 'alphavantageChangeInOperatingLiabilities', 'alphavantageChangeInOperatingAssets', 'alphavantageDepreciationDepletionAndAmortization', 'alphavantageCapitalExpenditures', 'alphavantageChangeInReceivables', 'alphavantageChangeInInventory', 'alphavantageProfitLoss', 'alphavantageCashflowFromInvestment', 'alphavantageCashflowFromFinancing', 'alphavantageProceedsFromRepaymentsOfShortTermDebt', 'alphavantagePaymentsForRepurchaseOfCommonStock', 'alphavantagePaymentsForRepurchaseOfEquity', 'alphavantagePaymentsForRepurchaseOfPreferredStock', 'alphavantageDividendPayout', 'alphavantageDividendPayoutCommonStock', 'alphavantageDividendPayoutPreferredStock', 'alphavantageProceedsFromIssuanceOfCommonStock', 'alphavantageProceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet', 'alphavantageProceedsFromIssuanceOfPreferredStock', 'alphavantageProceedsFromRepurchaseOfEquity', 'alphavantageProceedsFromSaleOfTreasuryStock', 'alphavantageChangeInCashAndCashEquivalents', 'alphavantageChangeInExchangeRate', 'polygonLogo', 'polygonListdate', 'polygonCik', 'polygonBloomberg', 'polygonFigi', 'polygonLei', 'polygonSic', 'polygonCountry', 'polygonIndustry', 'polygonSector', 'polygonMarketcap', 'polygonEmployees', 'polygonPhone', 'polygonCeo', 'polygonUrl', 'polygonDescription', 'polygonName', 'polygonExchangeSymbol', 'polygonHqAddress', 'polygonHqState', 'polygonHqCountry', 'polygonType', 'polygonTags', 'polygonSimilar', 'polygonActive']
class StagingFinancialsRow():
	def __init__(self, exchangeValue: str, symbolValue: str, periodValue: str, calendarDateValue: str, polygonReportPeriodValue: str, polygonUpdatedValue: str, polygonDateKeyValue: str, polygonAccumulatedOtherComprehensiveIncomeValue: str, polygonAssetsValue: str, polygonAssetsAverageValue: str, polygonAssetsCurrentValue: str, polygonAssetsNonCurrentValue: str, polygonAssetTurnoverValue: str, polygonBookValuePerShareValue: str, polygonCapitalExpenditureValue: str, polygonCashAndEquivalentsValue: str, polygonCashAndEquivalentsUSDValue: str, polygonCostOfRevenueValue: str, polygonConsolidatedIncomeValue: str, polygonCurrentRatioValue: str, polygonDebtToEquityRatioValue: str, polygonDebtValue: str, polygonDebtCurrentValue: str, polygonDebtNonCurrentValue: str, polygonDebtUSDValue: str, polygonDeferredRevenueValue: str, polygonDepreciationAmortizationAndAccretionValue: str, polygonDepositsValue: str, polygonDividendYieldValue: str, polygonDividendsPerBasicCommonShareValue: str, polygonEarningBeforeInterestTaxesValue: str, polygonEarningsBeforeInterestTaxesDepreciationAmortizationValue: str, polygonEBITDAMarginValue: str, polygonEarningsBeforeInterestTaxesDepreciationAmortizationUSDValue: str, polygonEarningBeforeInterestTaxesUSDValue: str, polygonEarningsBeforeTaxValue: str, polygonEarningsPerBasicShareValue: str, polygonEarningsPerDilutedShareValue: str, polygonEarningsPerBasicShareUSDValue: str, polygonShareholdersEquityValue: str, polygonAverageEquityValue: str, polygonShareholdersEquityUSDValue: str, polygonEnterpriseValueValue: str, polygonEnterpriseValueOverEBITValue: str, polygonEnterpriseValueOverEBITDAValue: str, polygonFreeCashFlowValue: str, polygonFreeCashFlowPerShareValue: str, polygonForeignCurrencyUSDExchangeRateValue: str, polygonGrossProfitValue: str, polygonGrossMarginValue: str, polygonGoodwillAndIntangibleAssetsValue: str, polygonInterestExpenseValue: str, polygonInvestedCapitalValue: str, polygonInvestedCapitalAverageValue: str, polygonInventoryValue: str, polygonInvestmentsValue: str, polygonInvestmentsCurrentValue: str, polygonInvestmentsNonCurrentValue: str, polygonTotalLiabilitiesValue: str, polygonCurrentLiabilitiesValue: str, polygonLiabilitiesNonCurrentValue: str, polygonMarketCapitalizationValue: str, polygonNetCashFlowValue: str, polygonNetCashFlowBusinessAcquisitionsDisposalsValue: str, polygonIssuanceEquitySharesValue: str, polygonIssuanceDebtSecuritiesValue: str, polygonPaymentDividendsOtherCashDistributionsValue: str, polygonNetCashFlowFromFinancingValue: str, polygonNetCashFlowFromInvestingValue: str, polygonNetCashFlowInvestmentAcquisitionsDisposalsValue: str, polygonNetCashFlowFromOperationsValue: str, polygonEffectOfExchangeRateChangesOnCashValue: str, polygonNetIncomeValue: str, polygonNetIncomeCommonStockValue: str, polygonNetIncomeCommonStockUSDValue: str, polygonNetLossIncomeFromDiscontinuedOperationsValue: str, polygonNetIncomeToNonControllingInterestsValue: str, polygonProfitMarginValue: str, polygonOperatingExpensesValue: str, polygonOperatingIncomeValue: str, polygonTradeAndNonTradePayablesValue: str, polygonPayoutRatioValue: str, polygonPriceToBookValueValue: str, polygonPriceEarningsValue: str, polygonPriceToEarningsRatioValue: str, polygonPropertyPlantEquipmentNetValue: str, polygonPreferredDividendsIncomeStatementImpactValue: str, polygonSharePriceAdjustedCloseValue: str, polygonPriceSalesValue: str, polygonPriceToSalesRatioValue: str, polygonTradeAndNonTradeReceivablesValue: str, polygonAccumulatedRetainedEarningsDeficitValue: str, polygonRevenuesValue: str, polygonRevenuesUSDValue: str, polygonResearchAndDevelopmentExpenseValue: str, polygonReturnOnAverageAssetsValue: str, polygonReturnOnAverageEquityValue: str, polygonReturnOnInvestedCapitalValue: str, polygonReturnOnSalesValue: str, polygonShareBasedCompensationValue: str, polygonSellingGeneralAndAdministrativeExpenseValue: str, polygonShareFactorValue: str, polygonSharesValue: str, polygonWeightedAverageSharesValue: str, polygonSalesPerShareValue: str, polygonTangibleAssetValueValue: str, polygonTaxAssetsValue: str, polygonIncomeTaxExpenseValue: str, polygonTaxLiabilitiesValue: str, polygonTangibleAssetsBookValuePerShareValue: str, polygonWorkingCapitalValue: str, polygonWeightedAverageSharesDilutedValue: str, fmpValue: int, alphavantageValue: int, polygonValue: int, alphavantageFiscalDateEndingValue: str, alphavantageReportedCurrencyValue: str, alphavantageGrossProfitValue: str, alphavantageTotalRevenueValue: str, alphavantageCostOfRevenueValue: str, alphavantageCostofGoodsAndServicesSoldValue: str, alphavantageOperatingIncomeValue: str, alphavantageSellingGeneralAndAdministrativeValue: str, alphavantageResearchAndDevelopmentValue: str, alphavantageOperatingExpensesValue: str, alphavantageInvestmentIncomeNetValue: str, alphavantageNetInterestIncomeValue: str, alphavantageInterestIncomeValue: str, alphavantageInterestExpenseValue: str, alphavantageNonInterestIncomeValue: str, alphavantageOtherNonOperatingIncomeValue: str, alphavantageDepreciationValue: str, alphavantageDepreciationAndAmortizationValue: str, alphavantageIncomeBeforeTaxValue: str, alphavantageIncomeTaxExpenseValue: str, alphavantageInterestAndDebtExpenseValue: str, alphavantageNetIncomeFromContinuingOperationsValue: str, alphavantageComprehensiveIncomeNetOfTaxValue: str, alphavantageEbitValue: str, alphavantageEbitdaValue: str, alphavantageNetIncomeValue: str, alphavantageTotalAssetsValue: str, alphavantageTotalCurrentAssetsValue: str, alphavantageCashAndCashEquivalentsAtCarryingValueValue: str, alphavantageCashAndShortTermInvestmentsValue: str, alphavantageInventoryValue: str, alphavantageCurrentNetReceivablesValue: str, alphavantageTotalNonCurrentAssetsValue: str, alphavantagePropertyPlantEquipmentValue: str, alphavantageAccumulatedDepreciationAmortizationPPEValue: str, alphavantageIntangibleAssetsValue: str, alphavantageIntangibleAssetsExcludingGoodwillValue: str, alphavantageGoodwillValue: str, alphavantageInvestmentsValue: str, alphavantageLongTermInvestmentsValue: str, alphavantageShortTermInvestmentsValue: str, alphavantageOtherCurrentAssetsValue: str, alphavantageOtherNonCurrrentAssetsValue: str, alphavantageTotalLiabilitiesValue: str, alphavantageTotalCurrentLiabilitiesValue: str, alphavantageCurrentAccountsPayableValue: str, alphavantageDeferredRevenueValue: str, alphavantageCurrentDebtValue: str, alphavantageShortTermDebtValue: str, alphavantageTotalNonCurrentLiabilitiesValue: str, alphavantageCapitalLeaseObligationsValue: str, alphavantageLongTermDebtValue: str, alphavantageCurrentLongTermDebtValue: str, alphavantageLongTermDebtNoncurrentValue: str, alphavantageShortLongTermDebtTotalValue: str, alphavantageOtherCurrentLiabilitiesValue: str, alphavantageOtherNonCurrentLiabilitiesValue: str, alphavantageTotalShareholderEquityValue: str, alphavantageTreasuryStockValue: str, alphavantageRetainedEarningsValue: str, alphavantageCommonStockValue: str, alphavantageCommonStockSharesOutstandingValue: str, alphavantageOperatingCashflowValue: str, alphavantagePaymentsForOperatingActivitiesValue: str, alphavantageProceedsFromOperatingActivitiesValue: str, alphavantageChangeInOperatingLiabilitiesValue: str, alphavantageChangeInOperatingAssetsValue: str, alphavantageDepreciationDepletionAndAmortizationValue: str, alphavantageCapitalExpendituresValue: str, alphavantageChangeInReceivablesValue: str, alphavantageChangeInInventoryValue: str, alphavantageProfitLossValue: str, alphavantageCashflowFromInvestmentValue: str, alphavantageCashflowFromFinancingValue: str, alphavantageProceedsFromRepaymentsOfShortTermDebtValue: str, alphavantagePaymentsForRepurchaseOfCommonStockValue: str, alphavantagePaymentsForRepurchaseOfEquityValue: str, alphavantagePaymentsForRepurchaseOfPreferredStockValue: str, alphavantageDividendPayoutValue: str, alphavantageDividendPayoutCommonStockValue: str, alphavantageDividendPayoutPreferredStockValue: str, alphavantageProceedsFromIssuanceOfCommonStockValue: str, alphavantageProceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNetValue: str, alphavantageProceedsFromIssuanceOfPreferredStockValue: str, alphavantageProceedsFromRepurchaseOfEquityValue: str, alphavantageProceedsFromSaleOfTreasuryStockValue: str, alphavantageChangeInCashAndCashEquivalentsValue: str, alphavantageChangeInExchangeRateValue: str, polygonLogoValue: str, polygonListdateValue: str, polygonCikValue: str, polygonBloombergValue: str, polygonFigiValue: str, polygonLeiValue: str, polygonSicValue: str, polygonCountryValue: str, polygonIndustryValue: str, polygonSectorValue: str, polygonMarketcapValue: str, polygonEmployeesValue: str, polygonPhoneValue: str, polygonCeoValue: str, polygonUrlValue: str, polygonDescriptionValue: str, polygonNameValue: str, polygonExchangeSymbolValue: str, polygonHqAddressValue: str, polygonHqStateValue: str, polygonHqCountryValue: str, polygonTypeValue: str, polygonTagsValue: str, polygonSimilarValue: str, polygonActiveValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.period = periodValue
		self.calendarDate = calendarDateValue
		self.polygonReportPeriod = polygonReportPeriodValue
		self.polygonUpdated = polygonUpdatedValue
		self.polygonDateKey = polygonDateKeyValue
		self.polygonAccumulatedOtherComprehensiveIncome = polygonAccumulatedOtherComprehensiveIncomeValue
		self.polygonAssets = polygonAssetsValue
		self.polygonAssetsAverage = polygonAssetsAverageValue
		self.polygonAssetsCurrent = polygonAssetsCurrentValue
		self.polygonAssetsNonCurrent = polygonAssetsNonCurrentValue
		self.polygonAssetTurnover = polygonAssetTurnoverValue
		self.polygonBookValuePerShare = polygonBookValuePerShareValue
		self.polygonCapitalExpenditure = polygonCapitalExpenditureValue
		self.polygonCashAndEquivalents = polygonCashAndEquivalentsValue
		self.polygonCashAndEquivalentsUSD = polygonCashAndEquivalentsUSDValue
		self.polygonCostOfRevenue = polygonCostOfRevenueValue
		self.polygonConsolidatedIncome = polygonConsolidatedIncomeValue
		self.polygonCurrentRatio = polygonCurrentRatioValue
		self.polygonDebtToEquityRatio = polygonDebtToEquityRatioValue
		self.polygonDebt = polygonDebtValue
		self.polygonDebtCurrent = polygonDebtCurrentValue
		self.polygonDebtNonCurrent = polygonDebtNonCurrentValue
		self.polygonDebtUSD = polygonDebtUSDValue
		self.polygonDeferredRevenue = polygonDeferredRevenueValue
		self.polygonDepreciationAmortizationAndAccretion = polygonDepreciationAmortizationAndAccretionValue
		self.polygonDeposits = polygonDepositsValue
		self.polygonDividendYield = polygonDividendYieldValue
		self.polygonDividendsPerBasicCommonShare = polygonDividendsPerBasicCommonShareValue
		self.polygonEarningBeforeInterestTaxes = polygonEarningBeforeInterestTaxesValue
		self.polygonEarningsBeforeInterestTaxesDepreciationAmortization = polygonEarningsBeforeInterestTaxesDepreciationAmortizationValue
		self.polygonEBITDAMargin = polygonEBITDAMarginValue
		self.polygonEarningsBeforeInterestTaxesDepreciationAmortizationUSD = polygonEarningsBeforeInterestTaxesDepreciationAmortizationUSDValue
		self.polygonEarningBeforeInterestTaxesUSD = polygonEarningBeforeInterestTaxesUSDValue
		self.polygonEarningsBeforeTax = polygonEarningsBeforeTaxValue
		self.polygonEarningsPerBasicShare = polygonEarningsPerBasicShareValue
		self.polygonEarningsPerDilutedShare = polygonEarningsPerDilutedShareValue
		self.polygonEarningsPerBasicShareUSD = polygonEarningsPerBasicShareUSDValue
		self.polygonShareholdersEquity = polygonShareholdersEquityValue
		self.polygonAverageEquity = polygonAverageEquityValue
		self.polygonShareholdersEquityUSD = polygonShareholdersEquityUSDValue
		self.polygonEnterpriseValue = polygonEnterpriseValueValue
		self.polygonEnterpriseValueOverEBIT = polygonEnterpriseValueOverEBITValue
		self.polygonEnterpriseValueOverEBITDA = polygonEnterpriseValueOverEBITDAValue
		self.polygonFreeCashFlow = polygonFreeCashFlowValue
		self.polygonFreeCashFlowPerShare = polygonFreeCashFlowPerShareValue
		self.polygonForeignCurrencyUSDExchangeRate = polygonForeignCurrencyUSDExchangeRateValue
		self.polygonGrossProfit = polygonGrossProfitValue
		self.polygonGrossMargin = polygonGrossMarginValue
		self.polygonGoodwillAndIntangibleAssets = polygonGoodwillAndIntangibleAssetsValue
		self.polygonInterestExpense = polygonInterestExpenseValue
		self.polygonInvestedCapital = polygonInvestedCapitalValue
		self.polygonInvestedCapitalAverage = polygonInvestedCapitalAverageValue
		self.polygonInventory = polygonInventoryValue
		self.polygonInvestments = polygonInvestmentsValue
		self.polygonInvestmentsCurrent = polygonInvestmentsCurrentValue
		self.polygonInvestmentsNonCurrent = polygonInvestmentsNonCurrentValue
		self.polygonTotalLiabilities = polygonTotalLiabilitiesValue
		self.polygonCurrentLiabilities = polygonCurrentLiabilitiesValue
		self.polygonLiabilitiesNonCurrent = polygonLiabilitiesNonCurrentValue
		self.polygonMarketCapitalization = polygonMarketCapitalizationValue
		self.polygonNetCashFlow = polygonNetCashFlowValue
		self.polygonNetCashFlowBusinessAcquisitionsDisposals = polygonNetCashFlowBusinessAcquisitionsDisposalsValue
		self.polygonIssuanceEquityShares = polygonIssuanceEquitySharesValue
		self.polygonIssuanceDebtSecurities = polygonIssuanceDebtSecuritiesValue
		self.polygonPaymentDividendsOtherCashDistributions = polygonPaymentDividendsOtherCashDistributionsValue
		self.polygonNetCashFlowFromFinancing = polygonNetCashFlowFromFinancingValue
		self.polygonNetCashFlowFromInvesting = polygonNetCashFlowFromInvestingValue
		self.polygonNetCashFlowInvestmentAcquisitionsDisposals = polygonNetCashFlowInvestmentAcquisitionsDisposalsValue
		self.polygonNetCashFlowFromOperations = polygonNetCashFlowFromOperationsValue
		self.polygonEffectOfExchangeRateChangesOnCash = polygonEffectOfExchangeRateChangesOnCashValue
		self.polygonNetIncome = polygonNetIncomeValue
		self.polygonNetIncomeCommonStock = polygonNetIncomeCommonStockValue
		self.polygonNetIncomeCommonStockUSD = polygonNetIncomeCommonStockUSDValue
		self.polygonNetLossIncomeFromDiscontinuedOperations = polygonNetLossIncomeFromDiscontinuedOperationsValue
		self.polygonNetIncomeToNonControllingInterests = polygonNetIncomeToNonControllingInterestsValue
		self.polygonProfitMargin = polygonProfitMarginValue
		self.polygonOperatingExpenses = polygonOperatingExpensesValue
		self.polygonOperatingIncome = polygonOperatingIncomeValue
		self.polygonTradeAndNonTradePayables = polygonTradeAndNonTradePayablesValue
		self.polygonPayoutRatio = polygonPayoutRatioValue
		self.polygonPriceToBookValue = polygonPriceToBookValueValue
		self.polygonPriceEarnings = polygonPriceEarningsValue
		self.polygonPriceToEarningsRatio = polygonPriceToEarningsRatioValue
		self.polygonPropertyPlantEquipmentNet = polygonPropertyPlantEquipmentNetValue
		self.polygonPreferredDividendsIncomeStatementImpact = polygonPreferredDividendsIncomeStatementImpactValue
		self.polygonSharePriceAdjustedClose = polygonSharePriceAdjustedCloseValue
		self.polygonPriceSales = polygonPriceSalesValue
		self.polygonPriceToSalesRatio = polygonPriceToSalesRatioValue
		self.polygonTradeAndNonTradeReceivables = polygonTradeAndNonTradeReceivablesValue
		self.polygonAccumulatedRetainedEarningsDeficit = polygonAccumulatedRetainedEarningsDeficitValue
		self.polygonRevenues = polygonRevenuesValue
		self.polygonRevenuesUSD = polygonRevenuesUSDValue
		self.polygonResearchAndDevelopmentExpense = polygonResearchAndDevelopmentExpenseValue
		self.polygonReturnOnAverageAssets = polygonReturnOnAverageAssetsValue
		self.polygonReturnOnAverageEquity = polygonReturnOnAverageEquityValue
		self.polygonReturnOnInvestedCapital = polygonReturnOnInvestedCapitalValue
		self.polygonReturnOnSales = polygonReturnOnSalesValue
		self.polygonShareBasedCompensation = polygonShareBasedCompensationValue
		self.polygonSellingGeneralAndAdministrativeExpense = polygonSellingGeneralAndAdministrativeExpenseValue
		self.polygonShareFactor = polygonShareFactorValue
		self.polygonShares = polygonSharesValue
		self.polygonWeightedAverageShares = polygonWeightedAverageSharesValue
		self.polygonSalesPerShare = polygonSalesPerShareValue
		self.polygonTangibleAssetValue = polygonTangibleAssetValueValue
		self.polygonTaxAssets = polygonTaxAssetsValue
		self.polygonIncomeTaxExpense = polygonIncomeTaxExpenseValue
		self.polygonTaxLiabilities = polygonTaxLiabilitiesValue
		self.polygonTangibleAssetsBookValuePerShare = polygonTangibleAssetsBookValuePerShareValue
		self.polygonWorkingCapital = polygonWorkingCapitalValue
		self.polygonWeightedAverageSharesDiluted = polygonWeightedAverageSharesDilutedValue
		self.fmp = fmpValue
		self.alphavantage = alphavantageValue
		self.polygon = polygonValue
		self.alphavantageFiscalDateEnding = alphavantageFiscalDateEndingValue
		self.alphavantageReportedCurrency = alphavantageReportedCurrencyValue
		self.alphavantageGrossProfit = alphavantageGrossProfitValue
		self.alphavantageTotalRevenue = alphavantageTotalRevenueValue
		self.alphavantageCostOfRevenue = alphavantageCostOfRevenueValue
		self.alphavantageCostofGoodsAndServicesSold = alphavantageCostofGoodsAndServicesSoldValue
		self.alphavantageOperatingIncome = alphavantageOperatingIncomeValue
		self.alphavantageSellingGeneralAndAdministrative = alphavantageSellingGeneralAndAdministrativeValue
		self.alphavantageResearchAndDevelopment = alphavantageResearchAndDevelopmentValue
		self.alphavantageOperatingExpenses = alphavantageOperatingExpensesValue
		self.alphavantageInvestmentIncomeNet = alphavantageInvestmentIncomeNetValue
		self.alphavantageNetInterestIncome = alphavantageNetInterestIncomeValue
		self.alphavantageInterestIncome = alphavantageInterestIncomeValue
		self.alphavantageInterestExpense = alphavantageInterestExpenseValue
		self.alphavantageNonInterestIncome = alphavantageNonInterestIncomeValue
		self.alphavantageOtherNonOperatingIncome = alphavantageOtherNonOperatingIncomeValue
		self.alphavantageDepreciation = alphavantageDepreciationValue
		self.alphavantageDepreciationAndAmortization = alphavantageDepreciationAndAmortizationValue
		self.alphavantageIncomeBeforeTax = alphavantageIncomeBeforeTaxValue
		self.alphavantageIncomeTaxExpense = alphavantageIncomeTaxExpenseValue
		self.alphavantageInterestAndDebtExpense = alphavantageInterestAndDebtExpenseValue
		self.alphavantageNetIncomeFromContinuingOperations = alphavantageNetIncomeFromContinuingOperationsValue
		self.alphavantageComprehensiveIncomeNetOfTax = alphavantageComprehensiveIncomeNetOfTaxValue
		self.alphavantageEbit = alphavantageEbitValue
		self.alphavantageEbitda = alphavantageEbitdaValue
		self.alphavantageNetIncome = alphavantageNetIncomeValue
		self.alphavantageTotalAssets = alphavantageTotalAssetsValue
		self.alphavantageTotalCurrentAssets = alphavantageTotalCurrentAssetsValue
		self.alphavantageCashAndCashEquivalentsAtCarryingValue = alphavantageCashAndCashEquivalentsAtCarryingValueValue
		self.alphavantageCashAndShortTermInvestments = alphavantageCashAndShortTermInvestmentsValue
		self.alphavantageInventory = alphavantageInventoryValue
		self.alphavantageCurrentNetReceivables = alphavantageCurrentNetReceivablesValue
		self.alphavantageTotalNonCurrentAssets = alphavantageTotalNonCurrentAssetsValue
		self.alphavantagePropertyPlantEquipment = alphavantagePropertyPlantEquipmentValue
		self.alphavantageAccumulatedDepreciationAmortizationPPE = alphavantageAccumulatedDepreciationAmortizationPPEValue
		self.alphavantageIntangibleAssets = alphavantageIntangibleAssetsValue
		self.alphavantageIntangibleAssetsExcludingGoodwill = alphavantageIntangibleAssetsExcludingGoodwillValue
		self.alphavantageGoodwill = alphavantageGoodwillValue
		self.alphavantageInvestments = alphavantageInvestmentsValue
		self.alphavantageLongTermInvestments = alphavantageLongTermInvestmentsValue
		self.alphavantageShortTermInvestments = alphavantageShortTermInvestmentsValue
		self.alphavantageOtherCurrentAssets = alphavantageOtherCurrentAssetsValue
		self.alphavantageOtherNonCurrrentAssets = alphavantageOtherNonCurrrentAssetsValue
		self.alphavantageTotalLiabilities = alphavantageTotalLiabilitiesValue
		self.alphavantageTotalCurrentLiabilities = alphavantageTotalCurrentLiabilitiesValue
		self.alphavantageCurrentAccountsPayable = alphavantageCurrentAccountsPayableValue
		self.alphavantageDeferredRevenue = alphavantageDeferredRevenueValue
		self.alphavantageCurrentDebt = alphavantageCurrentDebtValue
		self.alphavantageShortTermDebt = alphavantageShortTermDebtValue
		self.alphavantageTotalNonCurrentLiabilities = alphavantageTotalNonCurrentLiabilitiesValue
		self.alphavantageCapitalLeaseObligations = alphavantageCapitalLeaseObligationsValue
		self.alphavantageLongTermDebt = alphavantageLongTermDebtValue
		self.alphavantageCurrentLongTermDebt = alphavantageCurrentLongTermDebtValue
		self.alphavantageLongTermDebtNoncurrent = alphavantageLongTermDebtNoncurrentValue
		self.alphavantageShortLongTermDebtTotal = alphavantageShortLongTermDebtTotalValue
		self.alphavantageOtherCurrentLiabilities = alphavantageOtherCurrentLiabilitiesValue
		self.alphavantageOtherNonCurrentLiabilities = alphavantageOtherNonCurrentLiabilitiesValue
		self.alphavantageTotalShareholderEquity = alphavantageTotalShareholderEquityValue
		self.alphavantageTreasuryStock = alphavantageTreasuryStockValue
		self.alphavantageRetainedEarnings = alphavantageRetainedEarningsValue
		self.alphavantageCommonStock = alphavantageCommonStockValue
		self.alphavantageCommonStockSharesOutstanding = alphavantageCommonStockSharesOutstandingValue
		self.alphavantageOperatingCashflow = alphavantageOperatingCashflowValue
		self.alphavantagePaymentsForOperatingActivities = alphavantagePaymentsForOperatingActivitiesValue
		self.alphavantageProceedsFromOperatingActivities = alphavantageProceedsFromOperatingActivitiesValue
		self.alphavantageChangeInOperatingLiabilities = alphavantageChangeInOperatingLiabilitiesValue
		self.alphavantageChangeInOperatingAssets = alphavantageChangeInOperatingAssetsValue
		self.alphavantageDepreciationDepletionAndAmortization = alphavantageDepreciationDepletionAndAmortizationValue
		self.alphavantageCapitalExpenditures = alphavantageCapitalExpendituresValue
		self.alphavantageChangeInReceivables = alphavantageChangeInReceivablesValue
		self.alphavantageChangeInInventory = alphavantageChangeInInventoryValue
		self.alphavantageProfitLoss = alphavantageProfitLossValue
		self.alphavantageCashflowFromInvestment = alphavantageCashflowFromInvestmentValue
		self.alphavantageCashflowFromFinancing = alphavantageCashflowFromFinancingValue
		self.alphavantageProceedsFromRepaymentsOfShortTermDebt = alphavantageProceedsFromRepaymentsOfShortTermDebtValue
		self.alphavantagePaymentsForRepurchaseOfCommonStock = alphavantagePaymentsForRepurchaseOfCommonStockValue
		self.alphavantagePaymentsForRepurchaseOfEquity = alphavantagePaymentsForRepurchaseOfEquityValue
		self.alphavantagePaymentsForRepurchaseOfPreferredStock = alphavantagePaymentsForRepurchaseOfPreferredStockValue
		self.alphavantageDividendPayout = alphavantageDividendPayoutValue
		self.alphavantageDividendPayoutCommonStock = alphavantageDividendPayoutCommonStockValue
		self.alphavantageDividendPayoutPreferredStock = alphavantageDividendPayoutPreferredStockValue
		self.alphavantageProceedsFromIssuanceOfCommonStock = alphavantageProceedsFromIssuanceOfCommonStockValue
		self.alphavantageProceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet = alphavantageProceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNetValue
		self.alphavantageProceedsFromIssuanceOfPreferredStock = alphavantageProceedsFromIssuanceOfPreferredStockValue
		self.alphavantageProceedsFromRepurchaseOfEquity = alphavantageProceedsFromRepurchaseOfEquityValue
		self.alphavantageProceedsFromSaleOfTreasuryStock = alphavantageProceedsFromSaleOfTreasuryStockValue
		self.alphavantageChangeInCashAndCashEquivalents = alphavantageChangeInCashAndCashEquivalentsValue
		self.alphavantageChangeInExchangeRate = alphavantageChangeInExchangeRateValue
		self.polygonLogo = polygonLogoValue
		self.polygonListdate = polygonListdateValue
		self.polygonCik = polygonCikValue
		self.polygonBloomberg = polygonBloombergValue
		self.polygonFigi = polygonFigiValue
		self.polygonLei = polygonLeiValue
		self.polygonSic = polygonSicValue
		self.polygonCountry = polygonCountryValue
		self.polygonIndustry = polygonIndustryValue
		self.polygonSector = polygonSectorValue
		self.polygonMarketcap = polygonMarketcapValue
		self.polygonEmployees = polygonEmployeesValue
		self.polygonPhone = polygonPhoneValue
		self.polygonCeo = polygonCeoValue
		self.polygonUrl = polygonUrlValue
		self.polygonDescription = polygonDescriptionValue
		self.polygonName = polygonNameValue
		self.polygonExchangeSymbol = polygonExchangeSymbolValue
		self.polygonHqAddress = polygonHqAddressValue
		self.polygonHqState = polygonHqStateValue
		self.polygonHqCountry = polygonHqCountryValue
		self.polygonType = polygonTypeValue
		self.polygonTags = polygonTagsValue
		self.polygonSimilar = polygonSimilarValue
		self.polygonActive = polygonActiveValue

## TABLE: dump_nasdaq_earnings_dates ######################################
dumpNasdaqEarningsDatesSnakeCaseTableColumns = ['symbol', 'input_date', 'earnings_date', 'eps', 'surprise_percentage', 'time', 'name', 'last_year_report_date', 'last_year_eps', 'market_cap', 'fiscal_quarter_ending', 'eps_forecast', 'number_of_estimates']
dumpNasdaqEarningsDatesCamelCaseTableColumns = ['symbol', 'inputDate', 'earningsDate', 'eps', 'surprisePercentage', 'time', 'name', 'lastYearReportDate', 'lastYearEps', 'marketCap', 'fiscalQuarterEnding', 'epsForecast', 'numberOfEstimates']
class DumpNasdaqEarningsDatesRow():
	def __init__(self, symbolValue: str, inputDateValue: str, earningsDateValue: str, epsValue: float, surprisePercentageValue: float, timeValue: str, nameValue: str, lastYearReportDateValue: str, lastYearEpsValue: int, marketCapValue: int, fiscalQuarterEndingValue: str, epsForecastValue: str, numberOfEstimatesValue: int):
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.eps = epsValue
		self.surprisePercentage = surprisePercentageValue
		self.time = timeValue
		self.name = nameValue
		self.lastYearReportDate = lastYearReportDateValue
		self.lastYearEps = lastYearEpsValue
		self.marketCap = marketCapValue
		self.fiscalQuarterEnding = fiscalQuarterEndingValue
		self.epsForecast = epsForecastValue
		self.numberOfEstimates = numberOfEstimatesValue

## TABLE: staging_earnings_dates ######################################
stagingEarningsDatesSnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'earnings_date', 'nasdaq_eps', 'nasdaq_surprise_percentage', 'nasdaq_time', 'nasdaq_name', 'nasdaq_last_year_report_date', 'nasdaq_last_year_eps', 'nasdaq_market_cap', 'nasdaq_fiscal_quarter_ending', 'nasdaq_eps_forecast', 'nasdaq_number_of_estimates', 'yahoo_name', 'yahoo_event_name', 'yahoo_eps_forecast', 'yahoo_eps', 'yahoo_surprise_percentage', 'yahoo_start_date_time', 'yahoo_start_date_time_type', 'yahoo_time_zone_short_name', 'yahoo_gmt_offset_milli_seconds', 'marketwatch_name', 'marketwatch_fiscal_quarter_ending', 'marketwatch_eps_forecast', 'marketwatch_eps', 'marketwatch_surprise_percentage']
stagingEarningsDatesCamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'earningsDate', 'nasdaqEps', 'nasdaqSurprisePercentage', 'nasdaqTime', 'nasdaqName', 'nasdaqLastYearReportDate', 'nasdaqLastYearEps', 'nasdaqMarketCap', 'nasdaqFiscalQuarterEnding', 'nasdaqEpsForecast', 'nasdaqNumberOfEstimates', 'yahooName', 'yahooEventName', 'yahooEpsForecast', 'yahooEps', 'yahooSurprisePercentage', 'yahooStartDateTime', 'yahooStartDateTimeType', 'yahooTimeZoneShortName', 'yahooGmtOffsetMilliSeconds', 'marketwatchName', 'marketwatchFiscalQuarterEnding', 'marketwatchEpsForecast', 'marketwatchEps', 'marketwatchSurprisePercentage']
class StagingEarningsDatesRow():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, earningsDateValue: str, nasdaqEpsValue: float, nasdaqSurprisePercentageValue: float, nasdaqTimeValue: str, nasdaqNameValue: str, nasdaqLastYearReportDateValue: str, nasdaqLastYearEpsValue: int, nasdaqMarketCapValue: int, nasdaqFiscalQuarterEndingValue: str, nasdaqEpsForecastValue: str, nasdaqNumberOfEstimatesValue: int, yahooNameValue: str, yahooEventNameValue: str, yahooEpsForecastValue: str, yahooEpsValue: float, yahooSurprisePercentageValue: float, yahooStartDateTimeValue: str, yahooStartDateTimeTypeValue: str, yahooTimeZoneShortNameValue: str, yahooGmtOffsetMilliSecondsValue: float, marketwatchNameValue: str, marketwatchFiscalQuarterEndingValue: str, marketwatchEpsForecastValue: float, marketwatchEpsValue: float, marketwatchSurprisePercentageValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.nasdaqEps = nasdaqEpsValue
		self.nasdaqSurprisePercentage = nasdaqSurprisePercentageValue
		self.nasdaqTime = nasdaqTimeValue
		self.nasdaqName = nasdaqNameValue
		self.nasdaqLastYearReportDate = nasdaqLastYearReportDateValue
		self.nasdaqLastYearEps = nasdaqLastYearEpsValue
		self.nasdaqMarketCap = nasdaqMarketCapValue
		self.nasdaqFiscalQuarterEnding = nasdaqFiscalQuarterEndingValue
		self.nasdaqEpsForecast = nasdaqEpsForecastValue
		self.nasdaqNumberOfEstimates = nasdaqNumberOfEstimatesValue
		self.yahooName = yahooNameValue
		self.yahooEventName = yahooEventNameValue
		self.yahooEpsForecast = yahooEpsForecastValue
		self.yahooEps = yahooEpsValue
		self.yahooSurprisePercentage = yahooSurprisePercentageValue
		self.yahooStartDateTime = yahooStartDateTimeValue
		self.yahooStartDateTimeType = yahooStartDateTimeTypeValue
		self.yahooTimeZoneShortName = yahooTimeZoneShortNameValue
		self.yahooGmtOffsetMilliSeconds = yahooGmtOffsetMilliSecondsValue
		self.marketwatchName = marketwatchNameValue
		self.marketwatchFiscalQuarterEnding = marketwatchFiscalQuarterEndingValue
		self.marketwatchEpsForecast = marketwatchEpsForecastValue
		self.marketwatchEps = marketwatchEpsValue
		self.marketwatchSurprisePercentage = marketwatchSurprisePercentageValue

## TABLE: dump_symbol_info_yahoo ######################################
dumpSymbolInfoYahooSnakeCaseTableColumns = ['exchange', 'symbol', 'quote_type', 'short_name', 'long_name', 'message_board_id', 'exchange_timezone_name', 'exchange_timezone_short_name', 'gmt_off_set_milliseconds', 'market', 'is_esg_populated']
dumpSymbolInfoYahooCamelCaseTableColumns = ['exchange', 'symbol', 'quoteType', 'shortName', 'longName', 'messageBoardId', 'exchangeTimezoneName', 'exchangeTimezoneShortName', 'gmtOffSetMilliseconds', 'market', 'isEsgPopulated']
class DumpSymbolInfoYahooRow():
	def __init__(self, exchangeValue: str, symbolValue: str, quoteTypeValue: str, shortNameValue: str, longNameValue: str, messageBoardIdValue: str, exchangeTimezoneNameValue: str, exchangeTimezoneShortNameValue: str, gmtOffSetMillisecondsValue: float, marketValue: str, isEsgPopulatedValue):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.quoteType = quoteTypeValue
		self.shortName = shortNameValue
		self.longName = longNameValue
		self.messageBoardId = messageBoardIdValue
		self.exchangeTimezoneName = exchangeTimezoneNameValue
		self.exchangeTimezoneShortName = exchangeTimezoneShortNameValue
		self.gmtOffSetMilliseconds = gmtOffSetMillisecondsValue
		self.market = marketValue
		self.isEsgPopulated = isEsgPopulatedValue

## TABLE: staging_earnings_dates_bk ######################################
stagingEarningsDatesBkSnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'earnings_date', 'nasdaq_eps', 'nasdaq_surprise_percentage', 'nasdaq_time', 'nasdaq_name', 'nasdaq_last_year_report_date', 'nasdaq_last_year_eps', 'nasdaq_market_cap', 'nasdaq_fiscal_quarter_ending', 'nasdaq_eps_forecast', 'nasdaq_number_of_estimates', 'yahoo_name', 'yahoo_event_name', 'yahoo_eps_forecast', 'yahoo_eps', 'yahoo_surprise_percentage', 'yahoo_start_date_time', 'yahoo_start_date_time_type', 'yahoo_time_zone_short_name', 'yahoo_gmt_offset_milli_seconds', 'marketwatch_name', 'marketwatch_fiscal_quarter_ending', 'marketwatch_eps_forecast', 'marketwatch_eps', 'marketwatch_surprise_percentage']
stagingEarningsDatesBkCamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'earningsDate', 'nasdaqEps', 'nasdaqSurprisePercentage', 'nasdaqTime', 'nasdaqName', 'nasdaqLastYearReportDate', 'nasdaqLastYearEps', 'nasdaqMarketCap', 'nasdaqFiscalQuarterEnding', 'nasdaqEpsForecast', 'nasdaqNumberOfEstimates', 'yahooName', 'yahooEventName', 'yahooEpsForecast', 'yahooEps', 'yahooSurprisePercentage', 'yahooStartDateTime', 'yahooStartDateTimeType', 'yahooTimeZoneShortName', 'yahooGmtOffsetMilliSeconds', 'marketwatchName', 'marketwatchFiscalQuarterEnding', 'marketwatchEpsForecast', 'marketwatchEps', 'marketwatchSurprisePercentage']
class StagingEarningsDatesBkRow():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, earningsDateValue: str, nasdaqEpsValue: float, nasdaqSurprisePercentageValue: float, nasdaqTimeValue: str, nasdaqNameValue: str, nasdaqLastYearReportDateValue: str, nasdaqLastYearEpsValue: int, nasdaqMarketCapValue: int, nasdaqFiscalQuarterEndingValue: str, nasdaqEpsForecastValue: str, nasdaqNumberOfEstimatesValue: int, yahooNameValue: str, yahooEventNameValue: str, yahooEpsForecastValue: str, yahooEpsValue: float, yahooSurprisePercentageValue: float, yahooStartDateTimeValue: str, yahooStartDateTimeTypeValue: str, yahooTimeZoneShortNameValue: str, yahooGmtOffsetMilliSecondsValue: float, marketwatchNameValue: str, marketwatchFiscalQuarterEndingValue: str, marketwatchEpsForecastValue: float, marketwatchEpsValue: float, marketwatchSurprisePercentageValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.nasdaqEps = nasdaqEpsValue
		self.nasdaqSurprisePercentage = nasdaqSurprisePercentageValue
		self.nasdaqTime = nasdaqTimeValue
		self.nasdaqName = nasdaqNameValue
		self.nasdaqLastYearReportDate = nasdaqLastYearReportDateValue
		self.nasdaqLastYearEps = nasdaqLastYearEpsValue
		self.nasdaqMarketCap = nasdaqMarketCapValue
		self.nasdaqFiscalQuarterEnding = nasdaqFiscalQuarterEndingValue
		self.nasdaqEpsForecast = nasdaqEpsForecastValue
		self.nasdaqNumberOfEstimates = nasdaqNumberOfEstimatesValue
		self.yahooName = yahooNameValue
		self.yahooEventName = yahooEventNameValue
		self.yahooEpsForecast = yahooEpsForecastValue
		self.yahooEps = yahooEpsValue
		self.yahooSurprisePercentage = yahooSurprisePercentageValue
		self.yahooStartDateTime = yahooStartDateTimeValue
		self.yahooStartDateTimeType = yahooStartDateTimeTypeValue
		self.yahooTimeZoneShortName = yahooTimeZoneShortNameValue
		self.yahooGmtOffsetMilliSeconds = yahooGmtOffsetMilliSecondsValue
		self.marketwatchName = marketwatchNameValue
		self.marketwatchFiscalQuarterEnding = marketwatchFiscalQuarterEndingValue
		self.marketwatchEpsForecast = marketwatchEpsForecastValue
		self.marketwatchEps = marketwatchEpsValue
		self.marketwatchSurprisePercentage = marketwatchSurprisePercentageValue

## TABLE: dump_symbol_statistics_yahoo ######################################
dumpSymbolStatisticsYahooSnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'quote_type', 'currency', 'shares_outstanding', 'market_cap', 'full_exchange_name', 'first_trade_date_milliseconds', 'tradeable', 'crypto_tradeable']
dumpSymbolStatisticsYahooCamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'quoteType', 'currency', 'sharesOutstanding', 'marketCap', 'fullExchangeName', 'firstTradeDateMilliseconds', 'tradeable', 'cryptoTradeable']
class DumpSymbolStatisticsYahooRow():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, quoteTypeValue: str, currencyValue: str, sharesOutstandingValue: int, marketCapValue: int, fullExchangeNameValue: str, firstTradeDateMillisecondsValue: int, tradeableValue: bool, cryptoTradeableValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.quoteType = quoteTypeValue
		self.currency = currencyValue
		self.sharesOutstanding = sharesOutstandingValue
		self.marketCap = marketCapValue
		self.fullExchangeName = fullExchangeNameValue
		self.firstTradeDateMilliseconds = firstTradeDateMillisecondsValue
		self.tradeable = tradeableValue
		self.cryptoTradeable = cryptoTradeableValue

## TABLE: dump_short_interest_finra ######################################
dumpShortInterestFinraSnakeCaseTableColumns = ['market_class_code', 'symbol_code', 'settlement_date', 'revision_flag', 'issue_name', 'current_short_position_quantity', 'days_to_cover_quantity', 'previous_short_position_quantity', 'issuer_services_group_exchange_code', 'stock_split_flag']
dumpShortInterestFinraCamelCaseTableColumns = ['marketClassCode', 'symbolCode', 'settlementDate', 'revisionFlag', 'issueName', 'currentShortPositionQuantity', 'daysToCoverQuantity', 'previousShortPositionQuantity', 'issuerServicesGroupExchangeCode', 'stockSplitFlag']
class DumpShortInterestFinraRow():
	def __init__(self, marketClassCodeValue: str, symbolCodeValue: str, settlementDateValue: str, revisionFlagValue: float, issueNameValue: str, currentShortPositionQuantityValue: int, daysToCoverQuantityValue: int, previousShortPositionQuantityValue: int, issuerServicesGroupExchangeCodeValue: str, stockSplitFlagValue: float):
		self.marketClassCode = marketClassCodeValue
		self.symbolCode = symbolCodeValue
		self.settlementDate = settlementDateValue
		self.revisionFlag = revisionFlagValue
		self.issueName = issueNameValue
		self.currentShortPositionQuantity = currentShortPositionQuantityValue
		self.daysToCoverQuantity = daysToCoverQuantityValue
		self.previousShortPositionQuantity = previousShortPositionQuantityValue
		self.issuerServicesGroupExchangeCode = issuerServicesGroupExchangeCodeValue
		self.stockSplitFlag = stockSplitFlagValue

## TABLE: dump_yahoo_earnings_dates_bk ######################################
dumpYahooEarningsDatesBkSnakeCaseTableColumns = ['symbol', 'input_date', 'earnings_date', 'name', 'event_name', 'eps_forecast', 'earnings_per_share', 'surprise_percentage', 'start_date_time', 'start_date_time_type', 'time_zone_short_name', 'gmt_offset_milli_seconds']
dumpYahooEarningsDatesBkCamelCaseTableColumns = ['symbol', 'inputDate', 'earningsDate', 'name', 'eventName', 'epsForecast', 'earningsPerShare', 'surprisePercentage', 'startDateTime', 'startDateTimeType', 'timeZoneShortName', 'gmtOffsetMilliSeconds']
class DumpYahooEarningsDatesBkRow():
	def __init__(self, symbolValue: str, inputDateValue: str, earningsDateValue: str, nameValue: str, eventNameValue: str, epsForecastValue: str, earningsPerShareValue: float, surprisePercentageValue: float, startDateTimeValue: str, startDateTimeTypeValue: str, timeZoneShortNameValue: str, gmtOffsetMilliSecondsValue: float):
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.name = nameValue
		self.eventName = eventNameValue
		self.epsForecast = epsForecastValue
		self.earningsPerShare = earningsPerShareValue
		self.surprisePercentage = surprisePercentageValue
		self.startDateTime = startDateTimeValue
		self.startDateTimeType = startDateTimeTypeValue
		self.timeZoneShortName = timeZoneShortNameValue
		self.gmtOffsetMilliSeconds = gmtOffsetMilliSecondsValue

## TABLE: dump_nasdaq_earnings_dates_bk ######################################
dumpNasdaqEarningsDatesBkSnakeCaseTableColumns = ['symbol', 'input_date', 'earnings_date', 'earnings_per_share', 'surprise_percentage', 'time', 'name', 'last_year_report_date', 'last_year_eps', 'market_cap', 'fiscal_quarter_ending', 'eps_forecast', 'number_of_estimates']
dumpNasdaqEarningsDatesBkCamelCaseTableColumns = ['symbol', 'inputDate', 'earningsDate', 'earningsPerShare', 'surprisePercentage', 'time', 'name', 'lastYearReportDate', 'lastYearEps', 'marketCap', 'fiscalQuarterEnding', 'epsForecast', 'numberOfEstimates']
class DumpNasdaqEarningsDatesBkRow():
	def __init__(self, symbolValue: str, inputDateValue: str, earningsDateValue: str, earningsPerShareValue: float, surprisePercentageValue: float, timeValue: str, nameValue: str, lastYearReportDateValue: str, lastYearEpsValue: int, marketCapValue: int, fiscalQuarterEndingValue: str, epsForecastValue: str, numberOfEstimatesValue: int):
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.earningsPerShare = earningsPerShareValue
		self.surprisePercentage = surprisePercentageValue
		self.time = timeValue
		self.name = nameValue
		self.lastYearReportDate = lastYearReportDateValue
		self.lastYearEps = lastYearEpsValue
		self.marketCap = marketCapValue
		self.fiscalQuarterEnding = fiscalQuarterEndingValue
		self.epsForecast = epsForecastValue
		self.numberOfEstimates = numberOfEstimatesValue

## TABLE: dump_marketwatch_earnings_dates_bk ######################################
dumpMarketwatchEarningsDatesBkSnakeCaseTableColumns = ['symbol', 'input_date', 'earnings_date', 'name', 'fiscal_quarter_ending', 'eps_forecast', 'earnings_per_share', 'surprise_percentage']
dumpMarketwatchEarningsDatesBkCamelCaseTableColumns = ['symbol', 'inputDate', 'earningsDate', 'name', 'fiscalQuarterEnding', 'epsForecast', 'earningsPerShare', 'surprisePercentage']
class DumpMarketwatchEarningsDatesBkRow():
	def __init__(self, symbolValue: str, inputDateValue: str, earningsDateValue: str, nameValue: str, fiscalQuarterEndingValue: str, epsForecastValue: str, earningsPerShareValue: float, surprisePercentageValue: float):
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.name = nameValue
		self.fiscalQuarterEnding = fiscalQuarterEndingValue
		self.epsForecast = epsForecastValue
		self.earningsPerShare = earningsPerShareValue
		self.surprisePercentage = surprisePercentageValue

## TABLE: staging_earnings_dates_bk_20230722 ######################################
stagingEarningsDatesBk20230722SnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'earnings_date', 'nasdaq_eps', 'nasdaq_surprise_percentage', 'nasdaq_time', 'nasdaq_name', 'nasdaq_last_year_report_date', 'nasdaq_last_year_eps', 'nasdaq_market_cap', 'nasdaq_fiscal_quarter_ending', 'nasdaq_eps_forecast', 'nasdaq_number_of_estimates', 'yahoo_name', 'yahoo_event_name', 'yahoo_eps_forecast', 'yahoo_eps', 'yahoo_surprise_percentage', 'yahoo_start_date_time', 'yahoo_start_date_time_type', 'yahoo_time_zone_short_name', 'yahoo_gmt_offset_milli_seconds', 'marketwatch_name', 'marketwatch_fiscal_quarter_ending', 'marketwatch_eps_forecast', 'marketwatch_eps', 'marketwatch_surprise_percentage']
stagingEarningsDatesBk20230722CamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'earningsDate', 'nasdaqEps', 'nasdaqSurprisePercentage', 'nasdaqTime', 'nasdaqName', 'nasdaqLastYearReportDate', 'nasdaqLastYearEps', 'nasdaqMarketCap', 'nasdaqFiscalQuarterEnding', 'nasdaqEpsForecast', 'nasdaqNumberOfEstimates', 'yahooName', 'yahooEventName', 'yahooEpsForecast', 'yahooEps', 'yahooSurprisePercentage', 'yahooStartDateTime', 'yahooStartDateTimeType', 'yahooTimeZoneShortName', 'yahooGmtOffsetMilliSeconds', 'marketwatchName', 'marketwatchFiscalQuarterEnding', 'marketwatchEpsForecast', 'marketwatchEps', 'marketwatchSurprisePercentage']
class StagingEarningsDatesBk20230722Row():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, earningsDateValue: str, nasdaqEpsValue: float, nasdaqSurprisePercentageValue: float, nasdaqTimeValue: str, nasdaqNameValue: str, nasdaqLastYearReportDateValue: str, nasdaqLastYearEpsValue: int, nasdaqMarketCapValue: int, nasdaqFiscalQuarterEndingValue: str, nasdaqEpsForecastValue: str, nasdaqNumberOfEstimatesValue: int, yahooNameValue: str, yahooEventNameValue: str, yahooEpsForecastValue: str, yahooEpsValue: float, yahooSurprisePercentageValue: float, yahooStartDateTimeValue: str, yahooStartDateTimeTypeValue: str, yahooTimeZoneShortNameValue: str, yahooGmtOffsetMilliSecondsValue: float, marketwatchNameValue: str, marketwatchFiscalQuarterEndingValue: str, marketwatchEpsForecastValue: float, marketwatchEpsValue: float, marketwatchSurprisePercentageValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.nasdaqEps = nasdaqEpsValue
		self.nasdaqSurprisePercentage = nasdaqSurprisePercentageValue
		self.nasdaqTime = nasdaqTimeValue
		self.nasdaqName = nasdaqNameValue
		self.nasdaqLastYearReportDate = nasdaqLastYearReportDateValue
		self.nasdaqLastYearEps = nasdaqLastYearEpsValue
		self.nasdaqMarketCap = nasdaqMarketCapValue
		self.nasdaqFiscalQuarterEnding = nasdaqFiscalQuarterEndingValue
		self.nasdaqEpsForecast = nasdaqEpsForecastValue
		self.nasdaqNumberOfEstimates = nasdaqNumberOfEstimatesValue
		self.yahooName = yahooNameValue
		self.yahooEventName = yahooEventNameValue
		self.yahooEpsForecast = yahooEpsForecastValue
		self.yahooEps = yahooEpsValue
		self.yahooSurprisePercentage = yahooSurprisePercentageValue
		self.yahooStartDateTime = yahooStartDateTimeValue
		self.yahooStartDateTimeType = yahooStartDateTimeTypeValue
		self.yahooTimeZoneShortName = yahooTimeZoneShortNameValue
		self.yahooGmtOffsetMilliSeconds = yahooGmtOffsetMilliSecondsValue
		self.marketwatchName = marketwatchNameValue
		self.marketwatchFiscalQuarterEnding = marketwatchFiscalQuarterEndingValue
		self.marketwatchEpsForecast = marketwatchEpsForecastValue
		self.marketwatchEps = marketwatchEpsValue
		self.marketwatchSurprisePercentage = marketwatchSurprisePercentageValue

## TABLE: dump_marketwatch_earnings_dates ######################################
dumpMarketwatchEarningsDatesSnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'earnings_date', 'name', 'fiscal_quarter_ending', 'eps_forecast', 'eps', 'surprise_percentage']
dumpMarketwatchEarningsDatesCamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'earningsDate', 'name', 'fiscalQuarterEnding', 'epsForecast', 'eps', 'surprisePercentage']
class DumpMarketwatchEarningsDatesRow():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, earningsDateValue: str, nameValue: str, fiscalQuarterEndingValue: str, epsForecastValue: str, epsValue: float, surprisePercentageValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.name = nameValue
		self.fiscalQuarterEnding = fiscalQuarterEndingValue
		self.epsForecast = epsForecastValue
		self.eps = epsValue
		self.surprisePercentage = surprisePercentageValue

## TABLE: dump_yahoo_earnings_dates ######################################
dumpYahooEarningsDatesSnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'earnings_date', 'name', 'event_name', 'eps_forecast', 'eps', 'surprise_percentage', 'start_date_time', 'start_date_time_type', 'time_zone_short_name', 'gmt_offset_milli_seconds']
dumpYahooEarningsDatesCamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'earningsDate', 'name', 'eventName', 'epsForecast', 'eps', 'surprisePercentage', 'startDateTime', 'startDateTimeType', 'timeZoneShortName', 'gmtOffsetMilliSeconds']
class DumpYahooEarningsDatesRow():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, earningsDateValue: str, nameValue: str, eventNameValue: str, epsForecastValue: str, epsValue: float, surprisePercentageValue: float, startDateTimeValue: str, startDateTimeTypeValue: str, timeZoneShortNameValue: str, gmtOffsetMilliSecondsValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.name = nameValue
		self.eventName = eventNameValue
		self.epsForecast = epsForecastValue
		self.eps = epsValue
		self.surprisePercentage = surprisePercentageValue
		self.startDateTime = startDateTimeValue
		self.startDateTimeType = startDateTimeTypeValue
		self.timeZoneShortName = timeZoneShortNameValue
		self.gmtOffsetMilliSeconds = gmtOffsetMilliSecondsValue

## TABLE: staging_earnings_dates_bk_wip_20230810 ######################################
stagingEarningsDatesBkWip20230810SnakeCaseTableColumns = ['exchange', 'symbol', 'input_date', 'earnings_date', 'nasdaq_eps', 'nasdaq_surprise_percentage', 'nasdaq_time', 'nasdaq_name', 'nasdaq_last_year_report_date', 'nasdaq_last_year_eps', 'nasdaq_market_cap', 'nasdaq_fiscal_quarter_ending', 'nasdaq_eps_forecast', 'nasdaq_number_of_estimates', 'yahoo_name', 'yahoo_event_name', 'yahoo_eps_forecast', 'yahoo_eps', 'yahoo_surprise_percentage', 'yahoo_start_date_time', 'yahoo_start_date_time_type', 'yahoo_time_zone_short_name', 'yahoo_gmt_offset_milli_seconds', 'marketwatch_name', 'marketwatch_fiscal_quarter_ending', 'marketwatch_eps_forecast', 'marketwatch_eps', 'marketwatch_surprise_percentage']
stagingEarningsDatesBkWip20230810CamelCaseTableColumns = ['exchange', 'symbol', 'inputDate', 'earningsDate', 'nasdaqEps', 'nasdaqSurprisePercentage', 'nasdaqTime', 'nasdaqName', 'nasdaqLastYearReportDate', 'nasdaqLastYearEps', 'nasdaqMarketCap', 'nasdaqFiscalQuarterEnding', 'nasdaqEpsForecast', 'nasdaqNumberOfEstimates', 'yahooName', 'yahooEventName', 'yahooEpsForecast', 'yahooEps', 'yahooSurprisePercentage', 'yahooStartDateTime', 'yahooStartDateTimeType', 'yahooTimeZoneShortName', 'yahooGmtOffsetMilliSeconds', 'marketwatchName', 'marketwatchFiscalQuarterEnding', 'marketwatchEpsForecast', 'marketwatchEps', 'marketwatchSurprisePercentage']
class StagingEarningsDatesBkWip20230810Row():
	def __init__(self, exchangeValue: str, symbolValue: str, inputDateValue: str, earningsDateValue: str, nasdaqEpsValue: float, nasdaqSurprisePercentageValue: float, nasdaqTimeValue: str, nasdaqNameValue: str, nasdaqLastYearReportDateValue: str, nasdaqLastYearEpsValue: int, nasdaqMarketCapValue: int, nasdaqFiscalQuarterEndingValue: str, nasdaqEpsForecastValue: str, nasdaqNumberOfEstimatesValue: int, yahooNameValue: str, yahooEventNameValue: str, yahooEpsForecastValue: str, yahooEpsValue: float, yahooSurprisePercentageValue: float, yahooStartDateTimeValue: str, yahooStartDateTimeTypeValue: str, yahooTimeZoneShortNameValue: str, yahooGmtOffsetMilliSecondsValue: float, marketwatchNameValue: str, marketwatchFiscalQuarterEndingValue: str, marketwatchEpsForecastValue: float, marketwatchEpsValue: float, marketwatchSurprisePercentageValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.nasdaqEps = nasdaqEpsValue
		self.nasdaqSurprisePercentage = nasdaqSurprisePercentageValue
		self.nasdaqTime = nasdaqTimeValue
		self.nasdaqName = nasdaqNameValue
		self.nasdaqLastYearReportDate = nasdaqLastYearReportDateValue
		self.nasdaqLastYearEps = nasdaqLastYearEpsValue
		self.nasdaqMarketCap = nasdaqMarketCapValue
		self.nasdaqFiscalQuarterEnding = nasdaqFiscalQuarterEndingValue
		self.nasdaqEpsForecast = nasdaqEpsForecastValue
		self.nasdaqNumberOfEstimates = nasdaqNumberOfEstimatesValue
		self.yahooName = yahooNameValue
		self.yahooEventName = yahooEventNameValue
		self.yahooEpsForecast = yahooEpsForecastValue
		self.yahooEps = yahooEpsValue
		self.yahooSurprisePercentage = yahooSurprisePercentageValue
		self.yahooStartDateTime = yahooStartDateTimeValue
		self.yahooStartDateTimeType = yahooStartDateTimeTypeValue
		self.yahooTimeZoneShortName = yahooTimeZoneShortNameValue
		self.yahooGmtOffsetMilliSeconds = yahooGmtOffsetMilliSecondsValue
		self.marketwatchName = marketwatchNameValue
		self.marketwatchFiscalQuarterEnding = marketwatchFiscalQuarterEndingValue
		self.marketwatchEpsForecast = marketwatchEpsForecastValue
		self.marketwatchEps = marketwatchEpsValue
		self.marketwatchSurprisePercentage = marketwatchSurprisePercentageValue


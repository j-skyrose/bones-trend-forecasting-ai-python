from datetime import datetime

class ExchangesRow():
	## code, name
	def __init__(self, codeValue: str, nameValue: str):
		self.code = codeValue
		self.name = nameValue

class ExchangeAliasesRow():
	## exchange, alias, api
	def __init__(self, exchangeValue: str, aliasValue: str, apiValue: str):
		self.exchange = exchangeValue
		self.alias = aliasValue
		self.api = apiValue

class AssetTypesRow():
	## type, description
	def __init__(self, typeValue: str, descriptionValue: str):
		self.type = typeValue
		self.description = descriptionValue

class DataSetsRow():
	## id, network_id, exchange, symbol, series_type, date, network_set_id, set_type
	def __init__(self, idValue: int, networkIdValue: int, exchangeValue: str, symbolValue: str, seriesTypeValue: str, dateValue: str, networkSetIdValue: int, setTypeValue: str):
		self.id = idValue
		self.networkId = networkIdValue
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.seriesType = seriesTypeValue
		self.date = dateValue
		self.networkSetId = networkSetIdValue
		self.setType = setTypeValue

class SqliteSequenceRow():
	## name, seq
	def __init__(self, nameValue, seqValue):
		self.name = nameValue
		self.seq = seqValue

class CboeVolatilityIndexRow():
	## date, open, high, low, close, artificial
	def __init__(self, dateValue: str, openValue: float, highValue: float, lowValue: float, closeValue: float, artificialValue: bool):
		self.date = dateValue
		self.open = openValue
		self.high = highValue
		self.low = lowValue
		self.close = closeValue
		self.artificial = artificialValue

class SymbolsRow():
	## exchange, symbol, name, asset_type, api_alphavantage, api_polygon, google_topic_id, sector, industry, founded, api_fmp, api_neo
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

class SectorsRow():
	## sector, icb_industry, gics_sector
	def __init__(self, sectorValue: str, icbIndustryValue: str, gicsSectorValue: str):
		self.sector = sectorValue
		self.icbIndustry = icbIndustryValue
		self.gicsSector = gicsSectorValue

class StagingSymbolInfoRow():
	## exchange, symbol, migrated, founded, ipo, sector, polygon_sector, fmp_sector, alphavantage_sector, polygon_industry, fmp_industry, alphavantage_industry, polygon_description, fmp_description, alphavantage_description, polygon_ipo, fmp_ipo, alphavantage_assettype, fmp_isetf
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

class InputVectorFactoriesRow():
	## id, factory, config
	def __init__(self, idValue: int, factoryValue: bytes, configValue: bytes):
		self.id = idValue
		self.factory = factoryValue
		self.config = configValue

class StagingFinancialsRow():
	## exchange, symbol, period, calendarDate, polygon_reportPeriod, polygon_updated, polygon_dateKey, polygon_accumulatedOtherComprehensiveIncome, polygon_assets, polygon_assetsAverage, polygon_assetsCurrent, polygon_assetsNonCurrent, polygon_assetTurnover, polygon_bookValuePerShare, polygon_capitalExpenditure, polygon_cashAndEquivalents, polygon_cashAndEquivalentsUSD, polygon_costOfRevenue, polygon_consolidatedIncome, polygon_currentRatio, polygon_debtToEquityRatio, polygon_debt, polygon_debtCurrent, polygon_debtNonCurrent, polygon_debtUSD, polygon_deferredRevenue, polygon_depreciationAmortizationAndAccretion, polygon_deposits, polygon_dividendYield, polygon_dividendsPerBasicCommonShare, polygon_earningBeforeInterestTaxes, polygon_earningsBeforeInterestTaxesDepreciationAmortization, polygon_EBITDAMargin, polygon_earningsBeforeInterestTaxesDepreciationAmortizationUSD, polygon_earningBeforeInterestTaxesUSD, polygon_earningsBeforeTax, polygon_earningsPerBasicShare, polygon_earningsPerDilutedShare, polygon_earningsPerBasicShareUSD, polygon_shareholdersEquity, polygon_averageEquity, polygon_shareholdersEquityUSD, polygon_enterpriseValue, polygon_enterpriseValueOverEBIT, polygon_enterpriseValueOverEBITDA, polygon_freeCashFlow, polygon_freeCashFlowPerShare, polygon_foreignCurrencyUSDExchangeRate, polygon_grossProfit, polygon_grossMargin, polygon_goodwillAndIntangibleAssets, polygon_interestExpense, polygon_investedCapital, polygon_investedCapitalAverage, polygon_inventory, polygon_investments, polygon_investmentsCurrent, polygon_investmentsNonCurrent, polygon_totalLiabilities, polygon_currentLiabilities, polygon_liabilitiesNonCurrent, polygon_marketCapitalization, polygon_netCashFlow, polygon_netCashFlowBusinessAcquisitionsDisposals, polygon_issuanceEquityShares, polygon_issuanceDebtSecurities, polygon_paymentDividendsOtherCashDistributions, polygon_netCashFlowFromFinancing, polygon_netCashFlowFromInvesting, polygon_netCashFlowInvestmentAcquisitionsDisposals, polygon_netCashFlowFromOperations, polygon_effectOfExchangeRateChangesOnCash, polygon_netIncome, polygon_netIncomeCommonStock, polygon_netIncomeCommonStockUSD, polygon_netLossIncomeFromDiscontinuedOperations, polygon_netIncomeToNonControllingInterests, polygon_profitMargin, polygon_operatingExpenses, polygon_operatingIncome, polygon_tradeAndNonTradePayables, polygon_payoutRatio, polygon_priceToBookValue, polygon_priceEarnings, polygon_priceToEarningsRatio, polygon_propertyPlantEquipmentNet, polygon_preferredDividendsIncomeStatementImpact, polygon_sharePriceAdjustedClose, polygon_priceSales, polygon_priceToSalesRatio, polygon_tradeAndNonTradeReceivables, polygon_accumulatedRetainedEarningsDeficit, polygon_revenues, polygon_revenuesUSD, polygon_researchAndDevelopmentExpense, polygon_returnOnAverageAssets, polygon_returnOnAverageEquity, polygon_returnOnInvestedCapital, polygon_returnOnSales, polygon_shareBasedCompensation, polygon_sellingGeneralAndAdministrativeExpense, polygon_shareFactor, polygon_shares, polygon_weightedAverageShares, polygon_salesPerShare, polygon_tangibleAssetValue, polygon_taxAssets, polygon_incomeTaxExpense, polygon_taxLiabilities, polygon_tangibleAssetsBookValuePerShare, polygon_workingCapital, polygon_weightedAverageSharesDiluted, fmp, alphavantage, polygon, alphavantage_fiscalDateEnding, alphavantage_reportedCurrency, alphavantage_grossProfit, alphavantage_totalRevenue, alphavantage_costOfRevenue, alphavantage_costofGoodsAndServicesSold, alphavantage_operatingIncome, alphavantage_sellingGeneralAndAdministrative, alphavantage_researchAndDevelopment, alphavantage_operatingExpenses, alphavantage_investmentIncomeNet, alphavantage_netInterestIncome, alphavantage_interestIncome, alphavantage_interestExpense, alphavantage_nonInterestIncome, alphavantage_otherNonOperatingIncome, alphavantage_depreciation, alphavantage_depreciationAndAmortization, alphavantage_incomeBeforeTax, alphavantage_incomeTaxExpense, alphavantage_interestAndDebtExpense, alphavantage_netIncomeFromContinuingOperations, alphavantage_comprehensiveIncomeNetOfTax, alphavantage_ebit, alphavantage_ebitda, alphavantage_netIncome, alphavantage_totalAssets, alphavantage_totalCurrentAssets, alphavantage_cashAndCashEquivalentsAtCarryingValue, alphavantage_cashAndShortTermInvestments, alphavantage_inventory, alphavantage_currentNetReceivables, alphavantage_totalNonCurrentAssets, alphavantage_propertyPlantEquipment, alphavantage_accumulatedDepreciationAmortizationPPE, alphavantage_intangibleAssets, alphavantage_intangibleAssetsExcludingGoodwill, alphavantage_goodwill, alphavantage_investments, alphavantage_longTermInvestments, alphavantage_shortTermInvestments, alphavantage_otherCurrentAssets, alphavantage_otherNonCurrrentAssets, alphavantage_totalLiabilities, alphavantage_totalCurrentLiabilities, alphavantage_currentAccountsPayable, alphavantage_deferredRevenue, alphavantage_currentDebt, alphavantage_shortTermDebt, alphavantage_totalNonCurrentLiabilities, alphavantage_capitalLeaseObligations, alphavantage_longTermDebt, alphavantage_currentLongTermDebt, alphavantage_longTermDebtNoncurrent, alphavantage_shortLongTermDebtTotal, alphavantage_otherCurrentLiabilities, alphavantage_otherNonCurrentLiabilities, alphavantage_totalShareholderEquity, alphavantage_treasuryStock, alphavantage_retainedEarnings, alphavantage_commonStock, alphavantage_commonStockSharesOutstanding, alphavantage_operatingCashflow, alphavantage_paymentsForOperatingActivities, alphavantage_proceedsFromOperatingActivities, alphavantage_changeInOperatingLiabilities, alphavantage_changeInOperatingAssets, alphavantage_depreciationDepletionAndAmortization, alphavantage_capitalExpenditures, alphavantage_changeInReceivables, alphavantage_changeInInventory, alphavantage_profitLoss, alphavantage_cashflowFromInvestment, alphavantage_cashflowFromFinancing, alphavantage_proceedsFromRepaymentsOfShortTermDebt, alphavantage_paymentsForRepurchaseOfCommonStock, alphavantage_paymentsForRepurchaseOfEquity, alphavantage_paymentsForRepurchaseOfPreferredStock, alphavantage_dividendPayout, alphavantage_dividendPayoutCommonStock, alphavantage_dividendPayoutPreferredStock, alphavantage_proceedsFromIssuanceOfCommonStock, alphavantage_proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet, alphavantage_proceedsFromIssuanceOfPreferredStock, alphavantage_proceedsFromRepurchaseOfEquity, alphavantage_proceedsFromSaleOfTreasuryStock, alphavantage_changeInCashAndCashEquivalents, alphavantage_changeInExchangeRate, polygon_logo, polygon_listdate, polygon_cik, polygon_bloomberg, polygon_figi, polygon_lei, polygon_sic, polygon_country, polygon_industry, polygon_sector, polygon_marketcap, polygon_employees, polygon_phone, polygon_ceo, polygon_url, polygon_description, polygon_name, polygon_exchangeSymbol, polygon_hq_address, polygon_hq_state, polygon_hq_country, polygon_type, polygon_tags, polygon_similar, polygon_active
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

class DumpSymbolInfoRow():
	## exchange, symbol, alphavantage, fmp, polygon, polygon_logo, polygon_listdate, polygon_cik, polygon_bloomberg, polygon_figi, polygon_lei, polygon_sic, polygon_country, polygon_industry, polygon_sector, polygon_marketcap, polygon_employees, polygon_phone, polygon_ceo, polygon_url, polygon_description, polygon_name, polygon_exchangeSymbol, polygon_hq_address, polygon_hq_state, polygon_hq_country, polygon_type, polygon_updated, polygon_tags, polygon_similar, polygon_active
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

class DumpEdgarTagRow():
	## tag, version, custom, abstract, datatype, iord, crdr, tlabel, doc
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

class DumpEdgarSubRow():
	## exchange, symbol, adsh, cik, name, sic, countryba, stprba, cityba, zipba, bas1, bas2, baph, countryma, stprma, cityma, zipma, mas1, mas2, countryinc, stprinc, ein, former, changed, afs, wksi, fye, form, period, fy, fp, filed, accepted, prevrpt, detail, instance, nciks, aciks
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

class DumpEdgarLoadedRow():
	## type, period
	def __init__(self, typeValue: str, periodValue: str):
		self.type = typeValue
		self.period = periodValue

class DumpEdgarNumRow():
	## adsh, tag, version, coreg, ddate, qtrs, uom, value, footnote, duplicate
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

class EdgarSubBalanceStatusRow():
	## adsh, ddate, status
	def __init__(self, adshValue: str, ddateValue: str, statusValue: float):
		self.adsh = adshValue
		self.ddate = ddateValue
		self.status = statusValue

class VwtbEdgarQuartersRow():
	## exchange, symbol, period, quarter, filed
	def __init__(self, exchangeValue: str, symbolValue: str, periodValue: str, quarterValue: int, filedValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.period = periodValue
		self.quarter = quarterValue
		self.filed = filedValue

class VwtbEdgarFinancialNumsRow():
	## exchange, symbol, tag, ddate, qtrs, uom, value, duplicate
	def __init__(self, exchangeValue: str, symbolValue: str, tagValue: str, ddateValue: str, qtrsValue: int, uomValue: str, valueValue: int, duplicateValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.tag = tagValue
		self.ddate = ddateValue
		self.qtrs = qtrsValue
		self.uom = uomValue
		self.value = valueValue
		self.duplicate = duplicateValue

class SqliteStat1Row():
	## tbl, idx, stat
	def __init__(self, tblValue, idxValue, statValue):
		self.tbl = tblValue
		self.idx = idxValue
		self.stat = statValue

class NetworksRow():
	## id, factoryId, accuracyType, overallAccuracy, negativeAccuracy, positiveAccuracy, changeThreshold, precedingRange, followingRange, seriesType, highMax, volumeMax, epochs
	def __init__(self, idValue: int, factoryIdValue: int, accuracyTypeValue: str, overallAccuracyValue: float, negativeAccuracyValue: float, positiveAccuracyValue: float, changeThresholdValue: int, precedingRangeValue: int, followingRangeValue: int, seriesTypeValue: str, highMaxValue: int, volumeMaxValue: int, epochsValue: int):
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

class HistoricalDataMinuteRow():
	## exchange, symbol, timestamp, open, high, low, close, volume_weighted_average, volume, transactions, artificial
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

class NetworkAccuraciesRow():
	## network_id, accuracy_type, subtype1, subtype2, sum, count
	def __init__(self, networkIdValue: int, accuracyTypeValue: str, subtype1Value: str, subtype2Value: str, sumValue: float, countValue: int):
		self.networkId = networkIdValue
		self.accuracyType = accuracyTypeValue
		self.subtype1 = subtype1Value
		self.subtype2 = subtype2Value
		self.sum = sumValue
		self.count = countValue

class AccuracyLastUpdatesRow():
	## network_id, accuracy_type, data_count, min_date, last_exchange, last_symbol
	def __init__(self, networkIdValue: int, accuracyTypeValue: str, dataCountValue: int, minDateValue: str, lastExchangeValue: str, lastSymbolValue: str):
		self.networkId = networkIdValue
		self.accuracyType = accuracyTypeValue
		self.dataCount = dataCountValue
		self.minDate = minDateValue
		self.lastExchange = lastExchangeValue
		self.lastSymbol = lastSymbolValue

class TickerSplitsRow():
	## network_id, set_count, ticker_count, pickled_split
	def __init__(self, networkIdValue: int, setCountValue: int, tickerCountValue: int, pickledSplitValue: bytes):
		self.networkId = networkIdValue
		self.setCount = setCountValue
		self.tickerCount = tickerCountValue
		self.pickledSplit = pickledSplitValue

class AssetSubtypesRow():
	## asset_type, sub_type
	def __init__(self, assetTypeValue: str, subTypeValue: str):
		self.assetType = assetTypeValue
		self.subType = subTypeValue

class StatusKeyRow():
	## status, description
	def __init__(self, statusValue: int, descriptionValue: str):
		self.status = statusValue
		self.description = descriptionValue

class DumpStockSplitsPolygonRow():
	## exchange, symbol, date, split_from, split_to
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, splitFromValue: float, splitToValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.splitFrom = splitFromValue
		self.splitTo = splitToValue

class HistoricalDataRow():
	## exchange, symbol, type, date, open, high, low, close, volume, artificial
	def __init__(self, exchangeValue: str, symbolValue: str, typeValue: str, dateValue: str, openValue: float, highValue: float, lowValue: float, closeValue: float, volumeValue: float, artificialValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.type = typeValue
		self.date = dateValue
		self.open = openValue
		self.high = highValue
		self.low = lowValue
		self.close = closeValue
		self.volume = volumeValue
		self.artificial = artificialValue

class LastUpdatesRow():
	## exchange, symbol, type, api, date
	def __init__(self, exchangeValue: str, symbolValue: str, typeValue: str, apiValue: str, dateValue: str):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.type = typeValue
		self.api = apiValue
		self.date = dateValue

class GoogleInterestsRow():
	## exchange, symbol, date, relative_interest
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, relativeInterestValue: int):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.relativeInterest = relativeInterestValue

class HistoricalCalculatedTechnicalIndicatorDataRow():
	## exchange, symbol, date_type, date, indicator, period, value
	def __init__(self, exchangeValue: str, symbolValue: str, dateTypeValue: str, dateValue: str, indicatorValue: str, periodValue: float, valueValue: float):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.dateType = dateTypeValue
		self.date = dateValue
		self.indicator = indicatorValue
		self.period = periodValue
		self.value = valueValue

class HistoricalVectorSimilarityDataRow():
	## exchange, symbol, date_type, date, vector_class, preceding_range, following_range, change_threshold, value
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

class GoogleInterestsRawBkRow():
	## exchange, symbol, date, type, stream, relative_interest, artificial
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, typeValue: str, streamValue: int, relativeInterestValue: int, artificialValue: int):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.type = typeValue
		self.stream = streamValue
		self.relativeInterest = relativeInterestValue
		self.artificial = artificialValue

class GoogleInterestsRawRow():
	## exchange, symbol, date, type, stream, relative_interest, artificial
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, typeValue: str, streamValue: int, relativeInterestValue: int, artificialValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.type = typeValue
		self.stream = streamValue
		self.relativeInterest = relativeInterestValue
		self.artificial = artificialValue

class GoogleInterestsBkRow():
	## exchange, symbol, date, relative_interest
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, relativeInterestValue: int):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.relativeInterest = relativeInterestValue

class GoogleInterestsRawBk2Row():
	## exchange, symbol, date, type, stream, relative_interest, artificial
	def __init__(self, exchangeValue: str, symbolValue: str, dateValue: str, typeValue: str, streamValue: int, relativeInterestValue: int, artificialValue: bool):
		self.exchange = exchangeValue
		self.symbol = symbolValue
		self.date = dateValue
		self.type = typeValue
		self.stream = streamValue
		self.relativeInterest = relativeInterestValue
		self.artificial = artificialValue

class HistoricalVectorSimilarityDataBkRow():
	## exchange, symbol, date_type, date, vector_class, preceding_range, following_range, change_threshold, value
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

class DumpNasdaqEarningsDatesRow():
	## symbol, input_date, earnings_date, name, last_year_report_date, last_year_eps, time, market_cap, fiscal_quarter_ending, eps_forecast, number_of_estimates
	def __init__(self, symbolValue: str, inputDateValue: str, earningsDateValue: str, nameValue: str, lastYearReportDateValue: str, lastYearEpsValue: int, timeValue: str, marketCapValue: int, fiscalQuarterEndingValue: str, epsForecastValue: str, numberOfEstimatesValue: int):
		self.symbol = symbolValue
		self.inputDate = inputDateValue
		self.earningsDate = earningsDateValue
		self.name = nameValue
		self.lastYearReportDate = lastYearReportDateValue
		self.lastYearEps = lastYearEpsValue
		self.time = timeValue
		self.marketCap = marketCapValue
		self.fiscalQuarterEnding = fiscalQuarterEndingValue
		self.epsForecast = epsForecastValue
		self.numberOfEstimates = numberOfEstimatesValue


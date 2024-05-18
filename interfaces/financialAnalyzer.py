
import os, sys
path = os.path.dirname(os.path.abspath(__file__))
while ".vscode" not in os.listdir(path):
    if path == os.path.dirname(path):
        raise FileNotFoundError("Could not find project root")
    path = os.path.dirname(path)
sys.path.append(path)
## done boilerplate "package"

import tqdm, json
from managers.databaseManager import DatabaseManager
from utils.support import DotDict, Singleton, flatten, recdotdict, shortc

dbm: DatabaseManager = DatabaseManager()


LiabilitiesCurrentTags = [
    'AccountsPayable', 
    'AccruedLiabilities',
    'AccountsPayableCurrent',
    'AccruedLiabilitiesCurrent',
    'AccruedIncomeTaxesCurrent',
    'LongTermDebtCurrent',
    'OtherLiabilitiesCurrent',
    'AccountsPayableTradeCurrent',
    'EmployeeRelatedLiabilitiesCurrent',
    'AccountsPayableAndOther',
    'LongTermDebtAndCapitalLeaseObligationsCurrent',
    'ShortTermBorrowings',
    'AccountsPayableAndAccruedLiabilitiesCurrent',
    'DebtCurrent',
    'DeferredTaxLiabilitiesCurrent',
    'OtherAccruedLiabilitiesCurrent',
    'InterestPayableCurrent',
    'NotesPayableCurrent',
    'ConvertibleNotesPayableCurrent',
    'AccruedEmployeeBenefitsCurrent',
    'WarrantsAndRightsOutstanding',
    'LinesOfCreditCurrent',
    'NotesPayableRelatedPartiesCurrent',
    'CustomerAdvancesCurrent',
    'AccountsPayableAndAccruedLiabilities', 
    'OilAndGasDrillingAndOperatingCostsPayable',
    'NotesPayableRelatedPartiesClassifiedCurrent',
    'AccruedDispositionCosts', 
    'DeferredRevenueCurrent',
    'DerivativeLiabilitiesCurrent',
    'AccruedClinicalExpenseCurrent',
    'AccruedExpensesAndOtherCurrentLiabilities',
    'DueToRelatedPartiesCurrent',
    'DueToDirector',
    'AccountsPayableOtherCurrent',
    'DerivativeLiabilities',
    'ConvertibleNotesPayableRelatedPartiesCurrent',
    'InterestPayableRelatedPartiesCurrent',
    'DeferredCompensationLiabilityCurrent',
    'LoansPayableCurrent',
    'DueToOfficersOrStockholders',
    'TaxesPayableCurrent',
    'LitigationReserve',
    'DueToOfficersOrStockholdersCurrent',
    'AccruedIncomeTaxesPayable',
    'AccrualForTaxesOtherThanIncomeTaxesCurrent',
    'LiabilitiesOfDisposalGroupIncludingDiscontinuedOperationCurrent',
    'OtherAccruedTaxesCurrent',
    'AccruedIncomeTaxesIncludingDeferredTaxLiabilitiesCurrent', 
    'CapitalLeaseObligationsCurrent',
    'NotesPayableToBankCurrent', 
    'SalesAndExciseTaxPayableCurrent',
    'AccruedInsuranceCurrent', 
    'DividendsPayableCurrent',
    'ProductWarrantyAccrualClassifiedCurrent', 
    'ReserveForLossesAndLossAdjustmentExpenses',
    'ShortTermBankLoansAndNotesPayable',
    'ShortTermBorrowingsAndLongTermDebtCurrent',
    'IncomeTaxesPayableAndDeferred', 
    'NotesAndLoansPayableCurrent',
    'CustomerAdvancesAndDepositsCurrent',
    'AccruedCustomerPrograms',
    'InterestAndDividendsPayableCurrent',
    'BillingsInExcessOfCost',
    'DerivativeInstrumentsAndHedgesLiabilities',
    'DeferredRevenue',
    'OtherAccruedEmployeeStockPurchasePlanLiabilitiesCurrent', 
    'OtherAccruedLegalLiabilitiesCurrent', 
    'OtherAccruedRetailerLiabilitiesCurrent',
    'AccruedWarrantyAndOther', 
    'EarnOutsPayable',
    'AccruedExpensesAndOther',
    'ConvertibleSubordinatedDebtCurrent',
    'ConvertibleDebtCurrent',
    'AccruedRoyaltiesCurrent',
    'AccruedBonusesCurrent',
    'AccountsPayableRelatedPartiesCurrent',
    'CustomerDepositsAndStoreCredits',
    'AccruedDevelopmentExpenseCurrent',
    'AccountsPayableAndOtherAccruedLiabilitiesCurrent',
    'AccruedMarketingExpenses',
    'AccountsAndTaxesPayable',
    'FairvalueDerivativeLiabilities', 
    'StockIssuanceObligationCurrent',
    'AccruedExpensesAndOhterCurrentLiabilities',
    'EmbeddedDerivativeFairValueOfEmbeddedDerivativeLiability',
    'DeferredRentCreditCurrent',
    'AccruedProfessionalFeesCurrent', 
    'LoansFromOfficers',
    'DueToAffiliateCurrent',
    'DeferredCreditsAndOtherLiabilities',
    'CustomerDepositsCurrent',
    'LeaseLiabilitiesCurrent',
    'CustomerRefundLiabilityCurrent', 
    'DueToRelatedPartiesNoncurrent',
    'OtherAccountsPayableAndAccruedLiabilities',
    'BankOverdrafts',
    'CustomerAdvancePaymentsAndDeferredRevenue',
    'RestructuringReserveCurrent',
    'AirTrafficLiabilityCurrent',
    'AccruedSalesCommissionCurrent', 
    'BillingsInExcessOfCostCurrent', 
    'LongTermDebtComponentsCommercialLoansCurrent',

    'AccountsPayablesAndAccruedLiabilities',
    'AccruedCooperativeAdvertising',
    'RelatedPartyPayables',
    'SecuredDebtCurrent',
    'AccruedMarketingCostsCurrent',
    'OtherAccountsPayableAndAccruedExpensesCurrent',
    'AccruedEnvironmentalLossContingenciesCurrent',
    'DeferredAcquisitionPaymentsCurrent',
    'FundManagementAndAdministrationPayable',
    'LitigationReserveCurrent',

    'AssetRetirementObligationCurrent',
    'AccruedInterest',
    'AccruedSalariesCurrent',
    'DisputedAccountsPayable',
    'ShortTermNonBankLoansAndNotesPayable',
    'GasPurchasePayableCurrent',
    'AccruedResearchAndDevelopmentExpenses',
    'VehicleFloorPlanPayableNonTrade', 
    'VehicleFloorPlanPayableTrade',
    'AccruedLiabilitiesRelatedPartiesCurrent',
    'DerivativeLiabilityNotionalAmount',
    'DeferredRevenueAndCreditsCurrent',
    'DemandPromissoryNotes', 
    'LeaseholdIncentiveObligationCurrent',
    'SubordinatedDebtCurrent',
    'FairValueOfWarrantsPotentiallySettleableInCash',
    'OtherShortTermBorrowings',
    'LiabilitiesOfAssetsHeldForSale',

    'ShortTermBankDebtAndCurrentMaturitiesOfNotes',
    'ProceedsFromRelatedPartyDebt', #weird "proceeds"
    'ConvertibleDebtFairValueCurrent',

]

AssetsCurrentTags = [
    'CashAndCashEquivalentsAtCarryingValue', 
    'MarketableSecuritiesCurrent', 
    'InventoryNet', 
    'AccountsReceivableNetCurrent', 
    'DeferredTaxAssetsNetCurrent',
    'OtherAssetsCurrent',
    'OtherRestrictedAssetsCurrent',
    'PrepaidExpensesAndOther',
    'ShortTermInvestments',
    'RetailRelatedInventoryMerchandise',
    'PrepaidExpensesAndOtherCurrentAssets',
    'CashEquivalentsAtCarryingValue',
    'MaterialsAndSupplies',
    'InventoryFinishedGoods',
    'PrepaidExpenseCurrent',
    'ReceivablesNetCurrent',
    'PrepaidExpenseAndOtherAssets',
    'PrepaidExpenseAndOtherAssetsCurrent',
    'AvailableForSaleSecuritiesCurrent',
    'DueFromAffiliateCurrent',
    'Deposits',
    'PrepaidExpense',
    'AccruedIncomeReceivable',
    'USGovernmentSecuritiesAtCarryingValue',
    'Cash',
    'MarketableSecurities',
    'OfficeFurnitureNet',
    'DepositsAssetsCurrent',
    'RestrictedCashAndCashEquivalentsAtCarryingValue',
    'OtherReceivablesNetCurrent',
    'FinanceReceivablesHeldForInvestmentCurrent', 
    'ReceivablesHeldForSaleNetAmount',
    'InventoryFinishedGoodsAndWorkInProcess', 
    'MaterialsSuppliesAndPrepaidExpenses',
    'AssetsHeldForSaleCurrent', 
    'Supplies',
    'PrepaidTaxes',
    'DeferredCostsCurrent', 
    'PropertyPlantAndEquipmentGross',
    'AccountsAndOtherReceivablesNetCurrent',
    'IncomeTaxesReceivableAndDeferred',
    'NontradeReceivables',
    'CertificatesOfDepositAtCarryingValue',
    'UnbilledReceivablesCurrent',
    'PurchasedTechnologyNet',
    'OtherPrepaidExpenseCurrent',
    'InterestReceivableCurrent',
    'RestrictedCashAndCashEquivalents',
    'IncomeTaxesReceivable',
    'NoteReceivableAndOtherCurrentAssets', 
    'ReceivableAndDeferredTaxAssetsCurrent',
    'GrantsReceivableCurrent',
    'DeferredTaxAssetsGrossCurrent',
    'RetailRelatedInventory',
    'AvailableForSaleSecuritiesDebtSecuritiesCurrent',

    'AssetsOfDisposalGroupIncludingDiscontinuedOperationCurrent',
    'OtherReceivables',
    'DeferredTaxesAndOther',
    'DueFromRelatedPartiesCurrent', 
    'OtherReceivablesCurrent',
    'AccountsReceivableAndOtherAssetsCurrent',
    'DeferredIncomeTaxesAndOtherTaxReceivableCurrent',
    'PrepaidExpensesAndOtherAssetsCurrent',
    'AccountsNotesAndLoansReceivableNetCurrent',
    'Investments',
    'CustomerDepositsNetCurrent',
    'NontradeReceivablesCurrent',
    'RoyaltyReceivablesNetCurrent',
    'DeferredFinanceCostsCurrentNet',
    'AccountsReceivableGrossCurrent', 
    'AccountsReceivableRelatedPartiesCurrent',
    'OtherAssetsHeldForSaleCurrent',
    'PatronageDividendReceivable',
    'BilledContractReceivables', 
    'UnbilledContractsReceivable',
    'DerivativeAssetsCurrent',
    'AccountsReceivableCurrent',
    'NotesReceivableRelatedPartiesCurrent',
    'CostsInExcessOfBillingsOnUncompletedContractsOrPrograms', 
    'InventoryPartsAndComponentsNetOfReserves',


    'ContentLibraryNetCurrent',
    'NotesReceivableRelatedParties',
    'AccountsReceivableAndPrepaidExpensesCurrent',

    'DueFromEmployeesCurrent', 
    'MutualFunds', 
    'OtherAdvisory', 
    'TradingSecuritiesCurrent',

    'ConsumerLoansNet', 
    'PawnLoanFeesAndServiceChargesReceivable', 
    'PawnLoans',
    'AccountsReceivableNet',
    'CostsInExcessOfBillingsOnUncompletedContractsOrProgramsExpectedToBeCollectedWithinOneYear',
    'AvailableForSaleSecuritiesEquitySecuritiesCurrent',
    'DepositPrepaidExpensesAndInventory', 
    'DerivativeInstrumentsAndHedges',
    'AccountsAndNotesReceivableNet', 
    'DeferredIncomeTaxesAndOtherAssetsCurrent',
    'NotesAndLoansReceivableNetCurrent',
    'DeferredTaxAssetsOther',
    'OtherShortTermInvestments',
    'LicensingAndRoyaltyIncomeReceivable',

    'PrepaidResearchAndDevelopmentExpenses',
    'OtherInventory',

]

StockholdersEquityTags = [
    'CommonStockValue', 
    '-TreasuryStockValue', 
    'AdditionalPaidInCapital', 
    'RetainedEarningsAccumulatedDeficit', 
    'AccumulatedOtherComprehensiveIncomeLossNetOfTax',
    'CommonStockIncludingAdditionalPaidInCapital',
    'CommonStockValueOutstanding',
    'AdditionalPaidInCapitalCommonStock',
    'CommonStock',
    'ListedCommonStockValue'
    'AdjustmentsToAdditionalPaidInCapitalOther', 
    'NetIncomeLoss',
    'DevelopmentStageEnterpriseDeficitAccumulatedDuringDevelopmentStage',
    'StockIssuedDuringPeriodValueNewIssues',
    'AdjustmentsToAdditionalPaidInCapitalContributionOfCapital',
    'StockIssuedDuringPeriodForCashInMarch',
    'StockIssuedDuringPeriodForCashInSeptember',
    'IssuanceOfCommonStockAndFulfillmentOfStockSubscriptionsReceivableValue',
    'NetIncomeLossAvailableToCommonStockholdersBasic', 
    'StockIssuedDuringPeriodValueFounderIssues', 
    'AdjustmentsToAdditionalPaidInCapitalShareBasedCompensationStockOptionsConsultantsAndProfessionals',
    'AccumulatedOtherComprehensiveIncomeLossAvailableForSaleSecuritiesAdjustmentNetOfTax',
    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'AccruedIncomeTaxesNoncurrent',
    'ParentCompanyInvestments',
    'AccumulatedOtherComprehensiveIncomeLossForeignCurrencyTranslationAdjustmentNetOfTax',

    'OtherShareholdersEquity',

    'PreferredStockValue',
    'NetInvestmentOfParentPriorToSpinOffTransaction',

    'DeficitAccumulatedDuringDevelopmentalStage',
]

AssetTags = [
    'AssetsCurrent', 
    'PropertyPlantAndEquipmentNet', 
    'Goodwill', 
    'OtherAssetsNoncurrent', 
    'DeferredTaxAssetsNetNoncurrent',
    'FurnitureAndFixturesGross',
    'IntangibleAssetsNetExcludingGoodwill',
    'DepositsAndOtherAssets',
    'EquityMethodInvestments',
    'NotesAndLoansReceivableNetNoncurrent',
    'OtherAssets',
    'DueFromRelatedParties',
    'DepositsAssetsNoncurrent',
    'LongTermInvestments',
    'PlantTurnaroundsNet',
    'DeferredCostsCurrentAndNoncurrent', #weird2
    'CommonStockSharesAuthorized',

    'AvailableForSaleSecuritiesNoncurrent',
    'FiniteLivedIntangibleAssetOffMarketLeaseFavorableGross',
    'InventoryNoncurrent',
    'FiniteLivedIntangibleAssetsNet',
    'RestrictedCashAndCashEquivalentsNoncurrent',
    'AvailableForSaleSecuritiesDebtSecuritiesNoncurrent',
    'DepositsOnFlightEquipment', 
    'PrepaidAircraftMaintenanceToLessors', 
    'SecurityDepositsAndOtherLongTermAssets',

    'OtherAssetsMiscellaneousNoncurrent', 
    'OtherInventoryNoncurrent',
    'InvestmentsInAffiliatesSubsidiariesAssociatesAndJointVentures', 
    'PrepaidExpenseOtherNoncurrent',

    'DeferredOfferingCosts', 
    'DueFromAffiliateNoncurrent', 
    'OtherAssetsNoncurrentOther',
    'OtherIntangibleAssetsNet',
    'DeferredFinanceCostsNoncurrentNet',
    'GoodwillAndIntangibles',
    'AssetsHeldForSaleLongLived',
    'RentalProductNet',
    'MarketableSecuritiesNoncurrent',

    'RestrictedCashAndInvestmentsNoncurrent',
    'IncomeTaxesReceivableNoncurrent',

]

LiabilitiesAndStockholdersEquityTags = [
    'LiabilitiesCurrent', 
    'StockholdersEquity', 
    'LongTermDebtNoncurrent', 
    'OtherLiabilitiesNoncurrent',
    'Liabilities',
    'MinorityInterest',
    'DeferredTaxLiabilitiesNoncurrent',
    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'LongTermDebtAndCapitalLeaseObligations',
    'CapitalLeaseObligationsNoncurrent',
    'PartnersCapital',
    'LiabilitiesNoncurrent',
    'PartnersCapitalAttributableToNoncontrollingInterestConsolidatedEntities', 
    'PartnersCapitalAttributableToNoncontrollingInterestHoldings',
    'UnallocatedReserve', #maybe1
    'AccountsPayableAndAccruedLiabilitiesCurrentAndNoncurrent',
    'PartnersCapitalAttributableToNoncontrollingInterest',
    'DeferredRentCreditNoncurrent',
    'AccountsPayableTrade', 
    'ConvertibleNotesPayable', 
    'DueToRelatedParties', 
    'OtherAccruedLiabilitiesNoncurrent',
    'PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent',
    'TemporaryEquityCarryingAmount',
    'DeferredRevenueNoncurrent',
    'LongTermNotesPayable',

    'LiabilitiesOfDisposalGroupIncludingDiscontinuedOperationNoncurrent',
    'ConvertibleLongTermNotesPayable', 
    'WarrantLiabilitiesNoncurrent',

    'DeferredCreditsAndOtherLiabilitiesNoncurrent',
    'DerivativeLiabilitiesNoncurrent',
    'TemporaryEquityValueExcludingAdditionalPaidInCapital',
    'ConversionOptionSubjectToCashSettlement',

]

def printDuplicates(lst):
    seen = set()
    for x in lst:
        if x in seen: 
            print(x)
        seen.add(x)

if  len(LiabilitiesCurrentTags) != len(set(LiabilitiesCurrentTags)):
    print('liablte')
    printDuplicates(LiabilitiesCurrentTags)
    raise IndexError
if len(AssetsCurrentTags) != len(set(AssetsCurrentTags)):
    print('curraccset')
    printDuplicates(AssetsCurrentTags)
    raise IndexError
if len(StockholdersEquityTags) != len(set(StockholdersEquityTags)):
    print('stockequ')
    printDuplicates(StockholdersEquityTags)
    raise IndexError
if len(AssetTags) != len(set(AssetTags)):
    print('assetsfull')
    printDuplicates(AssetTags)
    raise IndexError
if len(LiabilitiesAndStockholdersEquityTags) != len(set(LiabilitiesAndStockholdersEquityTags)):
    print('liabstockequboth')
    printDuplicates(LiabilitiesAndStockholdersEquityTags)
    raise IndexError

taglist = LiabilitiesCurrentTags + AssetsCurrentTags + StockholdersEquityTags + AssetTags + LiabilitiesAndStockholdersEquityTags + [
    'Assets',
    'LiabilitiesAndStockholdersEquity'
]

taglist2 = [
    'AccountsPayable',
    'AccountsReceivableNetCurrent',
    'AccruedLiabilities',
    'AccumulatedOtherComprehensiveIncomeLossNetOfTax',
    'AdditionalPaidInCapital',
    'Assets',
    'AssetsCurrent',
    'CashAndCashEquivalentsAtCarryingValue',
    'CommitmentsAndContingencies',
    'CommonStockValue',
    'DeferredTaxAssetsNetCurrent',
    'DeferredTaxAssetsNetNoncurrent',
    'Goodwill',
    'InventoryNet',
    'LiabilitiesAndStockholdersEquity',
    'LiabilitiesCurrent',
    'LongTermDebtNoncurrent',
    'MarketableSecuritiesCurrent',
    'OtherAssetsNoncurrent',
    'OtherLiabilitiesNoncurrent',
    'PreferredStockValue',
    'PropertyPlantAndEquipmentNet',
    'RetainedEarningsAccumulatedDeficit',
    'StockholdersEquity',
    'TreasuryStockValue',

    ## code determined
    'Liabilities',
    'MinorityInterest',
    'CommonStockIncludingAdditionalPaidInCapital',
    'CommonStockValueOutstanding',
    'AdditionalPaidInCapitalCommonStock',
    'OtherAssetsCurrent',
    'OtherRestrictedAssetsCurrent',
    'FurnitureAndFixturesGross', ## weird1
    'IntangibleAssetsNetExcludingGoodwill', ## weird1
    'AccountsPayableCurrent',
    'AccruedLiabilitiesCurrent',
    'PrepaidExpensesAndOther',
    'ShortTermInvestments',
    'DeferredTaxLiabilitiesNoncurrent',
    'AccruedIncomeTaxesCurrent',
    'LongTermDebtCurrent',
    'OtherLiabilitiesCurrent',
    'RetailRelatedInventoryMerchandise',
    'AccountsPayableTradeCurrent',
    'EmployeeRelatedLiabilitiesCurrent',
    'PrepaidExpensesAndOtherCurrentAssets'
    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'CashEquivalentsAtCarryingValue',
    'AccountsPayableAndOther',
    'LongTermDebtAndCapitalLeaseObligationsCurrent',
    'MaterialsAndSupplies',
    'LongTermDebtAndCapitalLeaseObligations',
    'CommonStock',
    'DepositsAndOtherAssets',
    'CapitalLeaseObligationsNoncurrent',
    'ShortTermBorrowings',
    'AccountsPayableAndAccruedLiabilitiesCurrent',
    'DebtCurrent',
    'DeferredTaxLiabilitiesCurrent',
    'InventoryFinishedGoods',
    'PrepaidExpenseCurrent',
    'ReceivablesNetCurrent',
    'EquityMethodInvestments',
    'NotesAndLoansReceivableNetNoncurrent',
        'OtherAssets',
        'PartnersCapital',
        'OtherAccruedLiabilitiesCurrent',
        'PrepaidExpenseAndOtherAssets',
        'ListedCommonStockValue',
        'PrepaidExpenseAndOtherAssetsCurrent',
        'DueFromRelatedParties',
        'InterestPayableCurrent',
        'NotesPayableCurrent',
        'DepositsAssetsNoncurrent',
        'LongTermInvestments',
        'ConvertibleNotesPayableCurrent',
        'AccruedEmployeeBenefitsCurrent',
        'WarrantsAndRightsOutstanding',
        'AvailableForSaleSecuritiesCurrent',
        'LinesOfCreditCurrent',
            'NotesPayableRelatedPartiesCurrent',
            'AdjustmentsToAdditionalPaidInCapitalOther', 
            'NetIncomeLoss',
            'DueFromAffiliateCurrent',
            'LiabilitiesNoncurrent',
            'PlantTurnaroundsNet',
            'CustomerAdvancesCurrent',
            'DevelopmentStageEnterpriseDeficitAccumulatedDuringDevelopmentStage',
            'Deposits',
            'PrepaidExpense',
            'AccountsPayableAndAccruedLiabilities', 
            'OilAndGasDrillingAndOperatingCostsPayable',
            'PartnersCapitalAttributableToNoncontrollingInterestConsolidatedEntities', 
            'PartnersCapitalAttributableToNoncontrollingInterestHoldings',
            'AccruedIncomeReceivable',
            'USGovernmentSecuritiesAtCarryingValue',
            'UnallocatedReserve', #maybe1
            'StockIssuedDuringPeriodValueNewIssues',
            'Cash',
            'AccountsPayableAndAccruedLiabilitiesCurrentAndNoncurrent',
            'DeferredCostsCurrentAndNoncurrent', #weird2
            'NotesPayableRelatedPartiesClassifiedCurrent',
            'AdjustmentsToAdditionalPaidInCapitalContributionOfCapital',
            'StockIssuedDuringPeriodForCashInMarch',
            'StockIssuedDuringPeriodForCashInSeptember',
            'PartnersCapitalAttributableToNoncontrollingInterest',
                'AccruedDispositionCosts', 
                'DeferredRevenueCurrent',
                'DerivativeLiabilitiesCurrent',
                'AccruedClinicalExpenseCurrent',
                'MarketableSecurities',
                'DeferredRentCreditNoncurrent',
                'CommonStockSharesAuthorized',
                'AccountsPayableTrade', 
                'ConvertibleNotesPayable', 
                'DueToRelatedParties', 
                'OtherAccruedLiabilitiesNoncurrent',
                'IssuanceOfCommonStockAndFulfillmentOfStockSubscriptionsReceivableValue',
                'LiabilitiesNoncurrent',
                'OfficeFurnitureNet',
                'DepositsAssetsCurrent',
                'PartnersCapitalAttributableToNoncontrollingInterestConsolidatedEntities', 
                'PartnersCapitalAttributableToNoncontrollingInterestHoldings',
                'NetIncomeLossAvailableToCommonStockholdersBasic', 
                'StockIssuedDuringPeriodValueFounderIssues', 
                'AdjustmentsToAdditionalPaidInCapitalShareBasedCompensationStockOptionsConsultantsAndProfessionals',
                'AccruedExpensesAndOtherCurrentLiabilities',

                    'DueToRelatedPartiesCurrent',
                    'DueToDirector',
                    'AccountsPayableOtherCurrent',
                    'DerivativeLiabilities',
                    'ConvertibleNotesPayableRelatedPartiesCurrent',
                    'RestrictedCashAndCashEquivalentsAtCarryingValue',
                    'InterestPayableRelatedPartiesCurrent',
                    'DeferredCompensationLiabilityCurrent',
                    'LoansPayableCurrent',
                    'DueToOfficersOrStockholders',
                    'TaxesPayableCurrent',
                    'LitigationReserve',
                    'DueToOfficersOrStockholdersCurrent',
                    'OtherReceivablesNetCurrent',

                    'FinanceReceivablesHeldForInvestmentCurrent', 
                    'ReceivablesHeldForSaleNetAmount',
                    'AccruedIncomeTaxesPayable',
                    'InventoryFinishedGoodsAndWorkInProcess', 
                    'MaterialsSuppliesAndPrepaidExpenses',
                    'AssetsHeldForSaleCurrent', 
                    'Supplies',
                    'AccrualForTaxesOtherThanIncomeTaxesCurrent',
                    'LiabilitiesOfDisposalGroupIncludingDiscontinuedOperationCurrent',
                    'OtherAccruedTaxesCurrent',
                    'AccruedIncomeTaxesIncludingDeferredTaxLiabilitiesCurrent', 
                    'CapitalLeaseObligationsCurrent',
                    'NotesPayableToBankCurrent', 
                    'SalesAndExciseTaxPayableCurrent',
                    'AccruedInsuranceCurrent', 
                    'DividendsPayableCurrent',
                    'ProductWarrantyAccrualClassifiedCurrent', 
                    'ReserveForLossesAndLossAdjustmentExpenses',
                    'AccumulatedOtherComprehensiveIncomeLossAvailableForSaleSecuritiesAdjustmentNetOfTax',
                    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                    'ShortTermBankLoansAndNotesPayable',
                    'ShortTermBorrowingsAndLongTermDebtCurrent',
                    'IncomeTaxesPayableAndDeferred', 
                    'NotesAndLoansPayableCurrent',
                    'CustomerAdvancesAndDepositsCurrent',
                    'PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent',
                    'PrepaidTaxes',
                    'AccruedCustomerPrograms',
                    'InterestAndDividendsPayableCurrent',
                    'BillingsInExcessOfCost',
                    'DerivativeInstrumentsAndHedgesLiabilities',
                    'DeferredCostsCurrent', 
                    'PropertyPlantAndEquipmentGross',
                    'CapitalLeaseObligationsCurrent', 
                    'DeferredRevenue',
                    'AccountsAndOtherReceivablesNetCurrent',
                    'OtherAccruedEmployeeStockPurchasePlanLiabilitiesCurrent', 
                    'OtherAccruedLegalLiabilitiesCurrent', 
                    'OtherAccruedRetailerLiabilitiesCurrent',
                    'AccruedWarrantyAndOther', 
                    'EarnOutsPayable',
                    'IncomeTaxesReceivableAndDeferred',
                    'NontradeReceivables',
                    'AccruedExpensesAndOther',
                    'CertificatesOfDepositAtCarryingValue',
                    'TemporaryEquityCarryingAmount',
                    'UnbilledReceivablesCurrent',
                    'ConvertibleSubordinatedDebtCurrent',
                    'ConvertibleDebtCurrent',
                    'AccruedRoyaltiesCurrent',
                    'PurchasedTechnologyNet',
                    'OtherPrepaidExpenseCurrent',
                    'AccruedBonusesCurrent',
                    'AccountsPayableRelatedPartiesCurrent',
                    'CustomerDepositsAndStoreCredits',
                    'AccruedDevelopmentExpenseCurrent',
                    'AccountsPayableAndOtherAccruedLiabilitiesCurrent',
                    'AccruedMarketingExpenses',
                    'InterestReceivableCurrent',
                    'RestrictedCashAndCashEquivalents',
                    'IncomeTaxesReceivable',
                    'DeferredRevenueNoncurrent',
                    'NoteReceivableAndOtherCurrentAssets', 
                    'ReceivableAndDeferredTaxAssetsCurrent',
                    'AccountsAndTaxesPayable',
                    'FairvalueDerivativeLiabilities', 
                    'StockIssuanceObligationCurrent',
                    'AccruedExpensesAndOhterCurrentLiabilities',
                    'EmbeddedDerivativeFairValueOfEmbeddedDerivativeLiability',
                    'GrantsReceivableCurrent',
                    'DeferredRentCreditCurrent',
                    'CapitalLeaseObligationsCurrent',
                    'AccruedProfessionalFeesCurrent', 
                    'LoansFromOfficers',
                    'DueToAffiliateCurrent',
                    'DeferredCreditsAndOtherLiabilities',
                    'DeferredTaxAssetsGrossCurrent',
                    'AccruedIncomeTaxesNoncurrent',
                    'CustomerDepositsCurrent',
                    'ParentCompanyInvestments',
                    'LeaseLiabilitiesCurrent',
                    'CustomerRefundLiabilityCurrent', 
                    'DueToRelatedPartiesNoncurrent',
                    'OtherAccountsPayableAndAccruedLiabilities',
                    'RetailRelatedInventory',
                    'BankOverdrafts',
                    'AvailableForSaleSecuritiesDebtSecuritiesCurrent',
                    'CustomerAdvancePaymentsAndDeferredRevenue',
                    'LongTermNotesPayable',
                    'RestructuringReserveCurrent',
                    'AirTrafficLiabilityCurrent',
                    'AccruedSalesCommissionCurrent', 
                    'BillingsInExcessOfCostCurrent', 
                    'LongTermDebtComponentsCommercialLoansCurrent',
                    'AccumulatedOtherComprehensiveIncomeLossForeignCurrencyTranslationAdjustmentNetOfTax',


    ## not used
    'CommonStockParOrStatedValuePerShare',
    'PreferredStockParOrStatedValuePerShare',
]

import itertools

def reverseLookupKeys(d, val):
    retk = []
    for k,v in d.items():
        if v == val and k not in taglist: retk.append(k)
    if len(retk) == 0: return
    elif len(retk) == 1: return retk[0]
    else: return retk

def getCombinationKeys(d, target):
    retk = []

    for i in tqdm.tqdm(range(len(d.values())), desc='Looping lengths', leave=False):
        for j in itertools.combinations(d.values(), i):
            if sum(j) == target:
                ks = [reverseLookupKeys(d, m) for m in j]
                if len(ks) > 0 and ks[0]: retk.append(ks)
    return retk

## test
# s = {'dave':1, 'fred':2, 'alice':3, 'trey': 4, 'jake': 5, 'sonia': 6, 'matt': 7, 'nick': 8}
# print(getCombinationKeys(s, 8))


def printNumRowDict(d, tags=taglist):
    print('\n')
    for k,v in d.items():
        if k not in tags:
            print(str(k) + ';' + str(v))

keyspread = {}
c=0

def checkCalc(d, actualValTag, *tags):
    addvals = []
    for t in tags:
        try:
            if t[0] == '-':
                addvals.append( d[t[1:]] * -1)
            else:
                addvals.append(d[t])
        except KeyError:
            pass
    # AccountsPayable = d.AccountsPayable if "AccountsPayable" in d.keys() else 0
    # AccruedLiabilities = d.AccruedLiabilities if "AccruedLiabilities" in d.keys() else 0
    if '' in addvals: addvals.remove('')
    if None in addvals: addvals.remove(None)


    calc = sum(addvals)
    try:
        rem = d[actualValTag]-calc
    except KeyError:
        return
    
    if rem != 0:
        locald = dict(d)
        ## remove all keys whose values are 0
        for k,v, in d.items():
            if v == 0:
                del locald[k]
        try:
            keyspread[str(len(locald.values()))] += 1
        except KeyError:
            keyspread[str(len(locald.values()))] = 1
        if len(locald.values()) < 27: 
            poss = getCombinationKeys(locald, rem)
            if len(poss) > 0:
                printNumRowDict(locald)
                print('Remaining:', rem)
                print(actualValTag)
                print('Possibilites:', poss)
                # global c
                # if c < 30:
                #     c += 1
                # else:
                #     raise KeyError
        return False
    else:
        return True


def analyzeNUMFormulae():
    loadedQuarters = dbm.getLoadedQuarters()
    skipqcount = 5

    balancedcount=0
    unbalancedcount=0


    for q in tqdm.tqdm(loadedQuarters, desc='Analyzing quarters'):
        # if skipqcount > 0:
        #     skipqcount -= 1
        #     continue

        companies = dbm.dbc.execute(f'SELECT DISTINCT s.adsh FROM {dbm.getTableString("financial_stmts_sub_data_set_edgar_d")} s JOIN {dbm.getTableString("financial_stmts_num_data_set_edgar_d")} n, edgar_sub_balance_status b ON s.adsh=n.adsh and s.adsh=b.adsh WHERE b.status=0 AND fy=? AND fp=? AND exchange IS NOT NULL AND coreg=\'\' AND qtrs=\'0\' AND n.version LIKE \'%gaap%\'', (q[:4], q[4:].upper()))
        # print(len(companies))
        # print(q)
        # print('keyspread', keyspread)
        for c in tqdm.tqdm(companies, desc='Companies', leave=False):
            numValues = dbm.dbc.execute(f'SELECT * FROM {dbm.getTableString("financial_stmts_num_data_set_edgar_d")} WHERE adsh=?', (c.adsh,))
            ## map to tag names
            ddatedict = {}
            for n in numValues:
                if n.ddate not in ddatedict.keys(): ddatedict[n.ddate] = {}
                ddatedict[n.ddate][n.tag] = n.value if n.value != '' and n.value is not None else 0

            ddatedict = recdotdict(ddatedict)

            ## loop ddates
            for dd,d in ddatedict.items():
                # AccountsPayable = d.AccountsPayable if "AccountsPayable" in d.keys() else 0
                # AccruedLiabilities = d.AccruedLiabilities if "AccruedLiabilities" in d.keys() else 0
                # calc_LiabilitiesCurrent = AccountsPayable + AccruedLiabilities
                # if d.LiabilitiesCurrent != calc_LiabilitiesCurrent:
                #     printNumRowDict(d)
                #     print('Remaining:', d.LiabilitiesCurrent-calc_LiabilitiesCurrent)
                #     raise 'miss'

                balanced = True
                balanced = balanced and checkCalc(d, 'LiabilitiesCurrent', *LiabilitiesCurrentTags)
                balanced = balanced and checkCalc(d, 'AssetsCurrent', *AssetsCurrentTags)
                balanced = balanced and checkCalc(d, 'StockholdersEquity', *StockholdersEquityTags)
                balanced = balanced and checkCalc(d, 'Assets', *AssetTags)
                balanced = balanced and checkCalc(d, 'LiabilitiesAndStockholdersEquity', *LiabilitiesAndStockholdersEquityTags)

                remkeys = [i for i in d.keys() if i not in taglist]
                # print(len(remkeys),remkeys)
                
                dryrun = False
                stmt = 'UPDATE edgar_sub_balance_status SET status=? WHERE adsh="'+c.adsh+'" AND ddate="'+dd+'"'
                if balanced:
                    balancedcount+=1
                    print(remkeys)
                    if len(remkeys) == 0:
                        if not dryrun: dbm.dbc.execute(stmt, (1, )) ## submission is completely balanced
                    else:
                        allzero = True
                        for k in remkeys:
                            allzero = allzero and d[k] == 0

                        if allzero:
                            if not dryrun: dbm.dbc.execute(stmt, (3,)) ## unusable remaining key/values
                        else:
                            if not dryrun: dbm.dbc.execute(stmt, (2,)) ## remaining key/values could add up to something existing
                else:
                    # print('not balanced')
                    if len(remkeys) == 0:
                        unbalancedcount+=1
                        dbm.dbc.execute(stmt, (-1, )) ## unbalanced and all keys used
                    pass
                    
    print('New balanced', balancedcount)
    print('New unbalanced', unbalancedcount)






def getKeys(dct):
    keys = list(dct.keys())
    try:
        keys.remove('value')
        keys.remove('debit')
    except ValueError:
        pass

    if len(keys) == 0: return

    retkeys = list(keys)
    for k in keys:
        r = getKeys(dct[k])
        if r: retkeys.extend(r)

    return retkeys


if __name__ == '__main__':
    # analyzeNUMFormulae()

    ## check tags
    with open(os.path.join(path, 'miscellaneous/financialtagging/outp.txt'), 'r') as f:
        tagdict = json.load(f)
        # print(tagdict)
        ## gather tags from dict
        tagdictkeys = getKeys(tagdict)
        # print(list(tagdict.keys()))

        ## remove deprecated tags
        deprecatedtags = dbm.dbc.execute(f'select distinct tag from {dbm.getTableString("financial_stmts_tag_data_set_edgar_d")} where abstract=0 and tlabel like \'%deprecated%\'')
        for t in deprecatedtags:
            try:
                taglist.remove(t.tag)
            except ValueError:
                pass
        print(deprecatedtags)

        print('missing from tagdict ####################################################################################')
        for t in taglist:
            if t not in tagdictkeys:
                print(t)
        # print('missing from taglist #####################################################################################')
        # for t in tagdictkeys:
        #     if t not in taglist:
        #         print(t)

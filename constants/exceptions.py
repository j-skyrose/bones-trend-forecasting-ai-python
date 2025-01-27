class APILimitReached(Exception):
    pass

class APIError(Exception):
    pass

class APITimeout(Exception):
    pass

class LocationNotSpecificed(Exception):
    pass

class SufficientlyUpdatedDataNotAvailable(Exception):
    pass

class NoData(Exception):
    pass

class AnchorDateAheadOfLastDataDate(Exception):
    pass

class InsufficientDataAvailable(Exception):
    pass

class ArgumentError(Exception):
    pass

class NotSupportedYet(Exception):
    pass

class InsufficientInstances(Exception):
    pass

class DamageDetected(Exception):
    pass

class NotMarketDay(Exception):
    pass

class DatabaseStructureChanged(Exception):
    pass

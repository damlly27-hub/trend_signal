class TrendServiceError(Exception):
    """Base exception for Trend use cases."""


class DuplicateTrendError(TrendServiceError):
    pass


class DuplicateAliasError(TrendServiceError):
    pass


class TrendNotFoundError(TrendServiceError):
    pass


class TrendNotCollectibleError(TrendServiceError):
    pass


class CollectionFailedError(TrendServiceError):
    pass


"""Custom exceptions for the replenishment manager."""


class ReplenishmentError(Exception):
    """Base exception for replenishment manager."""

    pass


class ForecastingError(ReplenishmentError):
    """Base exception for forecasting service."""

    pass


class ModelNotFoundError(ForecastingError):
    """Raised when a model is not found."""

    pass


class InvalidInputError(ForecastingError):
    """Raised when input validation fails."""

    pass


class DataLoadError(ReplenishmentError):
    """Raised when data loading fails."""

    pass


class ReplenishmentPolicyError(ReplenishmentError):
    """Raised when replenishment policy calculation fails."""

    pass


class MarkdownPolicyError(ReplenishmentError):
    """Raised when markdown policy calculation fails."""

    pass


class ConfigurationError(ReplenishmentError):
    """Raised when configuration is invalid."""

    pass


"""Forecasting service configuration."""

from shared.config import ForecastingConfig, get_config


def get_forecasting_config() -> ForecastingConfig:
    """Get forecasting configuration."""
    config = get_config()
    return config.models.forecasting


"""Baseline forecasting models (naive methods)."""

from typing import List, Optional

import pandas as pd
import numpy as np

from services.forecasting.models.base import BaseForecastModel
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class LastValueForecaster(BaseForecastModel):
    """Forecast using the last observed value."""

    def __init__(self):
        super().__init__(name="last_value")
        self.last_value: Optional[float] = None

    def train(
        self,
        train_data: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """Train the model (simply store the last value)."""
        if target_col not in train_data.columns:
            raise ValueError(f"Target column '{target_col}' not found in training data")
        
        self.last_value = train_data[target_col].iloc[-1]
        self.is_trained = True
        logger.info("LastValueForecaster trained", last_value=self.last_value)

    def predict(
        self,
        data: pd.DataFrame,
        horizon: int = 1,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """Generate forecasts using last value."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        if self.last_value is None:
            raise ValueError("Model has no stored value")

        # Generate forecasts for the horizon
        forecasts = [self.last_value] * horizon
        
        # Create result DataFrame
        result = pd.DataFrame({
            'predicted_demand': forecasts,
            'lower_bound': forecasts,  # No uncertainty for baseline
            'upper_bound': forecasts,
        })
        
        return result

    def save(self, path: str) -> None:
        """Save model state."""
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({'last_value': self.last_value, 'is_trained': self.is_trained}, f)

    def load(self, path: str) -> None:
        """Load model state."""
        import pickle
        with open(path, 'rb') as f:
            state = pickle.load(f)
            self.last_value = state['last_value']
            self.is_trained = state['is_trained']


class MovingAverageForecaster(BaseForecastModel):
    """Forecast using moving average of last N periods."""

    def __init__(self, window: int = 7):
        """
        Initialize moving average forecaster.

        Args:
            window: Number of periods to average
        """
        super().__init__(name=f"moving_average_{window}")
        self.window = window
        self.mean_value: Optional[float] = None

    def train(
        self,
        train_data: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """Train the model (compute moving average)."""
        if target_col not in train_data.columns:
            raise ValueError(f"Target column '{target_col}' not found in training data")
        
        # Use last window values for moving average
        values = train_data[target_col].tail(self.window)
        self.mean_value = values.mean()
        self.is_trained = True
        logger.info("MovingAverageForecaster trained", window=self.window, mean_value=self.mean_value)

    def predict(
        self,
        data: pd.DataFrame,
        horizon: int = 1,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """Generate forecasts using moving average."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        if self.mean_value is None:
            raise ValueError("Model has no stored mean value")

        # Generate forecasts
        forecasts = [self.mean_value] * horizon
        
        # Create result DataFrame
        result = pd.DataFrame({
            'predicted_demand': forecasts,
            'lower_bound': forecasts,
            'upper_bound': forecasts,
        })
        
        return result

    def save(self, path: str) -> None:
        """Save model state."""
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'window': self.window,
                'mean_value': self.mean_value,
                'is_trained': self.is_trained
            }, f)

    def load(self, path: str) -> None:
        """Load model state."""
        import pickle
        with open(path, 'rb') as f:
            state = pickle.load(f)
            self.window = state['window']
            self.mean_value = state['mean_value']
            self.is_trained = state['is_trained']


class SeasonalNaiveForecaster(BaseForecastModel):
    """Forecast using value from same period in previous season (e.g., same day last week)."""

    def __init__(self, season_length: int = 7):
        """
        Initialize seasonal naive forecaster.

        Args:
            season_length: Length of the season (e.g., 7 for weekly seasonality)
        """
        super().__init__(name=f"seasonal_naive_{season_length}")
        self.season_length = season_length
        self.seasonal_values: Optional[List[float]] = None

    def train(
        self,
        train_data: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """Train the model (store seasonal pattern)."""
        if target_col not in train_data.columns:
            raise ValueError(f"Target column '{target_col}' not found in training data")
        
        # Store last season_length values
        values = train_data[target_col].tail(self.season_length)
        self.seasonal_values = values.tolist()
        self.is_trained = True
        logger.info("SeasonalNaiveForecaster trained", season_length=self.season_length)

    def predict(
        self,
        data: pd.DataFrame,
        horizon: int = 1,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """Generate forecasts using seasonal pattern."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        if self.seasonal_values is None:
            raise ValueError("Model has no stored seasonal values")

        # Generate forecasts by cycling through seasonal pattern
        forecasts = []
        for i in range(horizon):
            idx = i % len(self.seasonal_values)
            forecasts.append(self.seasonal_values[idx])
        
        # Create result DataFrame
        result = pd.DataFrame({
            'predicted_demand': forecasts,
            'lower_bound': forecasts,
            'upper_bound': forecasts,
        })
        
        return result

    def save(self, path: str) -> None:
        """Save model state."""
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'season_length': self.season_length,
                'seasonal_values': self.seasonal_values,
                'is_trained': self.is_trained
            }, f)

    def load(self, path: str) -> None:
        """Load model state."""
        import pickle
        with open(path, 'rb') as f:
            state = pickle.load(f)
            self.season_length = state['season_length']
            self.seasonal_values = state['seasonal_values']
            self.is_trained = state['is_trained']


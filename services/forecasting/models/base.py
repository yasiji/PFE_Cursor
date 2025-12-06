"""Base class for forecasting models."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd

from shared.logging_setup import get_logger

logger = get_logger(__name__)


class BaseForecastModel(ABC):
    """Base class for all forecasting models."""

    def __init__(self, name: str = "base_model"):
        """
        Initialize base forecast model.

        Args:
            name: Name of the model
        """
        self.name = name
        self.is_trained = False

    @abstractmethod
    def train(
        self,
        train_data: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        Train the forecasting model.

        Args:
            train_data: Training data DataFrame
            target_col: Name of the target column
            feature_cols: List of feature column names (if None, use all except target)
            **kwargs: Additional training parameters
        """
        pass

    @abstractmethod
    def predict(
        self,
        data: pd.DataFrame,
        horizon: int = 1,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Generate forecasts.

        Args:
            data: Input data DataFrame
            horizon: Forecast horizon (number of periods ahead)
            feature_cols: List of feature column names
            **kwargs: Additional prediction parameters

        Returns:
            DataFrame with forecasts (columns: date, predicted_demand, lower_bound, upper_bound)
        """
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """
        Save model to disk.

        Args:
            path: Path to save the model
        """
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """
        Load model from disk.

        Args:
            path: Path to load the model from
        """
        pass

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores (if available).

        Returns:
            Dictionary mapping feature names to importance scores, or None if not available
        """
        return None


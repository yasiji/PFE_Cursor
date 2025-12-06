"""Forecast evaluation metrics and utilities."""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from shared.logging_setup import get_logger

logger = get_logger(__name__)


class ForecastEvaluator:
    """Evaluate forecast accuracy using various metrics."""

    @staticmethod
    def mae(y_true: pd.Series, y_pred: pd.Series) -> float:
        """
        Calculate Mean Absolute Error.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            MAE value
        """
        return np.mean(np.abs(y_true - y_pred))

    @staticmethod
    def rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
        """
        Calculate Root Mean Squared Error.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            RMSE value
        """
        return np.sqrt(np.mean((y_true - y_pred) ** 2))

    @staticmethod
    def mape(y_true: pd.Series, y_pred: pd.Series) -> float:
        """
        Calculate Mean Absolute Percentage Error.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            MAPE value (as percentage)
        """
        # Avoid division by zero
        mask = y_true != 0
        if mask.sum() == 0:
            return np.nan
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

    @staticmethod
    def wape(y_true: pd.Series, y_pred: pd.Series) -> float:
        """
        Calculate Weighted Absolute Percentage Error.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            WAPE value (as percentage)
        """
        total_true = y_true.sum()
        if total_true == 0:
            return np.nan
        return (np.abs(y_true - y_pred).sum() / total_true) * 100

    @staticmethod
    def bias(y_true: pd.Series, y_pred: pd.Series) -> float:
        """
        Calculate forecast bias (mean signed error).

        Positive bias = over-forecasting, Negative bias = under-forecasting.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            Bias value
        """
        return np.mean(y_pred - y_true)

    @staticmethod
    def evaluate(
        y_true: pd.Series,
        y_pred: pd.Series,
        metrics: Optional[list[str]] = None
    ) -> Dict[str, float]:
        """
        Evaluate forecasts using multiple metrics.

        Args:
            y_true: True values
            y_pred: Predicted values
            metrics: List of metrics to compute. If None, compute all.

        Returns:
            Dictionary of metric names and values
        """
        if metrics is None:
            metrics = ['mae', 'rmse', 'mape', 'wape', 'bias']

        results = {}
        
        if 'mae' in metrics:
            results['mae'] = ForecastEvaluator.mae(y_true, y_pred)
        if 'rmse' in metrics:
            results['rmse'] = ForecastEvaluator.rmse(y_true, y_pred)
        if 'mape' in metrics:
            results['mape'] = ForecastEvaluator.mape(y_true, y_pred)
        if 'wape' in metrics:
            results['wape'] = ForecastEvaluator.wape(y_true, y_pred)
        if 'bias' in metrics:
            results['bias'] = ForecastEvaluator.bias(y_true, y_pred)

        return results

    @staticmethod
    def evaluate_by_group(
        df: pd.DataFrame,
        y_true_col: str,
        y_pred_col: str,
        group_col: Optional[str] = None,
        metrics: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """
        Evaluate forecasts grouped by a column (e.g., store, SKU).

        Args:
            df: DataFrame with true and predicted values
            y_true_col: Column name for true values
            y_pred_col: Column name for predicted values
            group_col: Column to group by (e.g., 'store_id', 'sku_id')
            metrics: List of metrics to compute

        Returns:
            DataFrame with metrics per group
        """
        if group_col is None:
            # Evaluate overall
            results = ForecastEvaluator.evaluate(
                df[y_true_col],
                df[y_pred_col],
                metrics
            )
            return pd.DataFrame([results])

        # Evaluate per group
        results = []
        for group_name, group_df in df.groupby(group_col):
            group_results = ForecastEvaluator.evaluate(
                group_df[y_true_col],
                group_df[y_pred_col],
                metrics
            )
            group_results[group_col] = group_name
            results.append(group_results)

        return pd.DataFrame(results)


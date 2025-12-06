"""Feature engineering pipeline for forecasting models."""

from typing import List, Optional

import pandas as pd
import numpy as np

from shared.utils import (
    add_calendar_features,
    add_lag_features,
    add_rolling_features
)
from shared.column_mappings import COLUMN_MAPPINGS
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def create_forecast_features(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    store_col: str,
    sku_col: str,
    include_calendar: bool = True,
    include_lags: bool = True,
    include_rolling: bool = True,
    include_weather: bool = True,
    include_promo: bool = True,
    lags: Optional[List[int]] = None,
    rolling_windows: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Create comprehensive feature set for forecasting.

    Args:
        df: Input DataFrame with time series data
        date_col: Name of the date column
        target_col: Name of the target column (e.g., 'demand', 'sales')
        store_col: Name of the store column
        sku_col: Name of the SKU/product column
        include_calendar: Whether to include calendar features
        include_lags: Whether to include lag features
        include_rolling: Whether to include rolling window features
        include_weather: Whether to include weather features
        include_promo: Whether to include promotion features
        lags: List of lag periods (default: [1, 7, 14, 28])
        rolling_windows: List of rolling window sizes (default: [7, 14, 28])

    Returns:
        DataFrame with engineered features
    """
    df = df.copy()

    # Default lag and window values
    if lags is None:
        lags = [1, 7, 14, 28]
    if rolling_windows is None:
        rolling_windows = [7, 14, 28]

    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    # Sort by store, SKU, and date
    df = df.sort_values([store_col, sku_col, date_col]).reset_index(drop=True)

    # Calendar features
    if include_calendar:
        logger.info("Adding calendar features")
        df = add_calendar_features(df, date_col)

    # Lag features
    if include_lags:
        logger.info(f"Adding lag features: {lags}")
        df = add_lag_features(
            df,
            value_col=target_col,
            group_cols=[store_col, sku_col],
            lags=lags
        )

    # Rolling window features
    if include_rolling:
        logger.info(f"Adding rolling features: {rolling_windows}")
        df = add_rolling_features(
            df,
            value_col=target_col,
            group_cols=[store_col, sku_col],
            windows=rolling_windows
        )

    # Weather features (if available)
    if include_weather:
        weather_col = COLUMN_MAPPINGS.get('weather_col', 'avg_temperature')
        if weather_col in df.columns:
            logger.info("Adding weather features")
            # Temperature features
            df[f'{weather_col}_lag_1'] = df.groupby([store_col, sku_col])[weather_col].shift(1)
            df[f'{weather_col}_rolling_mean_7'] = df.groupby([store_col, sku_col])[weather_col].transform(
                lambda x: x.rolling(7, min_periods=1).mean()
            )
            
            # Additional weather columns if available
            for col in ['precpt', 'avg_humidity', 'avg_wind_level']:
                if col in df.columns:
                    df[f'{col}_lag_1'] = df.groupby([store_col, sku_col])[col].shift(1)

    # Promotion features (if available)
    if include_promo:
        promo_col = COLUMN_MAPPINGS.get('promo_col', 'discount')
        if promo_col in df.columns:
            logger.info("Adding promotion features")
            df[f'{promo_col}_lag_1'] = df.groupby([store_col, sku_col])[promo_col].shift(1)
            df[f'{promo_col}_rolling_mean_7'] = df.groupby([store_col, sku_col])[promo_col].transform(
                lambda x: x.rolling(7, min_periods=1).mean()
            )
            
            # Binary flag for active promotion
            df[f'{promo_col}_active'] = (df[promo_col] > 0).astype(int)

    # Holiday and activity flags (if available)
    for flag_col in ['holiday_flag', 'activity_flag']:
        if flag_col in df.columns:
            df[f'{flag_col}_lag_1'] = df.groupby([store_col, sku_col])[flag_col].shift(1)

    # Store and SKU encoding (categorical features)
    df[f'{store_col}_encoded'] = pd.Categorical(df[store_col]).codes
    df[f'{sku_col}_encoded'] = pd.Categorical(df[sku_col]).codes

    # Category features (if available)
    category_col = COLUMN_MAPPINGS.get('category_col', 'first_category_id')
    if category_col in df.columns:
        df[f'{category_col}_encoded'] = pd.Categorical(df[category_col]).codes

    logger.info(f"Feature engineering complete. Total features: {len(df.columns)}")

    return df


def get_feature_columns(
    df: pd.DataFrame,
    exclude_cols: Optional[List[str]] = None
) -> List[str]:
    """
    Get list of feature columns (numeric columns excluding target and metadata).

    Args:
        df: DataFrame with features
        exclude_cols: Columns to exclude (e.g., ['date', 'store_id', 'sku_id', 'demand'])

    Returns:
        List of feature column names
    """
    if exclude_cols is None:
        exclude_cols = []

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Exclude specified columns
    feature_cols = [col for col in numeric_cols if col not in exclude_cols]

    return feature_cols


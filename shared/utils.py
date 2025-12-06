"""Shared utility functions."""

from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd

from shared.logging_setup import get_logger

logger = get_logger(__name__)


def create_date_range(start_date: str | datetime, end_date: str | datetime, freq: str = 'D') -> pd.DatetimeIndex:
    """
    Create a date range.

    Args:
        start_date: Start date (string or datetime)
        end_date: End date (string or datetime)
        freq: Frequency string (default: 'D' for daily)

    Returns:
        DatetimeIndex
    """
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    return pd.date_range(start=start_date, end=end_date, freq=freq)


def add_calendar_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """
    Add calendar features to a DataFrame.

    Args:
        df: Input DataFrame
        date_col: Name of the date column

    Returns:
        DataFrame with added calendar features
    """
    df = df.copy()
    
    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found in DataFrame")
    
    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    
    # Extract calendar features
    df['year'] = df[date_col].dt.year
    df['month'] = df[date_col].dt.month
    df['day'] = df[date_col].dt.day
    df['dayofweek'] = df[date_col].dt.dayofweek
    df['dayofyear'] = df[date_col].dt.dayofyear
    df['week'] = df[date_col].dt.isocalendar().week
    df['quarter'] = df[date_col].dt.quarter
    
    # Binary flags
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    df['is_month_start'] = df[date_col].dt.is_month_start.astype(int)
    df['is_month_end'] = df[date_col].dt.is_month_end.astype(int)
    df['is_quarter_start'] = df[date_col].dt.is_quarter_start.astype(int)
    df['is_quarter_end'] = df[date_col].dt.is_quarter_end.astype(int)
    
    return df


def add_lag_features(
    df: pd.DataFrame,
    value_col: str,
    group_cols: Optional[List[str]] = None,
    lags: List[int] = [1, 7, 14, 28]
) -> pd.DataFrame:
    """
    Add lag features to a DataFrame.

    Args:
        df: Input DataFrame (must be sorted by date)
        value_col: Name of the value column to lag
        group_cols: Columns to group by (e.g., ['store_id', 'sku_id'])
        lags: List of lag periods to create

    Returns:
        DataFrame with added lag features
    """
    df = df.copy()
    
    if group_cols is None:
        group_cols = []
    
    # Sort by group columns and date (if date column exists)
    date_cols = df.select_dtypes(include=['datetime64']).columns
    if len(date_cols) > 0:
        sort_cols = group_cols + [date_cols[0]]
    else:
        sort_cols = group_cols
    df = df.sort_values(sort_cols).reset_index(drop=True)
    
    # Create lag features
    for lag in lags:
        if group_cols:
            df[f'{value_col}_lag_{lag}'] = df.groupby(group_cols)[value_col].shift(lag)
        else:
            df[f'{value_col}_lag_{lag}'] = df[value_col].shift(lag)
    
    return df


def add_rolling_features(
    df: pd.DataFrame,
    value_col: str,
    group_cols: Optional[List[str]] = None,
    windows: List[int] = [7, 14, 28]
) -> pd.DataFrame:
    """
    Add rolling window features to a DataFrame.

    Args:
        df: Input DataFrame
        value_col: Name of the value column
        group_cols: Columns to group by
        windows: List of window sizes

    Returns:
        DataFrame with added rolling features
    """
    df = df.copy()
    
    if group_cols is None:
        group_cols = []
    
    # Sort by group columns and date
    date_cols = df.select_dtypes(include=['datetime64']).columns
    if len(date_cols) > 0:
        sort_cols = group_cols + [date_cols[0]]
    else:
        sort_cols = group_cols
    df = df.sort_values(sort_cols).reset_index(drop=True)
    
    # Create rolling features
    for window in windows:
        if group_cols:
            grouped = df.groupby(group_cols)[value_col]
        else:
            grouped = df[value_col]
        
        df[f'{value_col}_rolling_mean_{window}'] = grouped.transform(lambda x: x.rolling(window, min_periods=1).mean())
        df[f'{value_col}_rolling_std_{window}'] = grouped.transform(lambda x: x.rolling(window, min_periods=1).std())
        df[f'{value_col}_rolling_max_{window}'] = grouped.transform(lambda x: x.rolling(window, min_periods=1).max())
        df[f'{value_col}_rolling_min_{window}'] = grouped.transform(lambda x: x.rolling(window, min_periods=1).min())
    
    return df


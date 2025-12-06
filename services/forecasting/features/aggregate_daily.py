"""Aggregate time series data to daily level."""

from typing import List, Optional

import pandas as pd

from shared.logging_setup import get_logger

logger = get_logger(__name__)


def aggregate_to_daily(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_cols: Optional[List[str]] = None,
    agg_func: str = 'sum'
) -> pd.DataFrame:
    """
    Aggregate data to daily level per store-SKU (or other grouping).

    Args:
        df: Input DataFrame with time series data
        date_col: Name of the date/timestamp column
        value_col: Name of the value column to aggregate
        group_cols: Columns to group by (e.g., ['store_id', 'sku_id'])
        agg_func: Aggregation function ('sum', 'mean', 'max', 'min', 'count')

    Returns:
        DataFrame aggregated to daily level
    """
    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    
    # Extract date (remove time component)
    df = df.copy()
    df['_date'] = df[date_col].dt.date
    df['_date'] = pd.to_datetime(df['_date'])
    
    # Determine grouping columns
    if group_cols is None:
        group_cols = []
    
    grouping_cols = group_cols + ['_date']
    
    # Validate columns exist
    missing_cols = [col for col in grouping_cols + [value_col] if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Columns not found in DataFrame: {missing_cols}")
    
    # Aggregate
    if agg_func == 'sum':
        result = df.groupby(grouping_cols)[value_col].sum().reset_index()
    elif agg_func == 'mean':
        result = df.groupby(grouping_cols)[value_col].mean().reset_index()
    elif agg_func == 'max':
        result = df.groupby(grouping_cols)[value_col].max().reset_index()
    elif agg_func == 'min':
        result = df.groupby(grouping_cols)[value_col].min().reset_index()
    elif agg_func == 'count':
        result = df.groupby(grouping_cols)[value_col].count().reset_index()
    else:
        raise ValueError(f"Unsupported aggregation function: {agg_func}")
    
    # Rename date column back
    result = result.rename(columns={'_date': date_col})
    
    logger.info(
        "Aggregated to daily level",
        original_rows=len(df),
        aggregated_rows=len(result),
        group_cols=group_cols,
        agg_func=agg_func
    )
    
    return result


def validate_aggregation(
    original_df: pd.DataFrame,
    aggregated_df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_cols: Optional[List[str]] = None,
    tolerance: float = 1e-6
) -> bool:
    """
    Validate that aggregation totals match original data.

    Args:
        original_df: Original DataFrame before aggregation
        aggregated_df: Aggregated DataFrame
        date_col: Name of the date column
        value_col: Name of the value column
        group_cols: Columns used for grouping
        tolerance: Tolerance for floating point comparison

    Returns:
        True if validation passes, raises ValueError if not
    """
    # Calculate totals
    original_total = original_df[value_col].sum()
    
    if group_cols:
        # If grouped, sum should match per group
        agg_total = aggregated_df[value_col].sum()
    else:
        agg_total = aggregated_df[value_col].sum()
    
    # Compare
    diff = abs(original_total - agg_total)
    
    if diff > tolerance:
        raise ValueError(
            f"Aggregation validation failed: "
            f"Original total: {original_total}, "
            f"Aggregated total: {agg_total}, "
            f"Difference: {diff}"
        )
    
    logger.info("Aggregation validation passed", original_total=original_total, agg_total=agg_total)
    return True


def create_daily_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_cols: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fill_missing: bool = True,
    fill_value: float = 0.0
) -> pd.DataFrame:
    """
    Create a complete daily time series with all dates filled.

    Args:
        df: Input DataFrame
        date_col: Name of the date column
        value_col: Name of the value column
        group_cols: Columns to group by (e.g., ['store_id', 'sku_id'])
        start_date: Start date for the series (if None, use min date in data)
        end_date: End date for the series (if None, use max date in data)
        fill_missing: Whether to fill missing dates with fill_value
        fill_value: Value to use for missing dates

    Returns:
        DataFrame with complete daily series
    """
    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    
    # Determine date range
    if start_date is None:
        start_date = df[date_col].min()
    else:
        start_date = pd.to_datetime(start_date)
    
    if end_date is None:
        end_date = df[date_col].max()
    else:
        end_date = pd.to_datetime(end_date)
    
    # Create date range
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Get unique combinations of group columns
    if group_cols:
        groups = df[group_cols].drop_duplicates()
    else:
        groups = pd.DataFrame({'dummy': [1]})  # Single group
    
    # Create cartesian product of dates and groups
    date_df = pd.DataFrame({date_col: date_range})
    
    if group_cols:
        # Merge groups with dates
        complete_df = groups.merge(date_df, how='cross')
    else:
        complete_df = date_df.copy()
    
    # Merge with original data
    result = complete_df.merge(
        df[[date_col] + group_cols + [value_col]],
        on=[date_col] + group_cols,
        how='left'
    )
    
    # Fill missing values if requested
    if fill_missing:
        result[value_col] = result[value_col].fillna(fill_value)
    
    # Sort
    sort_cols = group_cols + [date_col]
    result = result.sort_values(sort_cols).reset_index(drop=True)
    
    logger.info(
        "Created daily series",
        start_date=start_date,
        end_date=end_date,
        total_days=len(date_range),
        groups=len(groups) if group_cols else 1,
        total_rows=len(result)
    )
    
    return result


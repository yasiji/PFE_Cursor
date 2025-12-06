"""Tests for daily aggregation functions."""

import pytest
import pandas as pd
import numpy as np

from services.forecasting.features.aggregate_daily import (
    aggregate_to_daily,
    validate_aggregation,
    create_daily_series,
)


@pytest.fixture
def hourly_data():
    """Create sample hourly data."""
    dates = pd.date_range('2024-01-01', periods=48, freq='h')  # 2 days of hourly data
    return pd.DataFrame({
        'timestamp': dates,
        'store_id': ['A'] * 24 + ['B'] * 24,
        'sku_id': ['SKU1'] * 48,
        'sales': np.random.randint(1, 10, size=48)
    })


def test_aggregate_to_daily_sum(hourly_data):
    """Test daily aggregation with sum."""
    result = aggregate_to_daily(
        hourly_data,
        date_col='timestamp',
        value_col='sales',
        group_cols=['store_id', 'sku_id'],
        agg_func='sum'
    )
    
    # Should have 2 rows (2 days) per store-SKU combination
    # hourly_data has: 2 stores, 1 SKU, 2 days = 2 rows total
    assert len(result) == 2  # 2 stores * 1 SKU * 2 days / 2 days = 2 rows
    
    # Check that totals match
    original_total = hourly_data['sales'].sum()
    agg_total = result['sales'].sum()
    assert original_total == agg_total


def test_aggregate_to_daily_mean(hourly_data):
    """Test daily aggregation with mean."""
    result = aggregate_to_daily(
        hourly_data,
        date_col='timestamp',
        value_col='sales',
        group_cols=['store_id', 'sku_id'],
        agg_func='mean'
    )
    
    # Should have 2 rows (2 days) per store-SKU combination
    assert len(result) == 2
    # Mean should be reasonable
    assert result['sales'].min() >= 0


def test_validate_aggregation(hourly_data):
    """Test aggregation validation."""
    aggregated = aggregate_to_daily(
        hourly_data,
        date_col='timestamp',
        value_col='sales',
        group_cols=['store_id', 'sku_id'],
        agg_func='sum'
    )
    
    # Should pass validation
    assert validate_aggregation(
        hourly_data,
        aggregated,
        date_col='timestamp',
        value_col='sales',
        group_cols=['store_id', 'sku_id']
    )


def test_create_daily_series():
    """Test creating complete daily series."""
    # Create sparse data (missing some dates)
    df = pd.DataFrame({
        'date': pd.to_datetime(['2024-01-01', '2024-01-03', '2024-01-05']),
        'store_id': ['A', 'A', 'A'],
        'sales': [10, 20, 30]
    })
    
    result = create_daily_series(
        df,
        date_col='date',
        value_col='sales',
        group_cols=['store_id'],
        start_date='2024-01-01',
        end_date='2024-01-05',
        fill_missing=True,
        fill_value=0.0
    )
    
    # Should have all 5 days
    assert len(result) == 5
    assert result['date'].nunique() == 5
    
    # Missing dates should be filled with 0
    assert result.loc[result['date'] == '2024-01-02', 'sales'].iloc[0] == 0.0
    assert result.loc[result['date'] == '2024-01-04', 'sales'].iloc[0] == 0.0


def test_aggregate_no_grouping():
    """Test aggregation without grouping columns."""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=48, freq='h'),
        'sales': np.random.randint(1, 10, size=48)
    })
    
    result = aggregate_to_daily(
        df,
        date_col='timestamp',
        value_col='sales',
        group_cols=None,
        agg_func='sum'
    )
    
    # Should have 2 rows (2 days)
    assert len(result) == 2
    
    # Totals should match
    assert df['sales'].sum() == result['sales'].sum()


"""Tests for shared utility functions."""

import pytest
import pandas as pd

from shared.utils import (
    create_date_range,
    add_calendar_features,
    add_lag_features,
    add_rolling_features,
)


def test_create_date_range():
    """Test date range creation."""
    dates = create_date_range('2024-01-01', '2024-01-05', freq='D')
    assert len(dates) == 5
    assert dates[0] == pd.Timestamp('2024-01-01')
    assert dates[-1] == pd.Timestamp('2024-01-05')


def test_add_calendar_features():
    """Test calendar feature addition."""
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'value': range(10)
    })
    
    result = add_calendar_features(df, 'date')
    
    assert 'year' in result.columns
    assert 'month' in result.columns
    assert 'dayofweek' in result.columns
    assert 'is_weekend' in result.columns
    assert result['is_weekend'].dtype == 'int64'


def test_add_lag_features():
    """Test lag feature addition."""
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'store_id': ['A'] * 5 + ['B'] * 5,
        'demand': range(10)
    })
    
    result = add_lag_features(df, 'demand', group_cols=['store_id'], lags=[1, 2])
    
    assert 'demand_lag_1' in result.columns
    assert 'demand_lag_2' in result.columns
    # First value in each group should have NaN for lag_1
    assert pd.isna(result.loc[0, 'demand_lag_1'])
    assert pd.isna(result.loc[5, 'demand_lag_1'])


def test_add_rolling_features():
    """Test rolling feature addition."""
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'demand': range(10)
    })
    
    result = add_rolling_features(df, 'demand', windows=[3, 5])
    
    assert 'demand_rolling_mean_3' in result.columns
    assert 'demand_rolling_mean_5' in result.columns
    assert 'demand_rolling_std_3' in result.columns
    assert 'demand_rolling_max_3' in result.columns
    assert 'demand_rolling_min_3' in result.columns


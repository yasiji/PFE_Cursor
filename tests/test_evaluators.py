"""Tests for forecast evaluation metrics."""

import pytest
import pandas as pd
import numpy as np

from services.forecasting.evaluators import ForecastEvaluator


@pytest.fixture
def sample_forecasts():
    """Create sample true and predicted values."""
    y_true = pd.Series([10, 20, 30, 40, 50])
    y_pred = pd.Series([12, 18, 32, 38, 52])
    return y_true, y_pred


def test_mae(sample_forecasts):
    """Test Mean Absolute Error."""
    y_true, y_pred = sample_forecasts
    mae = ForecastEvaluator.mae(y_true, y_pred)
    expected = np.mean([2, 2, 2, 2, 2])  # |12-10|, |18-20|, etc.
    assert mae == pytest.approx(expected)


def test_rmse(sample_forecasts):
    """Test Root Mean Squared Error."""
    y_true, y_pred = sample_forecasts
    rmse = ForecastEvaluator.rmse(y_true, y_pred)
    expected = np.sqrt(np.mean([4, 4, 4, 4, 4]))  # (12-10)^2, etc.
    assert rmse == pytest.approx(expected)


def test_mape(sample_forecasts):
    """Test Mean Absolute Percentage Error."""
    y_true, y_pred = sample_forecasts
    mape = ForecastEvaluator.mape(y_true, y_pred)
    # MAPE = mean(|(y_true - y_pred) / y_true|) * 100
    expected = np.mean([2/10, 2/20, 2/30, 2/40, 2/50]) * 100
    assert mape == pytest.approx(expected)


def test_wape(sample_forecasts):
    """Test Weighted Absolute Percentage Error."""
    y_true, y_pred = sample_forecasts
    wape = ForecastEvaluator.wape(y_true, y_pred)
    # WAPE = sum(|y_true - y_pred|) / sum(y_true) * 100
    total_error = sum([2, 2, 2, 2, 2])
    total_true = y_true.sum()
    expected = (total_error / total_true) * 100
    assert wape == pytest.approx(expected)


def test_bias(sample_forecasts):
    """Test forecast bias."""
    y_true, y_pred = sample_forecasts
    bias = ForecastEvaluator.bias(y_true, y_pred)
    # Bias = mean(y_pred - y_true)
    expected = np.mean([2, -2, 2, -2, 2])
    assert bias == pytest.approx(expected)


def test_evaluate(sample_forecasts):
    """Test evaluate method."""
    y_true, y_pred = sample_forecasts
    results = ForecastEvaluator.evaluate(y_true, y_pred)
    
    assert 'mae' in results
    assert 'rmse' in results
    assert 'mape' in results
    assert 'wape' in results
    assert 'bias' in results


def test_evaluate_by_group():
    """Test evaluate_by_group method."""
    df = pd.DataFrame({
        'store_id': ['A', 'A', 'B', 'B'],
        'true': [10, 20, 30, 40],
        'pred': [12, 18, 32, 38]
    })
    
    # Overall evaluation
    results = ForecastEvaluator.evaluate_by_group(
        df, 'true', 'pred', group_col=None
    )
    assert len(results) == 1
    assert 'mae' in results.columns
    
    # Grouped evaluation
    results = ForecastEvaluator.evaluate_by_group(
        df, 'true', 'pred', group_col='store_id'
    )
    assert len(results) == 2
    assert 'store_id' in results.columns
    assert set(results['store_id']) == {'A', 'B'}


"""Tests for baseline forecasting models."""

import pytest
import pandas as pd
import numpy as np

from services.forecasting.models.baseline import (
    LastValueForecaster,
    MovingAverageForecaster,
    SeasonalNaiveForecaster,
)


@pytest.fixture
def sample_data():
    """Create sample time series data."""
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    values = np.random.randint(10, 100, size=30)
    return pd.DataFrame({
        'date': dates,
        'demand': values
    })


def test_last_value_forecaster(sample_data):
    """Test LastValueForecaster."""
    model = LastValueForecaster()
    
    # Train
    model.train(sample_data, target_col='demand')
    assert model.is_trained
    assert model.last_value == sample_data['demand'].iloc[-1]
    
    # Predict
    predictions = model.predict(sample_data, horizon=5)
    assert len(predictions) == 5
    assert all(predictions['predicted_demand'] == model.last_value)
    
    # Save and load
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    
    try:
        model.save(temp_path)
        new_model = LastValueForecaster()
        new_model.load(temp_path)
        assert new_model.is_trained
        assert new_model.last_value == model.last_value
    finally:
        os.unlink(temp_path)


def test_moving_average_forecaster(sample_data):
    """Test MovingAverageForecaster."""
    window = 7
    model = MovingAverageForecaster(window=window)
    
    # Train
    model.train(sample_data, target_col='demand')
    assert model.is_trained
    expected_mean = sample_data['demand'].tail(window).mean()
    assert model.mean_value == pytest.approx(expected_mean)
    
    # Predict
    predictions = model.predict(sample_data, horizon=3)
    assert len(predictions) == 3
    # Check each prediction individually for floating point comparison
    for pred in predictions['predicted_demand']:
        assert pred == pytest.approx(model.mean_value)
    
    # Save and load
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    
    try:
        model.save(temp_path)
        new_model = MovingAverageForecaster(window=window)
        new_model.load(temp_path)
        assert new_model.is_trained
        assert new_model.mean_value == pytest.approx(model.mean_value)
    finally:
        os.unlink(temp_path)


def test_seasonal_naive_forecaster(sample_data):
    """Test SeasonalNaiveForecaster."""
    season_length = 7
    model = SeasonalNaiveForecaster(season_length=season_length)
    
    # Train
    model.train(sample_data, target_col='demand')
    assert model.is_trained
    assert len(model.seasonal_values) == season_length
    
    # Predict
    predictions = model.predict(sample_data, horizon=10)
    assert len(predictions) == 10
    # Check that predictions cycle through seasonal pattern
    for i in range(10):
        expected_idx = i % season_length
        assert predictions['predicted_demand'].iloc[i] == model.seasonal_values[expected_idx]
    
    # Save and load
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    
    try:
        model.save(temp_path)
        new_model = SeasonalNaiveForecaster(season_length=season_length)
        new_model.load(temp_path)
        assert new_model.is_trained
        assert new_model.seasonal_values == model.seasonal_values
    finally:
        os.unlink(temp_path)


def test_forecaster_requires_training():
    """Test that forecasters raise error if not trained."""
    model = LastValueForecaster()
    
    with pytest.raises(ValueError, match="must be trained"):
        model.predict(pd.DataFrame({'demand': [1, 2, 3]}), horizon=1)


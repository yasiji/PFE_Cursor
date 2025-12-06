"""Integration tests for end-to-end pipeline."""

import pytest
from datetime import date, timedelta
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.forecasting.models.lightgbm_model import LightGBMForecaster
from services.replenishment.policy import OrderUpToPolicy
from services.replenishment.markdown import MarkdownPolicy
from services.forecasting.features.aggregate_daily import aggregate_to_daily
from shared.config import get_config
from shared.column_mappings import COLUMN_MAPPINGS


class TestForecastingPipeline:
    """Test forecasting pipeline components."""
    
    def test_lightgbm_model_initialization(self):
        """Test LightGBM model can be initialized."""
        model = LightGBMForecaster()
        assert model is not None
        assert model.name == "lightgbm"
    
    def test_order_up_to_policy_initialization(self):
        """Test order-up-to policy can be initialized."""
        policy = OrderUpToPolicy()
        assert policy is not None
        assert policy.config is not None
    
    def test_markdown_policy_initialization(self):
        """Test markdown policy can be initialized."""
        policy = MarkdownPolicy()
        assert policy is not None
    
    def test_order_quantity_calculation(self):
        """Test order quantity calculation."""
        policy = OrderUpToPolicy()
        
        order_qty = policy.calculate_order_quantity(
            forecasted_demand=10.0,
            current_inventory=5.0,
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        assert order_qty >= 0
        assert isinstance(order_qty, (int, float))
    
    def test_markdown_recommendation(self):
        """Test markdown recommendation."""
        policy = MarkdownPolicy()
        
        recommendation = policy.recommend_markdown(
            days_until_expiry=2,
            current_inventory=10.0,
            category_id=4
        )
        
        if recommendation:
            assert "discount_percent" in recommendation
            assert recommendation["discount_percent"] > 0


class TestReplenishmentPipeline:
    """Test replenishment pipeline."""
    
    def test_policy_with_forecast(self):
        """Test policy works with forecast values."""
        policy = OrderUpToPolicy()
        
        # Test various forecast scenarios
        test_cases = [
            {"forecast": 10.0, "inventory": 5.0, "expected_min": 0},
            {"forecast": 20.0, "inventory": 2.0, "expected_min": 0},
            {"forecast": 5.0, "inventory": 15.0, "expected_min": 0},
        ]
        
        for case in test_cases:
            order_qty = policy.calculate_order_quantity(
                forecasted_demand=case["forecast"],
                current_inventory=case["inventory"],
                inbound_orders=0.0,
                expiring_units=0.0
            )
            assert order_qty >= case["expected_min"]


class TestConfiguration:
    """Test configuration system."""
    
    def test_config_loading(self):
        """Test configuration can be loaded."""
        config = get_config()
        assert config is not None
        assert config.data is not None
        assert config.models is not None
    
    def test_config_paths(self):
        """Test configuration paths are valid."""
        config = get_config()
        assert config.data.models_dir is not None
        assert config.data.processed_path is not None
    
    def test_shelf_life_config(self):
        """Test shelf life configuration."""
        config = get_config()
        shelf_life = config.shelf_life.get_shelf_life(category_id=4)
        assert isinstance(shelf_life, int)
        assert shelf_life > 0


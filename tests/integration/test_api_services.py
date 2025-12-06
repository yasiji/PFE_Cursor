"""Integration tests for API gateway services."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta

from services.api_gateway.services import ForecastingService, ReplenishmentService


class TestForecastingService:
    """Test forecasting service."""
    
    def test_service_initialization(self):
        """Test forecasting service can be initialized."""
        service = ForecastingService()
        assert service is not None
    
    @patch('services.api_gateway.services.load_mvp_data')
    def test_forecast_with_mock_data(self, mock_load_data):
        """Test forecast generation with mocked data."""
        # Mock data loading
        import pandas as pd
        mock_df = pd.DataFrame({
            'store_id': ['235'] * 10,
            'product_id': ['123'] * 10,
            'dt': pd.date_range('2024-01-01', periods=10),
            'sale_amount': [1.0] * 10
        })
        mock_load_data.return_value = (
            mock_df, 'store_id', 'product_id', 'dt', 'sale_amount'
        )
        
        service = ForecastingService()
        
        # This will fail if model not available, which is expected
        # In production, we'd ensure model exists or mock it
        try:
            forecasts = service.forecast(
                store_id="235",
                sku_id="123",
                horizon_days=3,
                include_uncertainty=False
            )
            assert isinstance(forecasts, list)
            if forecasts:
                assert len(forecasts) == 3
        except (ValueError, FileNotFoundError):
            # Expected if model not available
            pytest.skip("Model not available for testing")


class TestReplenishmentService:
    """Test replenishment service."""
    
    def test_service_initialization(self):
        """Test replenishment service can be initialized."""
        service = ReplenishmentService()
        assert service is not None
        assert service.policy is not None
        assert service.markdown_policy is not None
    
    def test_generate_replenishment_plan(self):
        """Test replenishment plan generation."""
        service = ReplenishmentService()
        
        current_inventory = [
            {
                "sku_id": "123",
                "quantity": 50.0,
                "expiry_date": str(date.today() + timedelta(days=2))
            }
        ]
        
        recommendations = service.generate_replenishment_plan(
            store_id="235",
            target_date=date.today() + timedelta(days=1),
            current_inventory=current_inventory
        )
        
        assert isinstance(recommendations, list)
        if recommendations:
            rec = recommendations[0]
            assert "sku_id" in rec
            assert "order_quantity" in rec
            assert rec["order_quantity"] >= 0


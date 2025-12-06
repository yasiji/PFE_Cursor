"""Unit tests for API gateway services."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta

from services.api_gateway.services import ForecastingService, ReplenishmentService


class TestForecastingService:
    """Test forecasting service."""
    
    def test_service_initialization(self):
        """Test service can be initialized."""
        service = ForecastingService()
        assert service is not None
    
    def test_service_has_model_attribute(self):
        """Test service has model attribute."""
        service = ForecastingService()
        # Model may be None if not loaded, but attribute should exist
        assert hasattr(service, 'model')


class TestReplenishmentService:
    """Test replenishment service."""
    
    def test_service_initialization(self):
        """Test service can be initialized."""
        service = ReplenishmentService()
        assert service is not None
        assert service.policy is not None
        assert service.markdown_policy is not None
    
    def test_generate_replenishment_plan_structure(self):
        """Test replenishment plan has correct structure."""
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
            assert isinstance(rec["order_quantity"], (int, float))
            assert rec["order_quantity"] >= 0


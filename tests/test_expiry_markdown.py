"""Tests for expiry and markdown functionality."""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from services.replenishment.expiry import (
    ExpiryBucket,
    InventoryAgeTracker,
    create_inventory_age_tracker,
    calculate_expiry_dates
)
from services.replenishment.markdown import MarkdownPolicy


class TestExpiryBucket:
    """Test expiry bucket functionality."""

    def test_expiry_bucket_creation(self):
        """Test creating an expiry bucket."""
        expiry_date = datetime(2024, 6, 15)
        bucket = ExpiryBucket(expiry_date, 50.0)
        
        assert bucket.expiry_date == expiry_date
        assert bucket.quantity == 50.0

    def test_update_days_until_expiry(self):
        """Test updating days until expiry."""
        expiry_date = datetime(2024, 6, 15)
        current_date = datetime(2024, 6, 10)
        
        bucket = ExpiryBucket(expiry_date, 50.0)
        bucket.update_days_until_expiry(current_date)
        
        assert bucket.days_until_expiry == 5

    def test_expired_inventory(self):
        """Test handling expired inventory."""
        expiry_date = datetime(2024, 6, 10)
        current_date = datetime(2024, 6, 15)
        
        bucket = ExpiryBucket(expiry_date, 50.0)
        bucket.update_days_until_expiry(current_date)
        
        assert bucket.days_until_expiry == 0


class TestInventoryAgeTracker:
    """Test inventory age tracker."""

    def test_add_inventory(self):
        """Test adding inventory to tracker."""
        current_date = datetime(2024, 6, 10)
        tracker = InventoryAgeTracker(current_date)
        
        expiry_date = datetime(2024, 6, 15)
        tracker.add_inventory(50.0, expiry_date)
        
        assert len(tracker.buckets) == 1
        assert tracker.buckets[0].quantity == 50.0
        assert tracker.buckets[0].days_until_expiry == 5

    def test_get_expiring_units(self):
        """Test getting expiring units."""
        current_date = datetime(2024, 6, 10)
        tracker = InventoryAgeTracker(current_date)
        
        # Add inventory expiring in different timeframes
        tracker.add_inventory(20.0, datetime(2024, 6, 12))  # 2 days
        tracker.add_inventory(30.0, datetime(2024, 6, 15))  # 5 days
        tracker.add_inventory(50.0, datetime(2024, 6, 20))  # 10 days
        
        # Get units expiring in next 3 days
        expiring = tracker.get_expiring_units(3)
        assert expiring == 20.0  # Only the 2-day bucket

    def test_get_total_inventory(self):
        """Test getting total inventory."""
        current_date = datetime(2024, 6, 10)
        tracker = InventoryAgeTracker(current_date)
        
        tracker.add_inventory(20.0, datetime(2024, 6, 12))
        tracker.add_inventory(30.0, datetime(2024, 6, 15))
        
        assert tracker.get_total_inventory() == 50.0

    def test_get_max_sellable_before_expiry(self):
        """Test calculating max sellable before expiry."""
        current_date = datetime(2024, 6, 10)
        tracker = InventoryAgeTracker(current_date)
        
        # Add inventory expiring in 5 days
        tracker.add_inventory(50.0, datetime(2024, 6, 15))
        
        # Forecast: 10 units/day, coverage: 7 days
        max_sellable = tracker.get_max_sellable_before_expiry(
            forecasted_daily_demand=10.0,
            coverage_days=7
        )
        
        # Can sell: min(50 inventory, 10*5=50 demand capacity) = 50
        assert max_sellable == 50.0


class TestCalculateExpiryDates:
    """Test expiry date calculation."""

    def test_calculate_expiry_dates_int(self):
        """Test calculating expiry dates with integer shelf life."""
        receipt_dates = pd.Series([
            datetime(2024, 6, 10),
            datetime(2024, 6, 11),
            datetime(2024, 6, 12)
        ])
        
        expiry_dates = calculate_expiry_dates(receipt_dates, shelf_life_days=5)
        
        assert len(expiry_dates) == 3
        assert expiry_dates.iloc[0] == datetime(2024, 6, 15)
        assert expiry_dates.iloc[1] == datetime(2024, 6, 16)
        assert expiry_dates.iloc[2] == datetime(2024, 6, 17)

    def test_calculate_expiry_dates_series(self):
        """Test calculating expiry dates with Series shelf life."""
        receipt_dates = pd.Series([
            datetime(2024, 6, 10),
            datetime(2024, 6, 11)
        ])
        shelf_life = pd.Series([5, 7])
        
        expiry_dates = calculate_expiry_dates(receipt_dates, shelf_life)
        
        assert expiry_dates.iloc[0] == datetime(2024, 6, 15)
        assert expiry_dates.iloc[1] == datetime(2024, 6, 18)


class TestMarkdownPolicy:
    """Test markdown policy."""

    def test_get_discount_for_expiry(self):
        """Test getting discount based on expiry."""
        policy = MarkdownPolicy()
        
        # 1 day until expiry should get highest discount
        discount = policy.get_discount_for_expiry(
            days_until_expiry=1,
            current_inventory=10.0
        )
        assert discount == 50.0  # 50% discount
        
        # 3 days until expiry
        discount = policy.get_discount_for_expiry(
            days_until_expiry=3,
            current_inventory=10.0
        )
        assert discount == 20.0  # 20% discount
        
        # 5 days until expiry (no discount)
        discount = policy.get_discount_for_expiry(
            days_until_expiry=5,
            current_inventory=10.0
        )
        assert discount == 0.0

    def test_min_inventory_threshold(self):
        """Test minimum inventory threshold."""
        policy = MarkdownPolicy()
        
        # Low inventory - no markdown
        discount = policy.get_discount_for_expiry(
            days_until_expiry=1,
            current_inventory=2.0,  # Below threshold
            min_threshold=5.0
        )
        assert discount == 0.0

    def test_estimate_demand_uplift(self):
        """Test demand uplift estimation."""
        policy = MarkdownPolicy()
        
        # Base demand: 10 units/day
        # 20% discount with elasticity -2.0
        # Price change: -0.2
        # Demand change: -2.0 * -0.2 = 0.4 (40% increase)
        # New demand: 10 * 1.4 = 14
        new_demand = policy.estimate_demand_uplift(
            base_demand=10.0,
            discount_percent=20.0,
            price_elasticity=-2.0
        )
        
        assert new_demand == 14.0

    def test_calculate_markdown_recommendations(self):
        """Test batch markdown recommendations."""
        policy = MarkdownPolicy()
        
        df = pd.DataFrame({
            'sku_id': ['A', 'B', 'C'],
            'days_until_expiry': [1, 2, 5],
            'current_inventory': [10.0, 8.0, 15.0]
        })
        
        result = policy.calculate_markdown_recommendations(df)
        
        assert 'recommended_discount' in result.columns
        assert 'markdown_recommended' in result.columns
        assert result.loc[0, 'recommended_discount'] == 50.0  # 1 day
        assert result.loc[1, 'recommended_discount'] == 35.0  # 2 days
        assert result.loc[2, 'recommended_discount'] == 0.0  # 5 days

    def test_calculate_markdown_effectiveness(self):
        """Test markdown effectiveness calculation."""
        policy = MarkdownPolicy()
        
        metrics = policy.calculate_markdown_effectiveness(
            units_sold=8.0,
            units_available=10.0,
            discount_percent=20.0,
            unit_cost=5.0,
            unit_price=10.0
        )
        
        assert metrics['sell_through_rate'] == 0.8
        assert metrics['waste_rate'] == pytest.approx(0.2, abs=0.01)
        assert metrics['waste_cost'] == 10.0  # 2 units * 5.0 cost


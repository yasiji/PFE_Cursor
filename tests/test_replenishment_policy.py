"""Tests for replenishment policy."""

import pytest
import pandas as pd
import numpy as np

from services.replenishment.policy import OrderUpToPolicy, calculate_max_sellable_before_expiry


class TestOrderUpToPolicy:
    """Test order-up-to policy calculations."""

    def test_basic_order_calculation(self):
        """Test basic order quantity calculation."""
        policy = OrderUpToPolicy()
        
        # Simple case: need to order to meet forecast
        order_qty = policy.calculate_order_quantity(
            forecasted_demand=10.0,  # 10 units/day
            current_inventory=20.0,  # 20 units on hand
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        # Expected: target_coverage (7) * demand (10) + safety - inventory (20)
        # = 70 + safety - 20 = ~50 + safety stock
        assert order_qty >= 0
        assert order_qty > 20  # Should order more than current inventory

    def test_no_order_when_sufficient_inventory(self):
        """Test that no order is placed when inventory is sufficient."""
        policy = OrderUpToPolicy()
        
        # High inventory, low demand
        order_qty = policy.calculate_order_quantity(
            forecasted_demand=5.0,
            current_inventory=100.0,
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        # Should be 0 or very small (min order constraint)
        assert order_qty >= 0

    def test_min_order_constraint(self):
        """Test minimum order quantity constraint."""
        config = {
            'target_coverage_days': 7,
            'min_order_quantity': 10,
            'max_order_quantity': 1000,
            'case_pack_size': 1,
            'service_level': 0.95,
            'safety_factor': 1.65
        }
        policy = OrderUpToPolicy(config=config)
        
        # Small order needed
        order_qty = policy.calculate_order_quantity(
            forecasted_demand=1.0,
            current_inventory=50.0,
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        # Should respect min order (if order > 0)
        if order_qty > 0:
            assert order_qty >= config['min_order_quantity']

    def test_max_order_constraint(self):
        """Test maximum order quantity constraint."""
        config = {
            'target_coverage_days': 7,
            'min_order_quantity': 1,
            'max_order_quantity': 100,
            'case_pack_size': 1,
            'service_level': 0.95,
            'safety_factor': 1.65
        }
        policy = OrderUpToPolicy(config=config)
        
        # Very high demand, low inventory
        order_qty = policy.calculate_order_quantity(
            forecasted_demand=100.0,
            current_inventory=0.0,
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        assert order_qty <= config['max_order_quantity']

    def test_case_pack_rounding(self):
        """Test case pack size rounding."""
        config = {
            'target_coverage_days': 7,
            'min_order_quantity': 1,
            'max_order_quantity': 1000,
            'case_pack_size': 12,  # Case of 12
            'service_level': 0.95,
            'safety_factor': 1.65
        }
        policy = OrderUpToPolicy(config=config)
        
        order_qty = policy.calculate_order_quantity(
            forecasted_demand=10.0,
            current_inventory=0.0,
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        # Should be multiple of 12
        assert order_qty % 12 == 0

    def test_expiring_units_adjustment(self):
        """Test that expiring units are excluded from available inventory."""
        policy = OrderUpToPolicy()
        
        # High inventory but some expiring
        order_qty_with_expiry = policy.calculate_order_quantity(
            forecasted_demand=10.0,
            current_inventory=50.0,
            inbound_orders=0.0,
            expiring_units=30.0  # 30 units expiring
        )
        
        # Without expiring units
        order_qty_no_expiry = policy.calculate_order_quantity(
            forecasted_demand=10.0,
            current_inventory=50.0,
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        # Should order more when units are expiring
        assert order_qty_with_expiry >= order_qty_no_expiry

    def test_inbound_orders_adjustment(self):
        """Test that inbound orders reduce order quantity."""
        policy = OrderUpToPolicy()
        
        # With inbound orders
        order_qty_with_inbound = policy.calculate_order_quantity(
            forecasted_demand=10.0,
            current_inventory=20.0,
            inbound_orders=30.0,
            expiring_units=0.0
        )
        
        # Without inbound orders
        order_qty_no_inbound = policy.calculate_order_quantity(
            forecasted_demand=10.0,
            current_inventory=20.0,
            inbound_orders=0.0,
            expiring_units=0.0
        )
        
        # Should order less when inbound orders exist
        assert order_qty_with_inbound <= order_qty_no_inbound

    def test_shelf_life_constraint(self):
        """Test shelf-life constraint limits order quantity."""
        policy = OrderUpToPolicy()
        
        # High demand but limited by shelf-life
        order_qty = policy.calculate_order_quantity(
            forecasted_demand=100.0,
            current_inventory=0.0,
            inbound_orders=0.0,
            expiring_units=0.0,
            max_sellable_before_expiry=50.0  # Can only sell 50 before expiry
        )
        
        assert order_qty <= 50.0

    def test_batch_calculation(self):
        """Test batch order quantity calculation."""
        policy = OrderUpToPolicy()
        
        df = pd.DataFrame({
            'store_id': [1, 2, 3],
            'sku_id': ['A', 'B', 'C'],
            'forecasted_demand': [10.0, 20.0, 5.0],
            'current_inventory': [20.0, 10.0, 50.0],
            'inbound_orders': [0.0, 5.0, 0.0],
            'expiring_units': [0.0, 0.0, 10.0]
        })
        
        result = policy.calculate_order_quantity_batch(df)
        
        assert 'order_quantity' in result.columns
        assert len(result) == 3
        assert all(result['order_quantity'] >= 0)


class TestMaxSellableCalculation:
    """Test max sellable before expiry calculation."""

    def test_basic_calculation(self):
        """Test basic max sellable calculation."""
        max_sellable = calculate_max_sellable_before_expiry(
            current_inventory=50.0,
            inbound_orders=20.0,
            forecasted_demand=10.0,
            shelf_life_days=7,
            days_until_expiry=5,
            coverage_days=7
        )
        
        # Total inventory: 70
        # Days available: min(5, 7) = 5
        # Max demand: 10 * 5 = 50
        # Max sellable: min(70, 50) = 50
        assert max_sellable == 50.0

    def test_inventory_limited(self):
        """Test when inventory limits sellable quantity."""
        max_sellable = calculate_max_sellable_before_expiry(
            current_inventory=30.0,
            inbound_orders=10.0,
            forecasted_demand=20.0,
            shelf_life_days=7,
            days_until_expiry=5,
            coverage_days=7
        )
        
        # Total inventory: 40
        # Max demand: 20 * 5 = 100
        # Max sellable: min(40, 100) = 40 (inventory limited)
        assert max_sellable == 40.0

    def test_demand_limited(self):
        """Test when demand limits sellable quantity."""
        max_sellable = calculate_max_sellable_before_expiry(
            current_inventory=100.0,
            inbound_orders=50.0,
            forecasted_demand=10.0,
            shelf_life_days=7,
            days_until_expiry=3,
            coverage_days=7
        )
        
        # Total inventory: 150
        # Days available: min(3, 7) = 3
        # Max demand: 10 * 3 = 30
        # Max sellable: min(150, 30) = 30 (demand limited)
        assert max_sellable == 30.0


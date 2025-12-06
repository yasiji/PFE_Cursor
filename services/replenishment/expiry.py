"""Shelf-life and expiry modeling for inventory management."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from shared.config import get_config
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class ExpiryBucket:
    """Represents inventory by expiry date bucket."""

    def __init__(self, expiry_date: datetime, quantity: float):
        """
        Initialize expiry bucket.

        Args:
            expiry_date: Date when inventory expires
            quantity: Quantity of units in this bucket
        """
        self.expiry_date = expiry_date
        self.quantity = quantity
        self.days_until_expiry = None

    def update_days_until_expiry(self, current_date: datetime):
        """Update days until expiry based on current date."""
        delta = self.expiry_date - current_date
        self.days_until_expiry = max(0, delta.days)


class InventoryAgeTracker:
    """Track inventory by age/expiry buckets."""

    def __init__(self, current_date: datetime):
        """
        Initialize inventory age tracker.

        Args:
            current_date: Current date for calculations
        """
        self.current_date = current_date
        self.buckets: List[ExpiryBucket] = []

    def add_inventory(
        self,
        quantity: float,
        expiry_date: datetime,
        receipt_date: Optional[datetime] = None
    ):
        """
        Add inventory to tracker.

        Args:
            quantity: Quantity of units
            expiry_date: Date when units expire
            receipt_date: Date when units were received (optional)
        """
        bucket = ExpiryBucket(expiry_date, quantity)
        bucket.update_days_until_expiry(self.current_date)
        self.buckets.append(bucket)

    def get_expiring_units(self, days_ahead: int) -> float:
        """
        Get units expiring within specified days.

        Args:
            days_ahead: Number of days ahead to check

        Returns:
            Total units expiring within days_ahead
        """
        total = 0.0
        for bucket in self.buckets:
            if bucket.days_until_expiry is not None:
                if 0 <= bucket.days_until_expiry <= days_ahead:
                    total += bucket.quantity
        return total

    def get_total_inventory(self) -> float:
        """Get total inventory across all buckets."""
        return sum(bucket.quantity for bucket in self.buckets)

    def get_inventory_by_expiry_bucket(self) -> Dict[int, float]:
        """
        Get inventory grouped by days until expiry.

        Returns:
            Dictionary mapping days_until_expiry to quantity
        """
        result = {}
        for bucket in self.buckets:
            if bucket.days_until_expiry is not None:
                days = bucket.days_until_expiry
                result[days] = result.get(days, 0.0) + bucket.quantity
        return result

    def get_max_sellable_before_expiry(
        self,
        forecasted_daily_demand: float,
        coverage_days: int
    ) -> float:
        """
        Calculate maximum units that can be sold before expiry.

        Args:
            forecasted_daily_demand: Forecasted daily demand
            coverage_days: Coverage window in days

        Returns:
            Maximum units that can be sold before expiry
        """
        total_inventory = self.get_total_inventory()
        
        # Calculate demand capacity based on expiry buckets
        demand_capacity = 0.0
        for bucket in self.buckets:
            if bucket.days_until_expiry is not None:
                days_available = min(bucket.days_until_expiry, coverage_days)
                if days_available > 0:
                    # Can sell min of bucket quantity and demand capacity
                    bucket_demand_capacity = forecasted_daily_demand * days_available
                    demand_capacity += min(bucket.quantity, bucket_demand_capacity)
        
        # Maximum sellable is limited by both total inventory and demand capacity
        max_sellable = min(total_inventory, demand_capacity)
        
        return max_sellable


def create_inventory_age_tracker(
    current_date: datetime,
    inventory_data: pd.DataFrame,
    expiry_date_col: str = 'expiry_date',
    quantity_col: str = 'quantity',
    receipt_date_col: Optional[str] = None
) -> InventoryAgeTracker:
    """
    Create inventory age tracker from DataFrame.

    Args:
        current_date: Current date
        inventory_data: DataFrame with inventory records
        expiry_date_col: Column name for expiry dates
        quantity_col: Column name for quantities
        receipt_date_col: Column name for receipt dates (optional)

    Returns:
        InventoryAgeTracker instance
    """
    tracker = InventoryAgeTracker(current_date)
    
    for _, row in inventory_data.iterrows():
        expiry_date = pd.to_datetime(row[expiry_date_col])
        quantity = float(row[quantity_col])
        receipt_date = pd.to_datetime(row[receipt_date_col]) if receipt_date_col else None
        
        tracker.add_inventory(quantity, expiry_date, receipt_date)
    
    return tracker


def calculate_expiry_dates(
    receipt_dates: pd.Series,
    shelf_life_days: int | pd.Series
) -> pd.Series:
    """
    Calculate expiry dates from receipt dates and shelf life.

    Args:
        receipt_dates: Series of receipt dates
        shelf_life_days: Shelf life in days (int or Series)

    Returns:
        Series of expiry dates
    """
    receipt_dates = pd.to_datetime(receipt_dates)
    
    if isinstance(shelf_life_days, (int, float)):
        expiry_dates = receipt_dates + pd.Timedelta(days=int(shelf_life_days))
    else:
        expiry_dates = receipt_dates + pd.to_timedelta(shelf_life_days, unit='D')
    
    return expiry_dates


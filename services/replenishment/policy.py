"""Replenishment policy implementation (order-up-to policy)."""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from shared.config import get_config
from shared.logging_setup import get_logger
from shared.exceptions import ReplenishmentPolicyError

logger = get_logger(__name__)


class OrderUpToPolicy:
    """Order-up-to replenishment policy."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize order-up-to policy.

        Args:
            config: Optional configuration dictionary. If None, loads from AppConfig.
        """
        if config is None:
            app_config = get_config()
            self.config = {
                'target_coverage_days': app_config.models.replenishment.target_coverage_days,
                'min_order_quantity': app_config.models.replenishment.min_order_quantity,
                'max_order_quantity': app_config.models.replenishment.max_order_quantity,
                'case_pack_size': app_config.models.replenishment.case_pack_size,
                'service_level': app_config.models.forecasting.default_service_level,
                'safety_factor': app_config.models.forecasting.safety_factor,
            }
        else:
            self.config = config

    def calculate_order_quantity(
        self,
        forecasted_demand: float,
        current_inventory: float,
        inbound_orders: float = 0.0,
        expiring_units: float = 0.0,
        forecast_uncertainty: Optional[float] = None,
        shelf_life_days: Optional[int] = None,
        days_until_expiry: Optional[int] = None,
        max_sellable_before_expiry: Optional[float] = None,
        demand_horizon_days: Optional[int] = None
    ) -> float:
        """
        Calculate recommended order quantity using order-up-to policy.

        Args:
            forecasted_demand: Forecasted demand for coverage window
            current_inventory: Current on-hand inventory
            inbound_orders: Confirmed deliveries arriving before/during window
            expiring_units: Units that will expire before/during window
            forecast_uncertainty: Standard deviation of forecast error (optional)
            shelf_life_days: Shelf life in days (optional, for validation)
            days_until_expiry: Days until current inventory expires (optional)
            max_sellable_before_expiry: Maximum units that can be sold before expiry (optional)

        Returns:
            Recommended order quantity
        """
        # Extract configuration
        target_coverage = self.config['target_coverage_days']
        min_order = self.config['min_order_quantity']
        max_order = self.config['max_order_quantity']
        case_pack = self.config['case_pack_size']
        safety_factor = self.config['safety_factor']

        # Estimate forecast uncertainty if not provided
        if forecast_uncertainty is None:
            # Use a simple heuristic: 30% of forecast (based on typical MAPE)
            forecast_uncertainty = forecasted_demand * 0.30

        # Calculate base order quantity using order-up-to formula
        # If demand horizon is supplied, treat forecasted_demand as total demand over that horizon
        if demand_horizon_days:
            target_stock = forecasted_demand + (safety_factor * forecast_uncertainty)
        else:
            target_stock = (
                target_coverage * forecasted_demand +
                safety_factor * forecast_uncertainty
            )

        # Adjust for current inventory (excluding expiring units)
        available_inventory = current_inventory - expiring_units

        # Calculate order quantity
        order_qty = max(0, target_stock - available_inventory - inbound_orders)

        # Apply shelf-life constraint
        if max_sellable_before_expiry is not None:
            # Don't order more than can be sold before expiry
            # Consider: current inventory + inbound + new order must be <= max_sellable
            max_new_order = max(0, max_sellable_before_expiry - available_inventory - inbound_orders)
            order_qty = min(order_qty, max_new_order)

        # Apply minimum order constraint
        if order_qty > 0:
            order_qty = max(min_order, order_qty)

        # Apply maximum order constraint
        order_qty = min(max_order, order_qty)

        # Round to case pack size
        if case_pack > 1:
            order_qty = np.ceil(order_qty / case_pack) * case_pack

        return float(order_qty)

    def calculate_order_quantity_batch(
        self,
        df: pd.DataFrame,
        forecast_col: str = 'forecasted_demand',
        inventory_col: str = 'current_inventory',
        inbound_col: str = 'inbound_orders',
        expiring_col: str = 'expiring_units',
        uncertainty_col: Optional[str] = None,
        shelf_life_col: Optional[str] = None,
        max_sellable_col: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Calculate order quantities for a batch of store-SKU combinations.

        Args:
            df: DataFrame with columns for forecast, inventory, etc.
            forecast_col: Column name for forecasted demand
            inventory_col: Column name for current inventory
            inbound_col: Column name for inbound orders
            expiring_col: Column name for expiring units
            uncertainty_col: Column name for forecast uncertainty (optional)
            shelf_life_col: Column name for shelf life (optional)
            max_sellable_col: Column name for max sellable before expiry (optional)

        Returns:
            DataFrame with added 'order_quantity' column
        """
        df = df.copy()

        # Calculate order quantities
        order_quantities = []
        for idx, row in df.iterrows():
            order_qty = self.calculate_order_quantity(
                forecasted_demand=row[forecast_col],
                current_inventory=row[inventory_col],
                inbound_orders=row.get(inbound_col, 0.0),
                expiring_units=row.get(expiring_col, 0.0),
                forecast_uncertainty=row.get(uncertainty_col) if uncertainty_col else None,
                max_sellable_before_expiry=row.get(max_sellable_col) if max_sellable_col else None
            )
            order_quantities.append(order_qty)

        df['order_quantity'] = order_quantities

        return df


def calculate_max_sellable_before_expiry(
    current_inventory: float,
    inbound_orders: float,
    forecasted_demand: float,
    shelf_life_days: int,
    days_until_expiry: int,
    coverage_days: int
) -> float:
    """
    Calculate maximum units that can be sold before expiry.

    Args:
        current_inventory: Current on-hand inventory
        inbound_orders: Inbound orders arriving
        forecasted_demand: Forecasted daily demand
        shelf_life_days: Total shelf life in days
        days_until_expiry: Days until current inventory expires
        coverage_days: Coverage window in days

    Returns:
        Maximum units that can be sold before expiry
    """
    # Total inventory available (current + inbound)
    total_inventory = current_inventory + inbound_orders

    # Days available to sell (min of expiry days and coverage days)
    days_available = min(days_until_expiry, coverage_days)

    # Maximum demand that can be satisfied before expiry
    max_demand = forecasted_demand * days_available

    # Maximum sellable is limited by both inventory and demand capacity
    max_sellable = min(total_inventory, max_demand)

    return max_sellable


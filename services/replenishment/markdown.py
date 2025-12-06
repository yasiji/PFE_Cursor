"""Markdown/discount rules for near-expiry products."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from shared.config import get_config
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class MarkdownPolicy:
    """Markdown policy for near-expiry products."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize markdown policy.

        Args:
            config: Optional configuration dictionary. If None, loads from AppConfig.
        """
        if config is None:
            app_config = get_config()
            self.config = {
                'expiry_buckets': [
                    {
                        'days_before_expiry': bucket.days_before_expiry,
                        'discount_percent': bucket.discount_percent
                    }
                    for bucket in app_config.models.markdown.expiry_buckets
                ],
                'min_inventory_threshold': 5,  # Minimum inventory to trigger markdown
            }
        else:
            self.config = config

    def get_discount_for_expiry(
        self,
        days_until_expiry: int,
        current_inventory: float,
        min_threshold: Optional[float] = None
    ) -> float:
        """
        Get recommended discount percentage based on days until expiry.

        Args:
            days_until_expiry: Days until product expires
            current_inventory: Current inventory level
            min_threshold: Minimum inventory to trigger markdown (optional)

        Returns:
            Recommended discount percentage (0-100)
        """
        if min_threshold is None:
            min_threshold = self.config.get('min_inventory_threshold', 0)

        # Don't apply markdown if inventory is too low
        if current_inventory < min_threshold:
            return 0.0

        # Find matching expiry bucket (most restrictive first)
        # Buckets are: 3 days (20%), 2 days (35%), 1 day (50%)
        # We want to match the most restrictive (smallest days_before_expiry) that applies
        buckets = sorted(
            self.config['expiry_buckets'],
            key=lambda x: x['days_before_expiry'],
            reverse=False  # Sort ascending to check most restrictive first
        )

        # Find the bucket with smallest days_before_expiry that still applies
        matching_bucket = None
        for bucket in buckets:
            if days_until_expiry <= bucket['days_before_expiry']:
                matching_bucket = bucket
                break
        
        if matching_bucket:
            return matching_bucket['discount_percent']

        # No markdown if not in any bucket
        return 0.0

    def recommend_markdown(
        self,
        days_until_expiry: int,
        current_inventory: float,
        category_id: Optional[int] = None,
        min_threshold: Optional[float] = None,
        current_price: Optional[float] = None,
        cost_per_unit: Optional[float] = None
    ) -> Optional[Dict[str, float | str | int | bool]]:
        """
        Provide a markdown recommendation dictionary if discount applies.
        
        Now includes at-cost price calculations.

        Returns:
            Dict with discount details or None if no markdown required.
        """
        discount = self.get_discount_for_expiry(
            days_until_expiry=days_until_expiry,
            current_inventory=current_inventory,
            min_threshold=min_threshold
        )

        if discount <= 0:
            return None

        # Calculate at-cost discount if cost and price are provided
        at_cost_price = False
        discount_to_reach_cost = 0.0
        potential_loss_if_not_sold = 0.0
        loss_from_discount = 0.0
        
        if current_price and cost_per_unit and current_price > 0:
            # Calculate discount needed to reach cost price
            discount_to_reach_cost = ((current_price - cost_per_unit) / current_price) * 100
            
            # If recommended discount is >= discount to reach cost, mark as at-cost
            if discount >= discount_to_reach_cost:
                at_cost_price = True
                discount = discount_to_reach_cost  # Use cost price discount
            
            # Calculate potential losses
            potential_loss_if_not_sold = current_inventory * cost_per_unit  # Full cost if not sold
            discounted_price = current_price * (1 - discount / 100)
            loss_from_discount = current_inventory * (current_price - discounted_price)  # Revenue lost from discount

        recommendation: Dict[str, float | str | int | bool] = {
            "discount_percent": discount,
            "reason": "Near expiry",
            "at_cost_price": at_cost_price,
            "discount_to_reach_cost": discount_to_reach_cost,
            "potential_loss_if_not_sold": potential_loss_if_not_sold,
            "loss_from_discount": loss_from_discount
        }
        
        if current_price:
            recommendation["current_price"] = current_price
        if cost_per_unit:
            recommendation["cost_per_unit"] = cost_per_unit
            if current_price:
                recommendation["discounted_price"] = current_price * (1 - discount / 100)
        
        if category_id is not None:
            recommendation["category_id"] = category_id
        return recommendation

    def calculate_markdown_recommendations(
        self,
        df: pd.DataFrame,
        days_until_expiry_col: str = 'days_until_expiry',
        inventory_col: str = 'current_inventory',
        min_threshold: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Calculate markdown recommendations for a batch of products.

        Args:
            df: DataFrame with product information
            days_until_expiry_col: Column name for days until expiry
            inventory_col: Column name for current inventory
            min_threshold: Minimum inventory threshold (optional)

        Returns:
            DataFrame with added 'recommended_discount' column
        """
        df = df.copy()

        discounts = []
        for _, row in df.iterrows():
            discount = self.get_discount_for_expiry(
                days_until_expiry=int(row[days_until_expiry_col]),
                current_inventory=float(row[inventory_col]),
                min_threshold=min_threshold
            )
            discounts.append(discount)

        df['recommended_discount'] = discounts
        df['markdown_recommended'] = df['recommended_discount'] > 0

        return df

    def estimate_demand_uplift(
        self,
        base_demand: float,
        discount_percent: float,
        price_elasticity: float = -2.0
    ) -> float:
        """
        Estimate demand uplift from discount using price elasticity.

        Args:
            base_demand: Base demand without discount
            discount_percent: Discount percentage (0-100)
            price_elasticity: Price elasticity coefficient (default: -2.0)

        Returns:
            Estimated demand with discount
        """
        if discount_percent == 0:
            return base_demand

        # Price change = -discount_percent / 100
        price_change = -discount_percent / 100.0

        # Demand change = elasticity * price_change
        demand_change = price_elasticity * price_change

        # New demand = base_demand * (1 + demand_change)
        new_demand = base_demand * (1 + demand_change)

        return max(0, new_demand)

    def calculate_markdown_effectiveness(
        self,
        units_sold: float,
        units_available: float,
        discount_percent: float,
        unit_cost: float,
        unit_price: float
    ) -> Dict[str, float]:
        """
        Calculate markdown effectiveness metrics.

        Args:
            units_sold: Units sold with markdown
            units_available: Units available for sale
            discount_percent: Discount percentage applied
            unit_cost: Cost per unit (COGS)
            unit_price: Regular price per unit

        Returns:
            Dictionary with effectiveness metrics
        """
        # Calculate metrics
        sell_through_rate = units_sold / units_available if units_available > 0 else 0.0
        waste_rate = 1.0 - sell_through_rate

        # Revenue and margin
        discounted_price = unit_price * (1 - discount_percent / 100.0)
        revenue = units_sold * discounted_price
        cost = units_sold * unit_cost
        margin = revenue - cost

        # Waste cost (if any)
        waste_units = units_available - units_sold
        waste_cost = waste_units * unit_cost

        # Total profit impact
        total_profit = margin - waste_cost

        return {
            'units_sold': units_sold,
            'units_available': units_available,
            'sell_through_rate': sell_through_rate,
            'waste_rate': waste_rate,
            'revenue': revenue,
            'cost': cost,
            'margin': margin,
            'waste_cost': waste_cost,
            'total_profit': total_profit,
            'discount_percent': discount_percent
        }


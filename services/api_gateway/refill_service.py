"""Service for calculating refill plans (how much to move from backroom to shelves)."""

from datetime import date, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
from sqlalchemy.orm import Session

from services.api_gateway.models import InventorySnapshot, Product, Order
from services.api_gateway.services import get_forecasting_service
from services.api_gateway.demand_factors_service import get_demand_factors_service
from services.replenishment.policy import OrderUpToPolicy
from shared.config import get_config
from shared.logging_setup import get_logger

logger = get_logger(__name__)
config = get_config()


class RefillService:
    """Service for calculating refill plans."""
    
    def __init__(self):
        """Initialize refill service."""
        self.forecasting_service = get_forecasting_service()
        self.policy = OrderUpToPolicy()
        self.safety_factor = 1.2  # 20% safety buffer for shelf quantity
        self.logger = get_logger(__name__)
    
    def calculate_refill_plan(
        self,
        store_id: str,
        target_date: date,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Calculate refill plan for a store.
        
        Args:
            store_id: Store identifier
            target_date: Target date for refill (typically tomorrow)
            db: Database session
            
        Returns:
            List of refill item dictionaries
        """
        refill_plan = []
        
        # Get current inventory snapshots
        today = date.today()
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == today
        ).all()
        
        if not inventory_snapshots:
            self.logger.warning(f"No inventory snapshots found for store {store_id} on {today}")
            return refill_plan
        
        # Get forecast for tomorrow - process all items but limit forecast calls
        tomorrow_forecasts = {}
        forecast_count = 0
        for inv_snapshot in inventory_snapshots:
            product = db.query(Product).filter(Product.id == inv_snapshot.product_id).first()
            if not product:
                continue
            
            # Limit forecast API calls but use estimates for others
            if forecast_count < 30:
                try:
                    forecasts = self.forecasting_service.forecast(
                        store_id=store_id,
                        sku_id=product.sku_id,
                        horizon_days=1,  # Just tomorrow
                        include_uncertainty=False
                    )
                    if forecasts and len(forecasts) > 0:
                        tomorrow_forecasts[product.sku_id] = forecasts[0].get('predicted_demand', 0.0)
                        forecast_count += 1
                except Exception as e:
                    self.logger.warning(f"Error forecasting for {product.sku_id}: {e}")
                    # Use estimate based on current inventory turnover (25% daily)
                    tomorrow_forecasts[product.sku_id] = inv_snapshot.quantity * 0.25
            else:
                # Use estimate for remaining products
                tomorrow_forecasts[product.sku_id] = inv_snapshot.quantity * 0.25
        
        # Process each inventory item
        for inv_snapshot in inventory_snapshots:
            product = db.query(Product).filter(Product.id == inv_snapshot.product_id).first()
            if not product:
                continue
            
            try:
                # Get shelf and backroom quantities
                shelf_qty = getattr(inv_snapshot, 'shelf_quantity', None)
                backroom_qty = getattr(inv_snapshot, 'backroom_quantity', None)
                
                # Fallback: split existing quantity if not set
                if shelf_qty is None or backroom_qty is None:
                    if inv_snapshot.quantity > 0:
                        shelf_qty = round(inv_snapshot.quantity * 0.7, 2)
                        backroom_qty = round(inv_snapshot.quantity * 0.3, 2)
                    else:
                        shelf_qty = 0.0
                        backroom_qty = 0.0
                
                # Get forecast for tomorrow
                forecasted_demand = tomorrow_forecasts.get(product.sku_id, 0.0)
                
                # Calculate recommended shelf quantity
                # Recommended = forecast * safety_factor (to ensure shelves stay full)
                recommended_shelf_qty = max(0.0, forecasted_demand * self.safety_factor)
                
                # Get in-transit orders for this product (arriving before or on target date)
                in_transit_orders = db.query(Order).filter(
                    Order.store_id == int(store_id),
                    Order.product_id == product.id,
                    Order.status.in_(["ordered", "in_transit"]),
                    Order.expected_arrival_date <= target_date
                ).all()
                
                in_transit_qty = sum(order.order_quantity for order in in_transit_orders)
                
                # Get transit days (from product or order)
                transit_days = product.transit_days or 1  # Default 1 day
                if in_transit_orders and in_transit_orders[0].transit_days:
                    transit_days = in_transit_orders[0].transit_days
                
                # Calculate refill quantity (how much to move from backroom to shelf)
                refill_qty = max(0.0, recommended_shelf_qty - shelf_qty)
                
                # Calculate available stock (backroom + in-transit items arriving in time)
                available_stock = backroom_qty + in_transit_qty
                
                # If refill needed > available stock, we need to order
                order_qty = 0.0
                if refill_qty > available_stock:
                    order_qty = refill_qty - available_stock
                    refill_qty = available_stock  # Can only refill what's available
                else:
                    # Can refill from available stock
                    refill_qty = min(refill_qty, available_stock)
                
                # Calculate expected arrival date for new orders
                if order_qty > 0:
                    # If we need to order, calculate when it would arrive
                    expected_arrival_date = (date.today() + timedelta(days=transit_days)).isoformat()
                elif in_transit_orders:
                    # Use the earliest expected arrival from in-transit orders
                    earliest_arrival = min(
                        order.expected_arrival_date 
                        for order in in_transit_orders 
                        if order.expected_arrival_date
                    )
                    expected_arrival_date = earliest_arrival.isoformat() if earliest_arrival else None
                else:
                    expected_arrival_date = None
                
                # Get factors affecting forecast (real-time weather, holidays, day of week)
                factors = self._get_forecast_factors(store_id, target_date)
                
                # Get expiry info
                days_until_expiry = getattr(inv_snapshot, 'days_until_expiry', None)
                expiry_date = getattr(inv_snapshot, 'expiry_date', None)
                expiry_buckets = getattr(inv_snapshot, 'expiry_buckets', {}) or {}
                
                # Items expiring in 1-3 days need priority attention
                expiring_soon = expiry_buckets.get('1_3', 0)
                needs_attention = (
                    refill_qty > 0 or 
                    order_qty > 0 or 
                    in_transit_qty > 0 or
                    (days_until_expiry is not None and days_until_expiry <= 3) or
                    expiring_soon > 0
                )
                
                # Include ALL items so user can see full inventory picture
                refill_plan.append({
                    'sku_id': product.sku_id,
                    'product_name': product.name or f"Product {product.sku_id}",
                    'category': product.category or "General",
                    'current_shelf_quantity': float(shelf_qty),
                    'current_backroom_quantity': float(backroom_qty),
                    'total_quantity': float(shelf_qty + backroom_qty),
                    'forecasted_demand_tomorrow': float(forecasted_demand),
                    'recommended_shelf_quantity': float(recommended_shelf_qty),
                    'refill_quantity': float(refill_qty),
                    'order_quantity': float(order_qty),
                    'in_transit_quantity': float(in_transit_qty),
                    'expected_arrival_date': expected_arrival_date,
                    'transit_days': transit_days,
                    'days_until_expiry': days_until_expiry,
                    'expiry_date': expiry_date.isoformat() if expiry_date else None,
                    'expiry_buckets': expiry_buckets,
                    'needs_attention': needs_attention,
                    'factors': factors
                })
            except Exception as e:
                self.logger.error(f"Error processing inventory item {inv_snapshot.id}: {e}")
                continue
        
        # Sort by refill quantity (highest first)
        refill_plan.sort(key=lambda x: x['refill_quantity'] + x['order_quantity'], reverse=True)
        
        return refill_plan
    
    def _get_forecast_factors(self, store_id: str, target_date: date) -> Dict[str, Any]:
        """
        Get factors affecting forecast for a given date using real-time data.
        
        Uses the centralized DemandFactorsService which provides:
        - Real weather data from Open-Meteo API
        - Real holiday data from Nager.Date API
        - Day-of-week patterns
        
        Args:
            store_id: Store identifier for location-specific data
            target_date: Date to get factors for
            
        Returns:
            Dictionary of factors with real-time data
        """
        try:
            # Get factors from centralized service (real-time APIs)
            factors_service = get_demand_factors_service()
            factors = factors_service.get_all_factors(store_id, target_date)
            
            return {
                'day_of_week': factors['day_of_week'],
                'is_weekend': factors['is_weekend'],
                'is_holiday': factors['is_holiday'],
                'is_pre_holiday': factors.get('is_pre_holiday', False),
                'holiday_name': factors.get('holiday_name'),
                'weather': factors['weather'],
                'temperature': factors['temperature'],
                'temperature_category': factors.get('temperature_category', 'mild'),
                'day_factor': factors['day_factor'],
                'weather_factor': factors['weather_factor'],
                'holiday_factor': factors['holiday_factor'],
                'seasonality_factor': factors['seasonality_factor'],
                'weather_source': factors.get('weather_source', 'Unknown'),
                'holiday_source': factors.get('holiday_source', 'Unknown')
            }
        except Exception as e:
            self.logger.warning(f"Error getting demand factors, using fallback: {e}")
            # Fallback to basic day-of-week only
            day_of_week = target_date.weekday()
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            is_weekend = day_of_week >= 5
            
            return {
                'day_of_week': day_names[day_of_week],
                'is_weekend': is_weekend,
                'is_holiday': False,
                'is_pre_holiday': False,
                'holiday_name': None,
                'weather': 'unknown',
                'temperature': None,
                'temperature_category': 'unknown',
                'day_factor': 1.2 if is_weekend else 1.0,
                'weather_factor': 1.0,
                'holiday_factor': 1.0,
                'seasonality_factor': 1.2 if is_weekend else 1.0,
                'weather_source': 'Fallback',
                'holiday_source': 'Fallback'
            }


# Global singleton instance
_refill_service_instance: Optional[RefillService] = None


def get_refill_service() -> RefillService:
    """Get or create the global RefillService singleton."""
    global _refill_service_instance
    if _refill_service_instance is None:
        _refill_service_instance = RefillService()
    return _refill_service_instance


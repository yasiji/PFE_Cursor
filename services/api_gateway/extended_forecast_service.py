"""Service for extended 30-day forecasts with revenue, profit, and loss calculations."""

from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import pandas as pd

from services.api_gateway.models import Store, Product, InventorySnapshot
from services.api_gateway.services import get_forecasting_service
from services.api_gateway.price_service import get_product_price, get_average_price_for_store
from services.api_gateway.profit_service import calculate_product_profit
from services.api_gateway.demand_factors_service import get_demand_factors_service
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class ExtendedForecastService:
    """Service for generating extended forecasts with financial projections."""
    
    def __init__(self):
        self.forecasting_service = get_forecasting_service()
        self.logger = get_logger(__name__)
    
    def generate_30_day_forecast(
        self,
        store_id: str,
        db: Session,
        category_filter: Optional[str] = None,
        product_filter: Optional[str] = None,
        horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate day-by-day forecast with revenue, profit, and loss.
        
        Args:
            store_id: Store identifier
            db: Database session
            category_filter: Optional category filter
            product_filter: Optional product SKU filter
            horizon_days: Number of days to forecast (default 30, max 30 for performance)
            
        Returns:
            Dictionary with daily forecasts and summary
        """
        # Limit horizon to 30 days for performance
        horizon_days = min(horizon_days, 30)
        today = date.today()
        daily_forecasts = []
        
        # Get products to forecast (limit to 10 for performance)
        query = db.query(Product)
        if product_filter:
            query = query.filter(Product.sku_id == product_filter)
        products = query.limit(10).all()  # Reduced from 20 to 10 for better performance
        
        if not products:
            return {
                "store_id": store_id,
                "forecast_period": "30d",
                "daily_forecasts": [],
                "summary": {
                    "total_revenue": 0.0,
                    "total_profit": 0.0,
                    "total_loss": 0.0,
                    "net_profit": 0.0,
                    "average_margin": 0.0
                }
            }
        
        # Get average price for store (fallback)
        avg_price = get_average_price_for_store(db, store_id=store_id)
        
        # Get current inventory for loss calculations
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == today
        ).all()
        inventory_map = {inv.product_id: inv for inv in inventory_snapshots}
        
        # Generate forecasts for each day
        # Optimize: Generate all forecasts at once for the full horizon, then extract daily values
        # This reduces the number of forecast calls from 30*N to just N
        product_forecasts_cache = {}
        for product in products:
            try:
                # Get full forecast once per product (optimization: one call instead of 30)
                forecasts = self.forecasting_service.forecast(
                    store_id=store_id,
                    sku_id=product.sku_id,
                    horizon_days=horizon_days,
                    include_uncertainty=False
                )
                product_forecasts_cache[product.id] = forecasts or []
            except Exception as e:
                self.logger.warning(f"Error getting forecast for product {product.sku_id}: {e}")
                product_forecasts_cache[product.id] = []
        
        for day_offset in range(1, horizon_days + 1):
            target_date = today + timedelta(days=day_offset)
            
            # Get factors for this date FIRST - these will be applied to predictions
            # Uses real-time data from Open-Meteo (weather) and Nager.Date (holidays)
            factors = self._get_forecast_factors(store_id, target_date)
            seasonality_multiplier = factors.get('seasonality_factor', 1.0)
            
            # Aggregate forecasts across products
            total_demand = 0.0
            total_revenue = 0.0
            total_profit = 0.0
            total_loss = 0.0
            
            for product in products:
                try:
                    # Get forecast from cache
                    forecasts = product_forecasts_cache.get(product.id, [])
                    
                    if forecasts and len(forecasts) >= day_offset:
                        base_demand = forecasts[day_offset - 1].get('predicted_demand', 0.0)
                        # APPLY SEASONALITY FACTOR to the prediction!
                        predicted_demand = base_demand * seasonality_multiplier
                    else:
                        predicted_demand = 0.0
                    
                    # Get price
                    price = get_product_price(db, product_id=product.id, target_date=target_date)
                    if price is None:
                        price = avg_price
                    
                    # Calculate revenue
                    revenue = predicted_demand * price
                    total_revenue += revenue
                    total_demand += predicted_demand
                    
                    # Calculate profit
                    profit_data = calculate_product_profit(
                        db=db,
                        product_id=product.id,
                        revenue=revenue,
                        items_sold=predicted_demand,
                        target_date=target_date
                    )
                    total_profit += profit_data.get('profit', 0.0)
                    
                    # Calculate predicted loss (from expiry/waste)
                    inv = inventory_map.get(product.id)
                    if inv and inv.quantity > 0:
                        # Estimate loss from items that might expire
                        expiry_buckets = inv.expiry_buckets or {}
                        qty_expiring = expiry_buckets.get("1_3", 0.0)
                        if qty_expiring > 0 and day_offset <= 3:
                            # Items expiring soon might not sell
                            cost_per_unit = profit_data.get('cost_per_unit', price * 0.7)
                            potential_loss = qty_expiring * cost_per_unit * 0.3  # 30% might not sell
                            total_loss += potential_loss
                
                except Exception as e:
                    self.logger.warning(f"Error forecasting for product {product.sku_id}: {e}")
                    continue
            
            # Calculate margin
            margin_percent = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0
            net_profit = total_profit - total_loss
            
            # factors already computed at start of loop with seasonality applied
            
            daily_forecasts.append({
                "date": target_date.isoformat(),
                "predicted_demand": round(total_demand, 2),
                "predicted_revenue": round(total_revenue, 2),
                "predicted_profit": round(total_profit, 2),
                "predicted_loss": round(total_loss, 2),
                "net_profit": round(net_profit, 2),
                "predicted_margin": round(margin_percent, 2),
                "factors": factors
            })
        
        # Calculate summary
        total_revenue = sum(f['predicted_revenue'] for f in daily_forecasts)
        total_profit = sum(f['predicted_profit'] for f in daily_forecasts)
        total_loss = sum(f['predicted_loss'] for f in daily_forecasts)
        net_profit = total_profit - total_loss
        avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0
        
        return {
            "store_id": store_id,
            "forecast_period": f"{horizon_days}d",
            "daily_forecasts": daily_forecasts,
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "net_profit": round(net_profit, 2),
                "average_margin": round(avg_margin, 2)
            }
        }
    
    def _get_forecast_factors(self, store_id: str, target_date: date) -> Dict[str, Any]:
        """
        Get factors affecting forecast for a given date using REAL-TIME DATA.
        
        Uses the centralized DemandFactorsService which provides:
        - Real weather data from Open-Meteo API
        - Real holiday data from Nager.Date API  
        - Day-of-week patterns based on retail analytics
        
        Returns factors that WILL BE APPLIED to predictions:
        - Weekend boost: typically +10-30% on weekends
        - Weather impact: real-time weather conditions affect demand
        - Holiday boost: real holidays from official calendar
        
        Args:
            store_id: Store identifier for location-specific data
            target_date: Date to get factors for
            
        Returns:
            Dictionary of real-time factors
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
                'day_factor': round(factors['day_factor'], 2),
                'weather_factor': round(factors['weather_factor'], 2),
                'holiday_factor': round(factors['holiday_factor'], 2),
                'seasonality_factor': round(factors['seasonality_factor'], 2),
                'weather_source': factors.get('weather_source', 'Open-Meteo API'),
                'holiday_source': factors.get('holiday_source', 'Nager.Date API'),
                'weather_description': factors.get('weather_description', ''),
                'holiday_description': factors.get('holiday_description', '')
            }
        except Exception as e:
            self.logger.warning(f"Error getting demand factors from API, using fallback: {e}")
            # Fallback to basic calculation if API fails
            return self._get_fallback_factors(target_date)
    
    def _get_fallback_factors(self, target_date: date) -> Dict[str, Any]:
        """Fallback factor calculation when APIs are unavailable."""
        day_of_week = target_date.weekday()
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        is_weekend = day_of_week >= 5
        
        day_factors = {0: 0.85, 1: 0.88, 2: 0.95, 3: 1.00, 4: 1.10, 5: 1.25, 6: 1.15}
        day_factor = day_factors.get(day_of_week, 1.0)
        
        return {
            'day_of_week': day_names[day_of_week],
            'is_weekend': is_weekend,
            'is_holiday': False,
            'is_pre_holiday': False,
            'holiday_name': None,
            'weather': 'unknown',
            'temperature': None,
            'temperature_category': 'unknown',
            'day_factor': day_factor,
            'weather_factor': 1.0,
            'holiday_factor': 1.0,
            'seasonality_factor': day_factor,
            'weather_source': 'Fallback',
            'holiday_source': 'Fallback',
            'weather_description': 'API unavailable',
            'holiday_description': 'API unavailable'
        }


def get_extended_forecast_service() -> ExtendedForecastService:
    """Get or create the global ExtendedForecastService singleton."""
    global _extended_forecast_service_instance
    if '_extended_forecast_service_instance' not in globals():
        _extended_forecast_service_instance = ExtendedForecastService()
    return _extended_forecast_service_instance


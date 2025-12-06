"""Business logic services for API Gateway."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from shared.logging_setup import get_logger

from services.forecasting.models.lightgbm_model import LightGBMForecaster
from services.replenishment.policy import OrderUpToPolicy
from services.replenishment.expiry import InventoryAgeTracker
from services.replenishment.markdown import MarkdownPolicy
from services.ingestion.datasets import load_freshretailnet_dataset
from shared.config import get_config
from shared.logging_setup import get_logger
from shared.column_mappings import COLUMN_MAPPINGS
from services.forecasting.features.feature_engineering import create_forecast_features

logger = get_logger(__name__)
config = get_config()

# Global singleton instances
_forecasting_service_instance: Optional['ForecastingService'] = None
_replenishment_service_instance: Optional['ReplenishmentService'] = None


def get_forecasting_service() -> 'ForecastingService':
    """Get or create the global ForecastingService singleton."""
    global _forecasting_service_instance
    if _forecasting_service_instance is None:
        _forecasting_service_instance = ForecastingService()
    return _forecasting_service_instance


def get_replenishment_service() -> 'ReplenishmentService':
    """Get or create the global ReplenishmentService singleton."""
    global _replenishment_service_instance
    if _replenishment_service_instance is None:
        _replenishment_service_instance = ReplenishmentService(forecasting_service=get_forecasting_service())
    return _replenishment_service_instance


def load_mvp_data() -> Tuple[pd.DataFrame, str, str, str, str]:
    """
    Load historical MVP data and return DataFrame with column references.
    
    Returns:
        Tuple containing (dataframe, store column, sku column, date column, sales column)
    """
    dataset = load_freshretailnet_dataset(use_local=True)
    df = dataset['train'].to_pandas()
    
    store_col = COLUMN_MAPPINGS.get('store_id', 'store_id')
    sku_col = COLUMN_MAPPINGS.get('sku_id', 'product_id')
    date_col = COLUMN_MAPPINGS.get('date_col', 'dt')
    sales_col = COLUMN_MAPPINGS.get('sales_col', 'sale_amount')

    # Trim to essential columns for faster filtering
    df = df[[store_col, sku_col, date_col, sales_col]].copy()

    # Normalize data types
    df[store_col] = df[store_col].astype(str)
    df[sku_col] = df[sku_col].astype(str)
    if df[date_col].dtype == 'object':
        df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values([store_col, sku_col, date_col]).reset_index(drop=True)

    return df, store_col, sku_col, date_col, sales_col


class ForecastingService:
    """Service for demand forecasting."""
    
    def __init__(self):
        """Initialize forecasting service."""
        self.model: Optional[LightGBMForecaster] = None
        self._historical_data: Optional[Tuple[pd.DataFrame, str, str, str, str]] = None
        self.feature_cols: Optional[List[str]] = None
        self._store_sku_cache: dict[tuple[str, str], pd.DataFrame] = {}
        self._seasonal_cache: dict[tuple[str, str], dict[int, float]] = {}
        self._load_model()
    
    def _load_model(self):
        """Load trained LightGBM model."""
        model_path = Path(config.data.models_dir) / "lightgbm_model.pkl"
        if model_path.exists():
            try:
                model_data = joblib.load(model_path)
                # Model is saved as dict with 'model', 'feature_cols', etc.
                if isinstance(model_data, dict):
                    self.model = model_data.get('model')
                    self.feature_cols = model_data.get('feature_cols')
                else:
                    # Fallback: assume it's the model directly
                    self.model = model_data
                    if hasattr(model_data, 'feature_cols'):
                        self.feature_cols = getattr(model_data, 'feature_cols')
                
                logger.info("Forecasting service initialized with LightGBM model")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self.model = None
                self.feature_cols = None
        else:
            logger.warning(f"Model not found at {model_path}")
    
    def _get_historical_data(self) -> Optional[Tuple[pd.DataFrame, str, str, str, str]]:
        """Lazy-load historical MVP data for forecasting."""
        if self._historical_data is None:
            try:
                self._historical_data = load_mvp_data()
            except Exception as exc:
                logger.error(f"Failed to load historical data: {exc}")
                self._historical_data = None
        return self._historical_data

    def _get_store_sku_history(self, store_id: str, sku_id: str) -> Optional[pd.DataFrame]:
        """Get cached historical data for a specific store/SKU."""
        data_tuple = self._get_historical_data()
        if not data_tuple:
            return None

        df, store_col, sku_col, date_col, sales_col = data_tuple
        cache_key = (str(store_id), str(sku_id))
        if cache_key not in self._store_sku_cache:
            subset = df[
                (df[store_col] == cache_key[0]) &
                (df[sku_col] == cache_key[1])
            ].copy()
            if subset.empty:
                return None
            subset = subset.rename(columns={sales_col: 'demand', date_col: 'date'})
            self._store_sku_cache[cache_key] = subset
            # Pre-compute weekday seasonal profile
            weekday_profile = subset.groupby(subset['date'].dt.dayofweek)['demand'].mean().to_dict()
            self._seasonal_cache[cache_key] = weekday_profile
        return self._store_sku_cache[cache_key].copy()

    def _get_seasonal_baseline(self, store_id: str, sku_id: str, weekday: int, default: float) -> float:
        """Return seasonal baseline demand for the given weekday."""
        profile = self._seasonal_cache.get((str(store_id), str(sku_id)))
        if not profile:
            return default
        if weekday in profile and np.isfinite(profile[weekday]):
            return float(profile[weekday])
        finite_values = [float(v) for v in profile.values() if np.isfinite(v)]
        if finite_values:
            return float(np.mean(finite_values))
        return default
    
    def _get_day_factor(self, target_date: date) -> float:
        """
        Get demand multiplier based on day of week.
        
        Retail patterns: weekends higher, Monday/Tuesday lower.
        """
        day_of_week = target_date.weekday()
        day_factors = {
            0: 0.85,   # Monday - lowest
            1: 0.88,   # Tuesday - low
            2: 0.95,   # Wednesday - average
            3: 1.00,   # Thursday - average
            4: 1.10,   # Friday - high (weekend prep)
            5: 1.25,   # Saturday - peak
            6: 1.15,   # Sunday - high but slightly less than Saturday
        }
        return day_factors.get(day_of_week, 1.0)
    
    def _get_weather_factor(self, target_date: date) -> float:
        """
        Get demand multiplier based on weather/season.
        
        Hot weather increases fresh/cold product demand.
        Cold weather decreases it.
        """
        month = target_date.month
        if month in [6, 7, 8]:  # Summer
            return 1.15
        elif month in [12, 1, 2]:  # Winter
            return 0.90
        return 1.0
    
    def _apply_external_factors(self, base_demand: float, target_date: date) -> float:
        """Apply day-of-week and weather factors to base demand."""
        day_factor = self._get_day_factor(target_date)
        weather_factor = self._get_weather_factor(target_date)
        return base_demand * day_factor * weather_factor

    def forecast(
        self,
        store_id: str,
        sku_id: str,
        horizon_days: int = 7,
        include_uncertainty: bool = False
    ) -> List[Dict]:
        """
        Generate forecast for a store-SKU combination.
        
        Args:
            store_id: Store identifier
            sku_id: SKU identifier
            horizon_days: Number of days to forecast
            include_uncertainty: Whether to include prediction intervals
            
        Returns:
            List of forecast dictionaries
        """
        if self.model is None:
            raise ValueError("Model not loaded. Please train the model first.")
        
        # Load historical data for feature engineering
        try:
            data_tuple = self._get_historical_data()
            if not data_tuple:
                raise ValueError("Historical data unavailable")

            df, store_col, sku_col, _, _ = data_tuple

            store_sku_data = self._get_store_sku_history(store_id, sku_id)
            if store_sku_data is None or store_sku_data.empty:
                logger.warning(
                    "No historical data for store/SKU, using default forecast",
                    store_id=store_id,
                    sku_id=sku_id
                )
                return self._build_constant_forecast(horizon_days, include_uncertainty)
            df_daily = store_sku_data.sort_values('date')

            historical_std = df_daily['demand'].std() if len(df_daily) > 1 else None

            if self.model is None or not self.feature_cols:
                logger.warning(
                    "LightGBM model unavailable, falling back to statistical forecast",
                    store_id=store_id,
                    sku_id=sku_id
                )
                return self._generate_statistical_forecast(
                    df_daily,
                    horizon_days=horizon_days,
                    include_uncertainty=include_uncertainty,
                    historical_std=historical_std,
                    store_id=str(store_id),
                    sku_id=str(sku_id)
                )

            return self._generate_model_forecast(
                df_daily=df_daily,
                store_col=store_col,
                sku_col=sku_col,
                horizon_days=horizon_days,
                include_uncertainty=include_uncertainty,
                historical_std=historical_std
            )
            
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            raise
    
    def _simple_forecast(self, df_daily: pd.DataFrame, horizon: int) -> float:
        """Simple forecast using moving average (fallback)."""
        if len(df_daily) == 0:
            return 0.0
        # Use 7-day moving average
        window = min(7, len(df_daily))
        return df_daily['demand'].tail(window).mean()

    def _generate_statistical_forecast(
        self,
        df_daily: pd.DataFrame,
        horizon_days: int,
        include_uncertainty: bool,
        historical_std: Optional[float] = None,
        store_id: Optional[str] = None,
        sku_id: Optional[str] = None
    ) -> List[Dict]:
        """Generate forecasts using a moving-average heuristic with external factors."""
        forecasts: List[Dict] = []
        last_date = pd.to_datetime(df_daily['date'].max())
        working_df = df_daily[['date', 'demand']].copy()

        for i in range(horizon_days):
            base_demand = self._simple_forecast(working_df, horizon=i + 1)
            target_date = last_date + timedelta(days=i + 1)
            target_date_obj = target_date.date() if hasattr(target_date, 'date') else target_date
            
            # Get historical seasonal baseline
            seasonal = self._get_seasonal_baseline(
                store_id or "",
                sku_id or "",
                target_date.weekday(),
                default=float(base_demand)
            )
            
            # Blend moving average with seasonal baseline
            blended_demand = 0.7 * float(base_demand) + 0.3 * seasonal
            
            # APPLY EXTERNAL FACTORS (day-of-week, weather)
            pred_demand = self._apply_external_factors(blended_demand, target_date_obj)
            
            forecast_item = {
                "date": target_date_obj,
                "predicted_demand": max(0.0, float(pred_demand))
            }
            if include_uncertainty:
                std = historical_std if historical_std and historical_std > 0 else abs(pred_demand) * 0.3
                forecast_item["lower_bound"] = max(0.0, pred_demand - 1.96 * std)
                forecast_item["upper_bound"] = pred_demand + 1.96 * std
            forecasts.append(forecast_item)
            working_df = pd.concat(
                [working_df, pd.DataFrame({"date": [target_date], "demand": [pred_demand]})],
                ignore_index=True
            )

        return forecasts

    def _generate_model_forecast(
        self,
        df_daily: pd.DataFrame,
        store_col: str,
        sku_col: str,
        horizon_days: int,
        include_uncertainty: bool,
        historical_std: Optional[float] = None
    ) -> List[Dict]:
        """Generate forecasts using the trained LightGBM model with external factors."""
        if self.feature_cols is None:
            raise ValueError("Model feature columns are not available")

        store_value = df_daily[store_col].iloc[0]
        sku_value = df_daily[sku_col].iloc[0]
        history = df_daily[[store_col, sku_col, 'date', 'demand']].copy().sort_values('date')
        forecasts: List[Dict] = []

        for _ in range(horizon_days):
            target_date = pd.to_datetime(history['date'].max()) + timedelta(days=1)
            target_date_obj = target_date.date()
            future_row = {
                store_col: store_value,
                sku_col: sku_value,
                'date': target_date,
                'demand': np.nan
            }
            history = pd.concat([history, pd.DataFrame([future_row])], ignore_index=True)
            features = create_forecast_features(
                history.copy(),
                date_col='date',
                target_col='demand',
                store_col=store_col,
                sku_col=sku_col
            )
            future_features = features[features['date'] == target_date]
            if future_features.empty:
                raise ValueError("Unable to construct feature row for forecast date")

            future_features = future_features.tail(1)
            model_input = self._prepare_model_inputs(future_features)
            base_pred = float(self.model.predict(model_input.values)[0])
            
            # Get historical seasonal baseline
            seasonal = self._get_seasonal_baseline(
                store_value,
                sku_value,
                target_date.weekday(),
                default=base_pred
            )
            
            # Blend model prediction with seasonal baseline
            blended_pred = 0.7 * base_pred + 0.3 * seasonal
            
            # APPLY EXTERNAL FACTORS (day-of-week boost, weather impact)
            pred_value = self._apply_external_factors(blended_pred, target_date_obj)

            forecast_entry = {
                "date": target_date_obj,
                "predicted_demand": max(0.0, pred_value)
            }

            if include_uncertainty:
                std = historical_std if historical_std and historical_std > 0 else abs(pred_value) * 0.3
                forecast_entry["lower_bound"] = max(0.0, pred_value - 1.96 * std)
                forecast_entry["upper_bound"] = pred_value + 1.96 * std

            forecasts.append(forecast_entry)
            history.loc[history['date'] == target_date, 'demand'] = pred_value

        return forecasts

    def _prepare_model_inputs(self, feature_row: pd.DataFrame) -> pd.DataFrame:
        """Ensure feature row contains all columns required by the model."""
        if self.feature_cols is None:
            raise ValueError("Feature columns not set for forecasting model")

        working_row = feature_row.copy()
        for col in self.feature_cols:
            if col not in working_row.columns:
                working_row[col] = 0.0

        return working_row[self.feature_cols].fillna(0.0)

    def _build_constant_forecast(
        self,
        horizon_days: int,
        include_uncertainty: bool = False,
        base_value: float = 10.0
    ) -> List[Dict]:
        """Fallback constant forecast when no historical data is available."""
        start_date = datetime.utcnow().date()
        forecasts: List[Dict] = []
        for i in range(horizon_days):
            target_date = start_date + timedelta(days=i + 1)
            forecast_item = {
                "date": target_date,
                "predicted_demand": base_value
            }
            if include_uncertainty:
                std = base_value * 0.3
                forecast_item["lower_bound"] = max(0, base_value - 1.96 * std)
                forecast_item["upper_bound"] = base_value + 1.96 * std
            forecasts.append(forecast_item)
        return forecasts


class ReplenishmentService:
    """Service for replenishment recommendations."""
    
    def __init__(self, forecasting_service: Optional[ForecastingService] = None):
        """Initialize replenishment service."""
        self.policy = OrderUpToPolicy()
        self.markdown_policy = MarkdownPolicy()
        self.logger = get_logger(__name__)
        self.forecasting_service = forecasting_service
        self.coverage_days = config.models.replenishment.target_coverage_days
        # Expiry tracker will be initialized when needed with current date
    
    def generate_replenishment_plan(
        self,
        store_id: str,
        target_date: date,
        current_inventory: List[Dict],
        forecasts: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Generate replenishment plan for a store.
        
        Args:
            store_id: Store identifier
            target_date: Target date for the plan
            current_inventory: List of current inventory items
            forecasts: Optional pre-computed forecasts
            
        Returns:
            List of replenishment recommendations
        """
        recommendations = []
        
        # If forecasts not provided, we'd need to generate them
        # For now, assume they're provided or use simple heuristic
        
        for inv_item in current_inventory:
            try:
                sku_id = str(inv_item['sku_id'])
                quantity = float(inv_item['quantity'])
                expiry_date = inv_item.get('expiry_date')
                
                # Convert expiry_date to date if it's a string
                expiry_date_obj = None
                if expiry_date:
                    if isinstance(expiry_date, str):
                        expiry_date_obj = pd.to_datetime(expiry_date).date()
                    elif isinstance(expiry_date, date):
                        expiry_date_obj = expiry_date
                    else:
                        self.logger.warning(f"Invalid expiry_date format for SKU {sku_id}: {expiry_date}")
                
                forecasted_demand = None
                if forecasts:
                    forecasted_demand = self._resolve_forecast_from_payload(forecasts, sku_id)
                if forecasted_demand is None:
                    forecasted_demand = self._get_forecast_for_sku(store_id, sku_id, target_date)
                
                # Calculate order quantity
                order_qty = self.policy.calculate_order_quantity(
                    forecasted_demand=forecasted_demand,
                    current_inventory=quantity,
                    inbound_orders=0.0,
                    expiring_units=0.0,
                    demand_horizon_days=self.coverage_days
                )
                
                # Check for markdown recommendations
                markdown = None
                if expiry_date_obj:
                    days_until_expiry = (expiry_date_obj - target_date).days
                    if days_until_expiry <= 3 and quantity > 0:
                        markdown_rec = self.markdown_policy.recommend_markdown(
                            days_until_expiry=days_until_expiry,
                            current_inventory=quantity,
                            category_id=None  # Would need to look up
                        )
                        if markdown_rec:
                            markdown = {
                                "discount_percent": markdown_rec['discount_percent'],
                                "effective_date": str(target_date),
                                "reason": markdown_rec.get('reason', 'Near expiry')
                            }
                
                recommendations.append({
                    "sku_id": sku_id,
                    "order_quantity": max(0, order_qty),
                    "markdown": markdown
                })
            except Exception as e:
                self.logger.error(f"Error processing inventory item {inv_item}: {e}")
                # Continue with next item
                continue
        
        return recommendations
    
    def _resolve_forecast_from_payload(self, forecasts: Optional[Dict], sku_id: str) -> Optional[float]:
        """Resolve forecasted demand from request payload if provided."""
        if not forecasts:
            return None
        sku_key = str(sku_id)
        sku_forecasts = forecasts.get(sku_key) if isinstance(forecasts, dict) else None
        if not sku_forecasts:
            return None
        values = [
            item.get("predicted_demand", 0.0)
            for item in sku_forecasts
            if isinstance(item, dict)
        ]
        if not values:
            return None
        horizon = max(1, min(self.coverage_days, len(values)))
        coverage_values = values[:horizon]
        return float(np.sum(coverage_values))

    def _get_forecast_for_sku(self, store_id: str, sku_id: str, target_date: date) -> float:
        """Get forecast for a SKU using ForecastingService."""
        default_value = 10.0
        if not self.forecasting_service:
            return default_value
        try:
            horizon = max(1, min(self.coverage_days, 14))
            forecasts = self.forecasting_service.forecast(
                store_id=store_id,
                sku_id=sku_id,
                horizon_days=horizon,
                include_uncertainty=False
            )
            if not forecasts:
                return default_value
            predicted_values = [
                max(0.0, float(item.get("predicted_demand", 0.0)))
                for item in forecasts
            ]
            coverage_values = predicted_values[:self.coverage_days]
            total_demand = float(np.sum(coverage_values))
            if np.isfinite(total_demand) and total_demand > 0:
                return total_demand
        except Exception as exc:
            self.logger.warning(
                "Forecast service unavailable, falling back to default",
                store_id=store_id,
                sku_id=sku_id,
                error=str(exc)
            )
        return default_value


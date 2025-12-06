"""
Sales Data Service - Queries and aggregates data from FreshRetailNet-50K dataset.

This service provides real sales data for the store manager application
by querying the FreshRetailNet-50K dataset.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from functools import lru_cache
from pathlib import Path

from services.ingestion.datasets import load_freshretailnet_dataset
from shared.column_mappings import COLUMN_MAPPINGS
from shared.logging_setup import get_logger
from shared.config import get_config

logger = get_logger(__name__)
config = get_config()

# Cache for loaded dataset (lazy loading)
_dataset_cache: Optional[pd.DataFrame] = None
_column_info: Optional[Dict[str, str]] = None
_column_info: Optional[Dict[str, str]] = None


def _load_dataset() -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Load and cache the FreshRetailNet-50K dataset."""
    global _dataset_cache, _column_info
    
    if _dataset_cache is not None:
        return _dataset_cache, _column_info
    
    try:
        logger.info("Loading FreshRetailNet-50K dataset for sales data")
        dataset = load_freshretailnet_dataset(use_local=True)
        df = dataset['train'].to_pandas()
        
        # Get column mappings
        store_col = COLUMN_MAPPINGS.get('store_id', 'store_id')
        sku_col = COLUMN_MAPPINGS.get('sku_id', 'product_id')
        date_col = COLUMN_MAPPINGS.get('date_col', 'dt')
        sales_col = COLUMN_MAPPINGS.get('sales_col', 'sale_amount')
        category_col = COLUMN_MAPPINGS.get('category_col', 'first_category_id')
        
        # Normalize data types
        df[store_col] = df[store_col].astype(str)
        df[sku_col] = df[sku_col].astype(str)
        if df[date_col].dtype == 'object':
            df[date_col] = pd.to_datetime(df[date_col])
        
        # Ensure date column is date type
        if pd.api.types.is_datetime64_any_dtype(df[date_col]):
            df[date_col] = df[date_col].dt.date
        
        _column_info = {
            'store_col': store_col,
            'sku_col': sku_col,
            'date_col': date_col,
            'sales_col': sales_col,
            'category_col': category_col
        }
        
        _dataset_cache = df
        logger.info(f"Dataset loaded: {len(df):,} records, {df[date_col].min()} to {df[date_col].max()}")
        
        return df, _column_info
    except Exception as e:
        logger.error(f"Error loading dataset: {e}", exc_info=True)
        raise


class SalesDataService:
    """Service for querying and aggregating sales data from FreshRetailNet-50K."""
    
    def __init__(self):
        """Initialize the sales data service."""
        self.df: Optional[pd.DataFrame] = None
        self.cols: Optional[Dict[str, str]] = None
        self.latest_date: Optional[date] = None  # Latest date in dataset
        self._load_data()
    
    def _load_data(self):
        """Load dataset on initialization."""
        try:
            self.df, self.cols = _load_dataset()
            if self.df is not None and self.cols is not None:
                # Get the latest date in the dataset
                date_col = self.cols['date_col']
                self.latest_date = self.df[date_col].max()
                logger.info(f"Sales data service initialized. Latest date in dataset: {self.latest_date}")
        except Exception as e:
            logger.error(f"Failed to initialize sales data service: {e}")
            self.df = None
            self.cols = None
            self.latest_date = None
    
    def get_effective_date(self, target_date: Optional[date] = None) -> date:
        """
        Get the effective date to use for queries.
        
        Since the dataset is historical, if target_date is not in the dataset,
        we use the latest available date instead.
        """
        if target_date is None:
            target_date = date.today()
        
        # If dataset has no data, return target_date as-is
        if self.latest_date is None:
            return target_date
        
        # If target_date is in the future or not in dataset, use latest available date
        if target_date > self.latest_date:
            logger.debug(f"Target date {target_date} is after latest dataset date {self.latest_date}, using latest date")
            return self.latest_date
        
        return target_date
    
    def get_store_sales(
        self,
        store_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get daily sales data for a store within a date range.
        
        Args:
            store_id: Store identifier
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of dicts with keys: date, sales, revenue, items_sold
        """
        if self.df is None:
            logger.warning("Dataset not loaded, returning empty sales data")
            return []
        
        try:
            store_col = self.cols['store_col']
            date_col = self.cols['date_col']
            sales_col = self.cols['sales_col']
            
            # Filter by store and date range
            mask = (
                (self.df[store_col] == str(store_id)) &
                (self.df[date_col] >= start_date) &
                (self.df[date_col] <= end_date)
            )
            filtered_df = self.df[mask].copy()
            
            if len(filtered_df) == 0:
                return []
            
            # Aggregate by date
            daily_sales = filtered_df.groupby(date_col)[sales_col].agg([
                ('sales', 'sum'),
                ('items_sold', 'count')
            ]).reset_index()
            
            # Calculate revenue (assuming average price - in production, use actual prices)
            # For now, we'll use a simple multiplier or get from product prices
            avg_price = self._get_average_price(store_id)
            daily_sales['revenue'] = daily_sales['sales'] * avg_price
            
            # Format results
            result = []
            for _, row in daily_sales.iterrows():
                result.append({
                    'date': row[date_col],
                    'sales': float(row['sales']),
                    'revenue': float(row['revenue']),
                    'items_sold': int(row['items_sold'])
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting store sales: {e}", exc_info=True)
            return []
    
    def get_product_sales(
        self,
        store_id: str,
        sku_id: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Get sales statistics for a specific product in a store.
        
        Returns:
            Dict with keys: items_sold_today, items_sold_week, items_sold_month
        """
        if self.df is None:
            return {
                'items_sold_today': 0,
                'items_sold_week': 0,
                'items_sold_month': 0
            }
        
        try:
            store_col = self.cols['store_col']
            sku_col = self.cols['sku_col']
            date_col = self.cols['date_col']
            sales_col = self.cols['sales_col']
            
            # Use latest date from dataset instead of today
            effective_today = self.get_effective_date()
            week_start = effective_today - timedelta(days=7)
            month_start = effective_today - timedelta(days=30)
            
            # Filter by store, SKU, and date
            mask = (
                (self.df[store_col] == str(store_id)) &
                (self.df[sku_col] == str(sku_id))
            )
            filtered_df = self.df[mask].copy()
            
            if len(filtered_df) == 0:
                return {
                    'items_sold_today': 0,
                    'items_sold_week': 0,
                    'items_sold_month': 0
                }
            
            # Calculate sales for different periods using effective date
            today_mask = filtered_df[date_col] == effective_today
            week_mask = (filtered_df[date_col] >= week_start) & (filtered_df[date_col] <= effective_today)
            month_mask = (filtered_df[date_col] >= month_start) & (filtered_df[date_col] <= effective_today)
            
            items_sold_today = float(filtered_df[today_mask][sales_col].sum()) if today_mask.any() else 0.0
            items_sold_week = float(filtered_df[week_mask][sales_col].sum()) if week_mask.any() else 0.0
            items_sold_month = float(filtered_df[month_mask][sales_col].sum()) if month_mask.any() else 0.0
            
            return {
                'items_sold_today': items_sold_today,
                'items_sold_week': items_sold_week,
                'items_sold_month': items_sold_month
            }
        except Exception as e:
            logger.error(f"Error getting product sales: {e}", exc_info=True)
            return {
                'items_sold_today': 0,
                'items_sold_week': 0,
                'items_sold_month': 0
            }
    
    def get_store_stats(
        self,
        store_id: str,
        target_date: date = None
    ) -> Dict:
        """
        Get store statistics for a specific date (defaults to today).
        
        Returns:
            Dict with keys: sales_today, revenue_today, items_sold
        """
        if self.df is None:
            return {
                'sales_today': 0.0,
                'revenue_today': 0.0,
                'items_sold': 0
            }
        
        if target_date is None:
            # Use latest date from dataset instead of today
            target_date = self.get_effective_date()
        else:
            # Ensure target_date is within dataset range
            target_date = self.get_effective_date(target_date)
        
        try:
            sales_data = self.get_store_sales(store_id, target_date, target_date)
            
            if sales_data:
                data = sales_data[0]
                return {
                    'sales_today': data['sales'],
                    'revenue_today': data['revenue'],
                    'items_sold': data['items_sold']
                }
            else:
                return {
                    'sales_today': 0.0,
                    'revenue_today': 0.0,
                    'items_sold': 0
                }
        except Exception as e:
            logger.error(f"Error getting store stats: {e}", exc_info=True)
            return {
                'sales_today': 0.0,
                'revenue_today': 0.0,
                'items_sold': 0
            }
    
    def _get_average_price(self, store_id: str) -> float:
        """
        Get average price for products in a store.
        
        Generates a varied average based on store to simulate real pricing.
        """
        import hashlib
        
        # Generate store-specific average price (between $2.50 - $5.50)
        store_hash = int(hashlib.md5(str(store_id).encode()).hexdigest()[:8], 16)
        base_avg = 2.50 + (store_hash % 300) / 100.0
        return round(base_avg, 2)
    
    def get_product_price(self, sku_id: str) -> float:
        """
        Get price for a specific product.
        
        Generates a varied price based on SKU to simulate real pricing.
        """
        import hashlib
        
        # Generate SKU-specific price (between $0.99 - $9.99)
        sku_hash = int(hashlib.md5(str(sku_id).encode()).hexdigest()[:8], 16)
        normalized = (sku_hash % 10000) / 10000.0
        base_price = 0.99 + (9.00 * normalized)
        
        # Round to realistic price endings
        price_int = int(base_price)
        decimal = base_price - price_int
        if decimal < 0.25:
            return price_int + 0.29
        elif decimal < 0.50:
            return price_int + 0.49
        elif decimal < 0.75:
            return price_int + 0.79
        else:
            return price_int + 0.99
    
    def get_store_daily_sales(
        self,
        store_id: str,
        target_date: date = None
    ) -> Dict:
        """
        Get daily sales for a specific date.
        
        Args:
            store_id: Store identifier
            target_date: Target date (defaults to latest date in dataset)
            
        Returns:
            Dict with total_units and total_revenue
        """
        if self.df is None:
            return {
                'total_units': 0,
                'total_revenue': 0.0
            }
        
        if target_date is None:
            target_date = self.get_effective_date()
        else:
            target_date = self.get_effective_date(target_date)
        
        try:
            store_col = self.cols['store_col']
            date_col = self.cols['date_col']
            sales_col = self.cols['sales_col']
            
            # Filter by store and date
            mask = (
                (self.df[store_col] == str(store_id)) &
                (self.df[date_col] == target_date)
            )
            filtered_df = self.df[mask]
            
            if len(filtered_df) == 0:
                return {
                    'total_units': 0,
                    'total_revenue': 0.0
                }
            
            total_units = float(filtered_df[sales_col].sum())
            avg_price = self._get_average_price(store_id)
            total_revenue = total_units * avg_price
            
            return {
                'total_units': total_units,
                'total_revenue': total_revenue
            }
        except Exception as e:
            logger.error(f"Error getting store daily sales: {e}", exc_info=True)
            return {
                'total_units': 0,
                'total_revenue': 0.0
            }


# Global instance
_sales_service: Optional[SalesDataService] = None


def get_sales_service() -> SalesDataService:
    """Get or create the global sales data service instance."""
    global _sales_service
    if _sales_service is None:
        _sales_service = SalesDataService()
    return _sales_service


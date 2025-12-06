"""Forecast accuracy calculation service."""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from services.api_gateway.models import Forecast, Store, Product
from services.api_gateway.sales_data_service import get_sales_service
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_mae(actual: List[float], predicted: List[float]) -> float:
    """Calculate Mean Absolute Error."""
    if len(actual) != len(predicted) or len(actual) == 0:
        return 0.0
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)


def calculate_mape(actual: List[float], predicted: List[float]) -> float:
    """Calculate Mean Absolute Percentage Error."""
    if len(actual) != len(predicted) or len(actual) == 0:
        return 0.0
    
    errors = []
    for a, p in zip(actual, predicted):
        if a != 0:
            errors.append(abs((a - p) / a) * 100)
    
    return sum(errors) / len(errors) if errors else 0.0


def calculate_wape(actual: List[float], predicted: List[float]) -> float:
    """Calculate Weighted Absolute Percentage Error."""
    if len(actual) != len(predicted) or len(actual) == 0:
        return 0.0
    
    total_actual = sum(actual)
    if total_actual == 0:
        return 0.0
    
    total_error = sum(abs(a - p) for a, p in zip(actual, predicted))
    return (total_error / total_actual) * 100.0


def calculate_bias(actual: List[float], predicted: List[float]) -> float:
    """Calculate forecast bias (positive = over-forecast, negative = under-forecast)."""
    if len(actual) != len(predicted) or len(actual) == 0:
        return 0.0
    return sum(p - a for a, p in zip(actual, predicted)) / len(actual)


def calculate_forecast_accuracy(
    db: Session,
    store_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    product_id: Optional[int] = None,
    days: Optional[int] = None
) -> Dict:
    """
    Calculate forecast accuracy metrics by comparing forecasts with actual sales.
    
    Args:
        db: Database session
        store_id: Store identifier
        start_date: Start date for comparison (defaults to 30 days ago)
        end_date: End date for comparison (defaults to today)
        product_id: Optional product ID to filter by specific product
        days: Number of days to look back (alternative to start_date/end_date)
        
    Returns:
        Dict with accuracy metrics: mae, mape, wape, bias, sample_size
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        if days:
            start_date = end_date - timedelta(days=days)
        else:
            start_date = end_date - timedelta(days=30)
    
    # Get sales service
    sales_service = get_sales_service()
    
    # Adjust dates to dataset range
    if sales_service.latest_date:
        if end_date > sales_service.latest_date:
            end_date = sales_service.latest_date
        if start_date > sales_service.latest_date:
            start_date = end_date - timedelta(days=30)
    
    # Get store
    store = db.query(Store).filter(Store.store_id == str(store_id)).first()
    if not store:
        return {
            'mae': 0.0,
            'mape': 0.0,
            'wape': 0.0,
            'bias': 0.0,
            'sample_size': 0,
            'error': 'Store not found'
        }
    
    # Get forecasts from database
    forecast_query = db.query(Forecast).filter(
        Forecast.store_id == store.id,
        Forecast.target_date >= start_date,
        Forecast.target_date <= end_date
    )
    
    if product_id:
        forecast_query = forecast_query.filter(Forecast.product_id == product_id)
    
    forecasts = forecast_query.all()
    
    if not forecasts:
        return {
            'mae': 0.0,
            'mape': 0.0,
            'wape': 0.0,
            'bias': 0.0,
            'sample_size': 0,
            'error': 'No forecasts found'
        }
    
    # Get actual sales for each forecast
    actual_sales = []
    predicted_sales = []
    
    for forecast in forecasts:
        # Get product SKU
        product = db.query(Product).filter(Product.id == forecast.product_id).first()
        if not product:
            continue
        
        # Get actual sales for this product on the target date
        sales_data = sales_service.get_store_sales(
            store_id=store_id,
            start_date=forecast.target_date,
            end_date=forecast.target_date
        )
        
        # Find sales for this specific product
        product_sales = 0.0
        for day_data in sales_data:
            # We need to get product-level sales, not store-level
            # For now, we'll use a simplified approach: divide store sales by number of products
            # In production, this should query product-specific sales
            pass
        
        # Get product-specific sales
        product_sales_stats = sales_service.get_product_sales(
            store_id=store_id,
            sku_id=product.sku_id,
            start_date=forecast.target_date,
            end_date=forecast.target_date
        )
        
        # Use items_sold_today as actual
        actual = product_sales_stats.get('items_sold_today', 0.0)
        predicted = forecast.predicted_demand
        
        if actual > 0 or predicted > 0:  # Include even if one is zero
            actual_sales.append(actual)
            predicted_sales.append(predicted)
    
    if len(actual_sales) == 0:
        return {
            'mae': 0.0,
            'mape': 0.0,
            'wape': 0.0,
            'bias': 0.0,
            'sample_size': 0,
            'error': 'No matching sales data found'
        }
    
    # Calculate metrics
    mae = calculate_mae(actual_sales, predicted_sales)
    mape = calculate_mape(actual_sales, predicted_sales)
    wape = calculate_wape(actual_sales, predicted_sales)
    bias = calculate_bias(actual_sales, predicted_sales)
    
    return {
        'mae': round(mae, 2),
        'mape': round(mape, 2),
        'wape': round(wape, 2),
        'bias': round(bias, 2),
        'sample_size': len(actual_sales),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }


def get_product_forecast_accuracy(
    db: Session,
    store_id: str,
    sku_id: str,
    days: int = 30
) -> Dict:
    """
    Get forecast accuracy for a specific product.
    
    Args:
        db: Database session
        store_id: Store identifier
        sku_id: Product SKU identifier
        days: Number of days to look back
        
    Returns:
        Dict with accuracy metrics
    """
    # Get product
    product = db.query(Product).filter(Product.sku_id == sku_id).first()
    if not product:
        return {
            'mae': 0.0,
            'mape': 0.0,
            'wape': 0.0,
            'bias': 0.0,
            'sample_size': 0,
            'error': 'Product not found'
        }
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    return calculate_forecast_accuracy(
        db=db,
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
        product_id=product.id
    )


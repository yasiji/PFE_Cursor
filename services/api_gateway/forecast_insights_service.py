"""Forecast insights service - provides forecasting summaries and insights."""

from datetime import date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from services.api_gateway.models import Store, Product, Forecast
from services.api_gateway.services import get_forecasting_service
from services.api_gateway.price_service import get_average_price_for_store
from services.api_gateway.profit_service import calculate_store_profit
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def get_forecast_insights(
    db: Session,
    store_id: str,
    horizon_days: int = 30
) -> Dict:
    """
    Get forecast insights for a store.
    
    Provides:
    - Tomorrow's forecast summary (TOTAL items for tomorrow)
    - Next week forecast (DAILY AVERAGE items)
    - Next month forecast (DAILY AVERAGE items)
    - Key insights (high/low forecasts, trends)
    
    Args:
        db: Database session
        store_id: Store identifier
        horizon_days: Number of days to forecast ahead (default: 30)
        
    Returns:
        Dict with forecast insights
    """
    # Get store
    store = db.query(Store).filter(Store.id == int(store_id)).first()
    if not store:
        store = db.query(Store).filter(Store.store_id == str(store_id)).first()
    
    if not store:
        return {
            'error': 'Store not found',
            'tomorrow': {},
            'next_week': {},
            'next_month': {},
            'insights': []
        }
    
    # Get all products for this store
    products = db.query(Product).all()
    
    if not products:
        return {
            'error': 'No products found',
            'tomorrow': {},
            'next_week': {},
            'next_month': {},
            'insights': []
        }
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # Get average price for revenue calculations
    avg_price = get_average_price_for_store(db, store_id=store_id)
    
    # Try to get forecasts from database first (much faster)
    forecasts_by_date = {}
    stored_forecasts = db.query(Forecast).filter(
        Forecast.store_id == int(store_id),
        Forecast.target_date >= tomorrow,
        Forecast.target_date <= today + timedelta(days=30)
    ).all()
    
    if stored_forecasts:
        # Aggregate forecasts by target date
        for f in stored_forecasts:
            target = f.target_date.isoformat()
            if target not in forecasts_by_date:
                forecasts_by_date[target] = 0.0
            forecasts_by_date[target] += f.predicted_demand
        
        logger.info(f"Found {len(stored_forecasts)} forecasts in database for {len(forecasts_by_date)} days")
    else:
        # Fall back to forecasting service (slower but works without stored forecasts)
        logger.info("No stored forecasts, using forecasting service")
        forecasting_service = get_forecasting_service()
        
        # Sample 10 products and scale
        sample_products = products[:10]
        scale_factor = len(products) / len(sample_products) if sample_products else 1.0
        
        for product in sample_products:
            try:
                product_forecasts = forecasting_service.forecast(
                    store_id=store_id,
                    sku_id=product.sku_id,
                    horizon_days=min(horizon_days, 30),
                    include_uncertainty=False
                )
                for f in product_forecasts:
                    target = f.get('date')
                    if target:
                        if target not in forecasts_by_date:
                            forecasts_by_date[target] = 0.0
                        forecasts_by_date[target] += f.get('predicted_demand', 0.0) * scale_factor
            except Exception as e:
                logger.warning(f"Error forecasting for {product.sku_id}: {e}")
    
    # Calculate tomorrow's forecast (TOTAL items for tomorrow)
    tomorrow_str = tomorrow.isoformat()
    tomorrow_items = int(forecasts_by_date.get(tomorrow_str, 0))
    
    # If no stored forecasts, estimate based on average
    if tomorrow_items == 0 and len(forecasts_by_date) > 0:
        tomorrow_items = int(sum(forecasts_by_date.values()) / len(forecasts_by_date))
    elif tomorrow_items == 0:
        # Fallback estimation: 10 items/day per product
        tomorrow_items = len(products) * 10
    
    tomorrow_revenue = tomorrow_items * avg_price
    tomorrow_profit_data = calculate_store_profit(
        db=db,
        store_id=store_id,
        revenue=tomorrow_revenue,
        items_sold=tomorrow_items,
        target_date=tomorrow
    )
    
    # Calculate next week forecast (days 1-7)
    next_week_total = 0.0
    next_week_days = 0
    for i in range(1, 8):
        target_date = (today + timedelta(days=i)).isoformat()
        if target_date in forecasts_by_date:
            next_week_total += forecasts_by_date[target_date]
            next_week_days += 1
    
    # If we have some days but not all, extrapolate
    if next_week_days > 0:
        next_week_daily_avg = next_week_total / next_week_days
    elif tomorrow_items > 0:
        next_week_daily_avg = tomorrow_items  # Use tomorrow as baseline
    else:
        next_week_daily_avg = len(products) * 10  # Fallback
    
    next_week_revenue_daily = next_week_daily_avg * avg_price
    next_week_profit_data = calculate_store_profit(
        db=db,
        store_id=store_id,
        revenue=next_week_revenue_daily,
        items_sold=int(next_week_daily_avg),
        target_date=today + timedelta(days=7)
    )
    
    # Calculate next month forecast (days 1-30)
    next_month_total = 0.0
    next_month_days = 0
    for i in range(1, 31):
        target_date = (today + timedelta(days=i)).isoformat()
        if target_date in forecasts_by_date:
            next_month_total += forecasts_by_date[target_date]
            next_month_days += 1
    
    # If we have some days but not all, extrapolate
    if next_month_days > 0:
        next_month_daily_avg = next_month_total / next_month_days
    elif next_week_daily_avg > 0:
        next_month_daily_avg = next_week_daily_avg  # Use week as baseline
    else:
        next_month_daily_avg = len(products) * 10  # Fallback
    
    next_month_revenue_daily = next_month_daily_avg * avg_price
    next_month_profit_data = calculate_store_profit(
        db=db,
        store_id=store_id,
        revenue=next_month_revenue_daily,
        items_sold=int(next_month_daily_avg),
        target_date=today + timedelta(days=30)
    )
    
    # Generate insights
    insights = []
    
    if tomorrow_items > 0:
        insights.append({
            'type': 'tomorrow',
            'title': f"Tomorrow's Forecast",
            'message': f"Expected {int(tomorrow_items)} items sold, generating ${tomorrow_revenue:.2f} in revenue",
            'severity': 'info'
        })
    
    # Compare daily averages
    if next_week_daily_avg > 0 and tomorrow_items > 0:
        if next_week_daily_avg > tomorrow_items * 1.1:
            insights.append({
                'type': 'trend',
                'title': 'Increasing Demand',
                'message': 'Next week shows 10%+ higher daily average demand',
                'severity': 'success'
            })
        elif next_week_daily_avg < tomorrow_items * 0.9:
            insights.append({
                'type': 'trend',
                'title': 'Decreasing Demand',
                'message': 'Next week shows 10%+ lower daily average demand',
                'severity': 'warning'
            })
    
    if tomorrow_profit_data['margin_percent'] > 50:
        insights.append({
            'type': 'profitability',
            'title': 'High Profitability',
            'message': f"Tomorrow's forecast shows {tomorrow_profit_data['margin_percent']:.1f}% margin",
            'severity': 'success'
        })
    
    return {
        'tomorrow': {
            'date': tomorrow.isoformat(),
            'forecasted_items': int(tomorrow_items),
            'forecasted_sales': round(float(tomorrow_items), 2),
            'forecasted_revenue': round(tomorrow_revenue, 2),
            'forecasted_profit': round(tomorrow_profit_data['profit'], 2),
            'forecasted_margin': round(tomorrow_profit_data['margin_percent'], 2)
        },
        'next_week': {
            'start_date': (today + timedelta(days=1)).isoformat(),
            'end_date': (today + timedelta(days=7)).isoformat(),
            'daily_avg_items': int(next_week_daily_avg),
            'daily_avg_sales': round(float(next_week_daily_avg), 2),
            'daily_avg_revenue': round(next_week_revenue_daily, 2),
            'daily_avg_profit': round(next_week_profit_data['profit'], 2),
            'daily_avg_margin': round(next_week_profit_data['margin_percent'], 2)
        },
        'next_month': {
            'start_date': (today + timedelta(days=1)).isoformat(),
            'end_date': (today + timedelta(days=30)).isoformat(),
            'daily_avg_items': int(next_month_daily_avg),
            'daily_avg_sales': round(float(next_month_daily_avg), 2),
            'daily_avg_revenue': round(next_month_revenue_daily, 2),
            'daily_avg_profit': round(next_month_profit_data['profit'], 2),
            'daily_avg_margin': round(next_month_profit_data['margin_percent'], 2)
        },
        'insights': insights
    }

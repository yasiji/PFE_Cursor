"""Top products analysis service."""

from datetime import date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from services.api_gateway.models import Product, Store
from services.api_gateway.sales_data_service import get_sales_service
from services.api_gateway.price_service import get_product_price
from services.api_gateway.profit_service import calculate_product_profit
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def get_top_products(
    db: Session,
    store_id: str,
    limit: int = 10,
    sort_by: str = "sales_volume",  # sales_volume, revenue, profit, growth
    period_days: int = 30
) -> List[Dict]:
    """
    Get top products for a store.
    
    Args:
        db: Database session
        store_id: Store identifier
        limit: Number of top products to return
        sort_by: Sort criteria (sales_volume, revenue, profit, growth)
        period_days: Number of days to analyze
        
    Returns:
        List of product dicts with sales, revenue, profit metrics
    """
    sales_service = get_sales_service()
    
    # Get store
    store = db.query(Store).filter(Store.store_id == str(store_id)).first()
    if not store:
        return []
    
    # Get effective date range
    today = date.today()
    if sales_service.latest_date and today > sales_service.latest_date:
        end_date = sales_service.latest_date
    else:
        end_date = today
    
    start_date = end_date - timedelta(days=period_days)
    
    # Get all products
    products = db.query(Product).limit(100).all()  # Limit for performance
    
    product_stats = []
    
    for product in products:
        # Get sales data
        sales_stats = sales_service.get_product_sales(
            store_id=store_id,
            sku_id=product.sku_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get price
        price = get_product_price(db, sku_id=product.sku_id)
        
        # Calculate metrics
        items_sold = sales_stats.get('items_sold_month', 0.0)
        revenue = items_sold * price
        
        # Calculate profit
        profit_data = calculate_product_profit(
            db=db,
            sku_id=product.sku_id,
            revenue=revenue,
            items_sold=items_sold,
            target_date=end_date
        )
        
        # Calculate growth (compare last 7 days vs previous 7 days)
        week_start = end_date - timedelta(days=7)
        prev_week_start = week_start - timedelta(days=7)
        
        recent_sales = sales_service.get_product_sales(
            store_id=store_id,
            sku_id=product.sku_id,
            start_date=week_start,
            end_date=end_date
        )
        
        prev_sales = sales_service.get_product_sales(
            store_id=store_id,
            sku_id=product.sku_id,
            start_date=prev_week_start,
            end_date=week_start
        )
        
        recent_items = recent_sales.get('items_sold_week', 0.0)
        prev_items = prev_sales.get('items_sold_week', 0.0)
        
        if prev_items > 0:
            growth_rate = ((recent_items - prev_items) / prev_items) * 100
        else:
            growth_rate = 100.0 if recent_items > 0 else 0.0
        
        product_stats.append({
            'sku_id': product.sku_id,
            'name': product.name or f"Product {product.sku_id}",
            'category': "General",  # Would come from category table
            'sales_volume': items_sold,
            'revenue': revenue,
            'profit': profit_data['profit'],
            'margin_percent': profit_data['margin_percent'],
            'growth_rate': growth_rate,
            'price': price
        })
    
    # Sort by criteria
    if sort_by == "sales_volume":
        product_stats.sort(key=lambda x: x['sales_volume'], reverse=True)
    elif sort_by == "revenue":
        product_stats.sort(key=lambda x: x['revenue'], reverse=True)
    elif sort_by == "profit":
        product_stats.sort(key=lambda x: x['profit'], reverse=True)
    elif sort_by == "growth":
        product_stats.sort(key=lambda x: x['growth_rate'], reverse=True)
    
    # Return top N
    return product_stats[:limit]


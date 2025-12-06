"""Profit and margin calculation service."""

from datetime import date
from typing import Optional, Dict
from sqlalchemy.orm import Session

from services.api_gateway.price_service import get_product_price, get_product_cost, get_average_price_for_store
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_profit(
    revenue: float,
    cost: float
) -> float:
    """
    Calculate profit (revenue - cost).
    
    Args:
        revenue: Total revenue
        cost: Total cost
        
    Returns:
        Profit amount
    """
    return max(0.0, revenue - cost)


def calculate_margin_percent(
    revenue: float,
    cost: float
) -> float:
    """
    Calculate profit margin percentage.
    
    Args:
        revenue: Total revenue
        cost: Total cost
        
    Returns:
        Margin percentage (0-100)
    """
    if revenue == 0:
        return 0.0
    return ((revenue - cost) / revenue) * 100.0


def calculate_store_profit(
    db: Session,
    store_id: str,
    revenue: float,
    items_sold: float,
    target_date: Optional[date] = None
) -> Dict[str, float]:
    """
    Calculate profit and margin for a store based on revenue and items sold.
    
    Args:
        db: Database session
        store_id: Store identifier
        revenue: Total revenue
        items_sold: Total items sold
        target_date: Date to calculate profit for (defaults to today)
        
    Returns:
        Dict with keys: profit, cost, margin_percent
    """
    if target_date is None:
        target_date = date.today()
    
    # Get average cost for the store
    # For now, we'll estimate cost as 50% of average price
    avg_price = get_average_price_for_store(db, store_id=store_id, target_date=target_date)
    avg_cost = avg_price * 0.5  # Estimate: cost is 50% of price
    
    # Calculate total cost
    total_cost = items_sold * avg_cost
    
    # Calculate profit
    profit = calculate_profit(revenue, total_cost)
    
    # Calculate margin
    margin_percent = calculate_margin_percent(revenue, total_cost)
    
    return {
        'profit': profit,
        'cost': total_cost,
        'margin_percent': margin_percent
    }


def calculate_product_profit(
    db: Session,
    product_id: Optional[int] = None,
    sku_id: Optional[str] = None,
    revenue: float = 0.0,
    items_sold: float = 0.0,
    target_date: Optional[date] = None
) -> Dict[str, float]:
    """
    Calculate profit and margin for a specific product.
    
    Args:
        db: Database session
        product_id: Product ID (internal)
        sku_id: SKU ID (external identifier)
        revenue: Revenue for this product
        items_sold: Items sold for this product
        target_date: Date to calculate profit for (defaults to today)
        
    Returns:
        Dict with keys: profit, cost, margin_percent
    """
    if target_date is None:
        target_date = date.today()
    
    # Get product price and cost
    price = get_product_price(db, product_id=product_id, sku_id=sku_id, target_date=target_date)
    cost = get_product_cost(db, product_id=product_id, sku_id=sku_id, target_date=target_date)
    
    # If no cost in database, estimate as 50% of price
    if cost == 0.0:
        cost = price * 0.5
    
    # Calculate total cost
    total_cost = items_sold * cost
    
    # Calculate profit
    profit = calculate_profit(revenue, total_cost)
    
    # Calculate margin
    margin_percent = calculate_margin_percent(revenue, total_cost)
    
    return {
        'profit': profit,
        'cost': total_cost,
        'margin_percent': margin_percent,
        'price': price,
        'cost_per_unit': cost
    }


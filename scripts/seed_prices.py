"""Seed initial product prices and costs from dataset or defaults."""

import sys
import random
import hashlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date
from sqlalchemy.orm import Session

from services.api_gateway.database import SessionLocal, init_db
from services.api_gateway.models import Product, ProductPrice, ProductCost
from shared.logging_setup import get_logger

logger = get_logger(__name__)

# Realistic price ranges by category type (fresh retail)
CATEGORY_PRICE_RANGES = {
    # Category ID -> (min_price, max_price, margin_percent)
    0: (1.99, 4.99, 0.45),    # General fresh
    3: (2.49, 6.99, 0.40),    # Premium fresh
    4: (0.99, 3.49, 0.50),    # Basic produce
    5: (1.49, 4.49, 0.45),    # Dairy
    7: (2.99, 7.99, 0.35),    # Prepared foods
    8: (1.29, 3.99, 0.48),    # Bakery
    10: (3.49, 9.99, 0.38),   # Meat/Deli
    11: (0.79, 2.49, 0.55),   # Budget items
    'default': (1.99, 5.99, 0.45)  # Default range
}


def _get_product_price_for_sku(sku_id: str, category_id: int = None) -> tuple:
    """
    Generate a consistent but varied price for a product.
    
    Uses hash of SKU to ensure same SKU always gets same price,
    but different SKUs get different prices.
    """
    # Get price range for category
    price_range = CATEGORY_PRICE_RANGES.get(category_id, CATEGORY_PRICE_RANGES['default'])
    min_price, max_price, margin = price_range
    
    # Use hash of SKU to generate consistent random-looking price
    hash_val = int(hashlib.md5(str(sku_id).encode()).hexdigest()[:8], 16)
    random.seed(hash_val)
    
    # Generate price within range (round to .49 or .99 endings for realism)
    base_price = min_price + (max_price - min_price) * random.random()
    
    # Round to realistic price endings
    price_int = int(base_price)
    decimal = base_price - price_int
    if decimal < 0.25:
        final_price = price_int + 0.29
    elif decimal < 0.50:
        final_price = price_int + 0.49
    elif decimal < 0.75:
        final_price = price_int + 0.79
    else:
        final_price = price_int + 0.99
    
    # Calculate cost based on margin
    cost = final_price * (1 - margin)
    
    # Reset random seed
    random.seed()
    
    return round(final_price, 2), round(cost, 2)


def seed_prices(db: Session, default_price: float = 2.99, default_cost: float = 1.50):
    """
    Seed initial prices and costs for all products with VARIED realistic prices.
    
    Args:
        db: Database session
        default_price: Default price per unit (fallback)
        default_cost: Default cost per unit (fallback)
    """
    products = db.query(Product).all()
    
    if not products:
        logger.warning("No products found in database. Run seed_test_data.py first.")
        return
    
    today = date.today()
    prices_created = 0
    costs_created = 0
    
    for product in products:
        # Generate varied price based on SKU and category
        category_id = product.category_id if product.category_id else 0
        product_price, product_cost = _get_product_price_for_sku(product.sku_id, category_id)
        
        # Check if product already has a current price
        existing_price = db.query(ProductPrice).filter(
            ProductPrice.product_id == product.id,
            ProductPrice.end_date.is_(None)
        ).first()
        
        if existing_price:
            # Update existing price to varied price
            existing_price.price = product_price
        else:
            # Create new price
            price = ProductPrice(
                product_id=product.id,
                price=product_price,
                effective_date=today,
                end_date=None  # Current price
            )
            db.add(price)
            prices_created += 1
        
        # Check if product already has a current cost
        existing_cost = db.query(ProductCost).filter(
            ProductCost.product_id == product.id,
            ProductCost.end_date.is_(None)
        ).first()
        
        if existing_cost:
            # Update existing cost
            existing_cost.cost_per_unit = product_cost
        else:
            # Create new cost
            cost = ProductCost(
                product_id=product.id,
                cost_per_unit=product_cost,
                effective_date=today,
                end_date=None  # Current cost
            )
            db.add(cost)
            costs_created += 1
    
    db.commit()
    logger.info(f"Created/updated {prices_created} prices and {costs_created} costs for {len(products)} products")
    
    # Log some sample prices for verification
    sample_products = products[:5]
    for p in sample_products:
        price, cost = _get_product_price_for_sku(p.sku_id, p.category_id)
        logger.info(f"  SKU {p.sku_id}: ${price:.2f} (cost: ${cost:.2f})")


def seed_category_prices(db: Session):
    """
    Seed prices based on product categories (if category information is available).
    This is a placeholder for more sophisticated pricing logic.
    """
    # TODO: Implement category-based pricing if category data is available
    # For now, use default pricing
    pass


def main():
    """Main function to seed prices."""
    logger.info("Starting price seeding...")
    
    # Initialize database
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Seed default prices and costs
        seed_prices(db, default_price=2.99, default_cost=1.50)
        
        logger.info("Price seeding completed successfully!")
    except Exception as e:
        logger.error(f"Error seeding prices: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()


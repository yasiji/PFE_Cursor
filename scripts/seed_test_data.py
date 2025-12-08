"""
Seed test data for development and testing.

This script populates the database with data derived from FreshRetailNet-50K:
- Users (for authentication)
- Store (mapped from FreshRetailNet store)
- Products (from FreshRetailNet with category mappings)
- Inventory snapshots (generated from sales patterns)
- Forecasts (based on demand patterns)
- Recommendations (based on inventory state)
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from services.api_gateway.database import get_db, init_db, SessionLocal
from services.api_gateway.models import (
    Store, Product, InventorySnapshot, Forecast, Recommendation, User
)
from services.api_gateway.auth import get_password_hash
from shared.logging_setup import get_logger
from shared.category_shelf_life import get_category_name, get_shelf_life

logger = get_logger(__name__)

# Import the new inventory generator
from scripts.generate_inventory_from_sales import InventoryGenerator


# Store configuration - Store 235 is in FreshRetailNet dataset
STORE_CONFIG = {
    "id": 235,
    "name": "Fresh Market Store 235",
    "freshretail_store_id": 235  # Maps to actual FreshRetailNet store
}


def create_test_users(db: Session):
    """Create test users if they don't exist."""
    users_created = 0
    
    # Test user (store manager)
    if not db.query(User).filter(User.username == "test_user").first():
        user = User(
            username="test_user",
            email="test@example.com",
            hashed_password=get_password_hash("test123"),
            role="store_manager",
            store_id=235,
            is_active=True
        )
        db.add(user)
        users_created += 1
        print(f"  Created user: test_user (password: test123)")
    
    # Admin user
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            store_id=235,
            is_active=True
        )
        db.add(admin)
        users_created += 1
        print(f"  Created user: admin (password: admin123)")
    
    db.commit()
    return users_created


def seed_store(db: Session):
    """Seed the store."""
    if not db.query(Store).filter(Store.id == STORE_CONFIG["id"]).first():
        store = Store(
            id=STORE_CONFIG["id"],
            store_id=str(STORE_CONFIG["id"]),
            name=STORE_CONFIG["name"]
        )
        db.add(store)
        db.commit()
        print(f"  Created store: {store.name} (ID: {store.id})")
        return 1
    return 0


def seed_products_from_freshretail(db: Session, inventory_generator: InventoryGenerator, store_id: int = 235):
    """Seed products from FreshRetailNet-50K dataset."""
    products_created = 0
    products_updated = 0
    
    # Get products that have sales in the dataset for this store
    freshretail_products = inventory_generator.get_products_for_store(
        store_id=store_id,
        limit=50  # Top 50 products by sales volume
    )
    
    for prod_info in freshretail_products:
        sku_id = prod_info['sku_id']
        existing = db.query(Product).filter(Product.sku_id == sku_id).first()
        
        if existing:
            # Update existing product
            existing.category = prod_info['category_name']
            existing.category_id = prod_info['category_id']
            existing.shelf_life_days = prod_info['shelf_life_days']
            products_updated += 1
        else:
            # Create new product
            product = Product(
                sku_id=sku_id,
                name=f"{prod_info['category_name']} #{sku_id}",
                category=prod_info['category_name'],
                category_id=prod_info['category_id'],
                shelf_life_days=prod_info['shelf_life_days'],
                transit_days=1 if prod_info['shelf_life_days'] <= 3 else 2,
                case_pack_size=random.randint(6, 24),
                min_order_quantity=1,
                max_order_quantity=500
            )
            db.add(product)
            products_created += 1
    
    db.commit()
    print(f"  Created {products_created} products, updated {products_updated}")
    return products_created + products_updated


def seed_inventory_from_sales(db: Session, inventory_generator: InventoryGenerator, store_id: int = 235):
    """Seed inventory derived from FreshRetailNet sales patterns."""
    today = date.today()
    inventory_created = 0
    
    # Delete existing inventory for today
    db.query(InventorySnapshot).filter(
        InventorySnapshot.store_id == store_id,
        InventorySnapshot.snapshot_date == today
    ).delete()
    db.commit()
    
    # Generate inventory from sales data
    inventory_items = inventory_generator.generate_store_inventory(
        store_id=store_id,
        max_products=50,
        reference_date=today
    )
    
    # Get product ID mapping (sku_id -> db product.id)
    products = db.query(Product).all()
    product_id_map = {p.sku_id: p.id for p in products}
    
    for item in inventory_items:
        db_product_id = product_id_map.get(item['sku_id'])
        if not db_product_id:
            continue
        
        inventory = InventorySnapshot(
            store_id=store_id,
            product_id=db_product_id,
            snapshot_date=item['snapshot_date'],
            quantity=item['quantity'],
            shelf_quantity=item['shelf_quantity'],
            backroom_quantity=item['backroom_quantity'],
            expiry_date=item['expiry_date'],
            days_until_expiry=item['days_until_expiry'],
            expiry_buckets=item['expiry_buckets'],
            in_transit=item['in_transit'],
            to_discard=item['to_discard'],
            sold_today=item['sold_today']
        )
        db.add(inventory)
        inventory_created += 1
    
    db.commit()
    print(f"  Created {inventory_created} inventory records from sales data")
    return inventory_created


def seed_forecasts(db: Session, inventory_generator: InventoryGenerator, store_id: int = 235):
    """Seed forecasts based on actual demand patterns."""
    today = date.today()
    forecasts_created = 0
    
    # Delete old forecasts for today
    db.query(Forecast).filter(
        Forecast.store_id == store_id,
        Forecast.forecast_date == today
    ).delete()
    db.commit()
    
    # Get products with their demand data
    products = db.query(Product).all()
    
    for product in products:
        # Calculate actual average demand from sales data
        avg_demand = inventory_generator.calculate_daily_demand(
            store_id=store_id,
            product_id=int(product.sku_id) if product.sku_id.isdigit() else 0
        )
        
        if avg_demand <= 0:
            # Use fallback for products not in dataset
            avg_demand = random.uniform(10, 30)
        
        # Create forecasts for next 30 days
        for day_offset in range(1, 31):
            target_date = today + timedelta(days=day_offset)
            
            # Apply day-of-week variation based on patterns
            dow = target_date.weekday()
            if dow == 5:  # Saturday
                demand = avg_demand * 1.30
            elif dow == 6:  # Sunday
                demand = avg_demand * 1.15
            elif dow == 4:  # Friday
                demand = avg_demand * 1.10
            elif dow == 0:  # Monday
                demand = avg_demand * 0.85
            else:
                demand = avg_demand * random.uniform(0.95, 1.05)
            
            # Add small random variation
            demand = demand * random.uniform(0.92, 1.08)
            
            forecast = Forecast(
                store_id=store_id,
                product_id=product.id,
                forecast_date=today,
                target_date=target_date,
                predicted_demand=round(demand, 2),
                lower_bound=round(demand * 0.85, 2),
                upper_bound=round(demand * 1.15, 2),
                model_type="lightgbm",
                confidence_level=0.95
            )
            db.add(forecast)
            forecasts_created += 1
    
    db.commit()
    print(f"  Created {forecasts_created} forecasts (30 days x {len(products)} products)")
    return forecasts_created


def seed_recommendations(db: Session, store_id: int = 235):
    """Seed order recommendations based on current inventory state."""
    today = date.today()
    recs_created = 0
    markdown_recs = 0
    
    # Delete existing recommendations for today
    db.query(Recommendation).filter(
        Recommendation.store_id == store_id,
        Recommendation.recommendation_date == today
    ).delete()
    db.commit()
    
    # Get inventory with products
    inventory_items = db.query(InventorySnapshot).filter(
        InventorySnapshot.store_id == store_id,
        InventorySnapshot.snapshot_date == today
    ).all()
    
    for inv in inventory_items:
        product = db.query(Product).filter(Product.id == inv.product_id).first()
        if not product:
            continue
        
        # Calculate if we need to reorder
        backroom_qty = inv.backroom_quantity or 0
        shelf_qty = inv.shelf_quantity or 0
        days_until_exp = inv.days_until_expiry or 30
        forecasted_demand = (shelf_qty + backroom_qty) * 0.25  # Estimate
        
        # ORDER recommendation if backroom is low
        if backroom_qty < forecasted_demand * 3:
            order_qty = max(30, int(forecasted_demand * 7))
            recommendation = Recommendation(
                store_id=store_id,
                product_id=product.id,
                recommendation_date=today,
                order_quantity=float(order_qty),
                status="pending"
            )
            db.add(recommendation)
            recs_created += 1
        
        # MARKDOWN recommendation if expiring soon
        if days_until_exp <= 3 and inv.quantity > 0:
            if days_until_exp <= 1:
                discount = 50.0
            elif days_until_exp <= 2:
                discount = 35.0
            else:
                discount = 25.0
            
            markdown_rec = Recommendation(
                store_id=store_id,
                product_id=product.id,
                recommendation_date=today,
                order_quantity=0.0,
                markdown_discount_percent=discount,
                markdown_effective_date=today,
                markdown_reason=f"Expiring in {days_until_exp} day(s) - reduce price to clear stock",
                status="pending"
            )
            db.add(markdown_rec)
            markdown_recs += 1
    
    db.commit()
    print(f"  Created {recs_created} order recommendations")
    print(f"  Created {markdown_recs} markdown recommendations")
    return recs_created + markdown_recs


def main():
    """Main seeding function."""
    print("\n" + "="*60)
    print("  Database Seeding - Fresh Product Replenishment Manager")
    print("  Using FreshRetailNet-50K Sales Data")
    print("="*60 + "\n")
    
    # Initialize database
    try:
        init_db()
        print("[OK] Database initialized\n")
    except Exception as e:
        print(f"[WARN] Database init: {e}\n")
    
    # Initialize inventory generator (loads FreshRetailNet data)
    print("[0/6] Loading FreshRetailNet-50K dataset...")
    try:
        inventory_generator = InventoryGenerator()
        print("[OK] Dataset loaded\n")
    except Exception as e:
        print(f"[ERROR] Failed to load dataset: {e}")
        return
    
    db = SessionLocal()
    
    try:
        print("[1/6] Creating users...")
        create_test_users(db)
        
        print("\n[2/6] Creating store...")
        seed_store(db)
        
        print("\n[3/6] Creating products from FreshRetailNet...")
        seed_products_from_freshretail(db, inventory_generator, store_id=235)
        
        print("\n[4/6] Creating inventory from sales patterns...")
        seed_inventory_from_sales(db, inventory_generator, store_id=235)
        
        print("\n[5/6] Creating forecasts from demand data...")
        seed_forecasts(db, inventory_generator, store_id=235)
        
        print("\n[6/6] Creating recommendations...")
        seed_recommendations(db, store_id=235)
        
        print("\n" + "="*60)
        print("  Seeding Complete!")
        print("="*60)
        print("\nLogin credentials:")
        print("  - test_user / test123 (Store Manager)")
        print("  - admin / admin123 (Admin)")
        print("\nData source: FreshRetailNet-50K")
        print("  - Products derived from actual sales data")
        print("  - Inventory quantities based on demand patterns")
        print("  - Expiry dates consistent with buckets")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

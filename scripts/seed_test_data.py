"""
Seed test data for development and testing.

This script populates the database with realistic sample data including:
- Products with proper categories
- Inventory snapshots with expiry dates
- Sales data
- Forecasts
- Recommendations
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

logger = get_logger(__name__)

# Category mapping
CATEGORIES = {
    "Fruits": {"id": 1, "products": [
        {"sku_id": "FRU-001", "name": "Fresh Apples", "shelf_life_days": 14, "base_price": 1.99},
        {"sku_id": "FRU-002", "name": "Bananas", "shelf_life_days": 7, "base_price": 0.69},
        {"sku_id": "FRU-003", "name": "Oranges", "shelf_life_days": 21, "base_price": 1.49},
        {"sku_id": "FRU-004", "name": "Strawberries", "shelf_life_days": 5, "base_price": 4.99},
        {"sku_id": "FRU-005", "name": "Grapes", "shelf_life_days": 10, "base_price": 3.49},
        {"sku_id": "FRU-006", "name": "Watermelon", "shelf_life_days": 14, "base_price": 5.99},
    ]},
    "Vegetables": {"id": 2, "products": [
        {"sku_id": "VEG-001", "name": "Fresh Tomatoes", "shelf_life_days": 7, "base_price": 2.49},
        {"sku_id": "VEG-002", "name": "Lettuce", "shelf_life_days": 5, "base_price": 1.99},
        {"sku_id": "VEG-003", "name": "Carrots", "shelf_life_days": 21, "base_price": 1.49},
        {"sku_id": "VEG-004", "name": "Broccoli", "shelf_life_days": 7, "base_price": 2.99},
        {"sku_id": "VEG-005", "name": "Cucumbers", "shelf_life_days": 10, "base_price": 0.99},
        {"sku_id": "VEG-006", "name": "Bell Peppers", "shelf_life_days": 10, "base_price": 1.29},
    ]},
    "Dairy": {"id": 3, "products": [
        {"sku_id": "DAI-001", "name": "Organic Milk", "shelf_life_days": 10, "base_price": 4.99},
        {"sku_id": "DAI-002", "name": "Greek Yogurt", "shelf_life_days": 21, "base_price": 5.49},
        {"sku_id": "DAI-003", "name": "Cheddar Cheese", "shelf_life_days": 60, "base_price": 6.99},
        {"sku_id": "DAI-004", "name": "Butter", "shelf_life_days": 90, "base_price": 4.49},
        {"sku_id": "DAI-005", "name": "Heavy Cream", "shelf_life_days": 14, "base_price": 3.99},
    ]},
    "Bakery": {"id": 4, "products": [
        {"sku_id": "BAK-001", "name": "Whole Wheat Bread", "shelf_life_days": 5, "base_price": 3.49},
        {"sku_id": "BAK-002", "name": "Bagels (6pk)", "shelf_life_days": 4, "base_price": 4.99},
        {"sku_id": "BAK-003", "name": "Croissants (4pk)", "shelf_life_days": 3, "base_price": 5.99},
        {"sku_id": "BAK-004", "name": "Sourdough Loaf", "shelf_life_days": 5, "base_price": 4.49},
        {"sku_id": "BAK-005", "name": "Blueberry Muffins", "shelf_life_days": 4, "base_price": 5.49},
    ]},
    "Meat": {"id": 5, "products": [
        {"sku_id": "MEA-001", "name": "Ground Beef", "shelf_life_days": 3, "base_price": 7.99},
        {"sku_id": "MEA-002", "name": "Chicken Breast", "shelf_life_days": 4, "base_price": 8.99},
        {"sku_id": "MEA-003", "name": "Salmon Fillet", "shelf_life_days": 2, "base_price": 12.99},
        {"sku_id": "MEA-004", "name": "Turkey Deli Slices", "shelf_life_days": 7, "base_price": 6.49},
    ]},
    "Prepared Foods": {"id": 6, "products": [
        {"sku_id": "PRE-001", "name": "Rotisserie Chicken", "shelf_life_days": 3, "base_price": 8.99},
        {"sku_id": "PRE-002", "name": "Caesar Salad Kit", "shelf_life_days": 5, "base_price": 6.99},
        {"sku_id": "PRE-003", "name": "Fresh Sushi Pack", "shelf_life_days": 1, "base_price": 9.99},
        {"sku_id": "PRE-004", "name": "Hummus", "shelf_life_days": 10, "base_price": 4.49},
    ]},
}

# Sample stores
SAMPLE_STORES = [
    {"id": 235, "name": "Downtown NYC", "city": "New York"},
    {"id": 236, "name": "LA Mall", "city": "Los Angeles"},
    {"id": 237, "name": "Chicago Central", "city": "Chicago"},
]


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


def seed_stores(db: Session):
    """Seed stores."""
    stores_created = 0
    for store_data in SAMPLE_STORES:
        if not db.query(Store).filter(Store.id == store_data["id"]).first():
            store = Store(
                id=store_data["id"],
                store_id=str(store_data["id"]),
                name=store_data["name"]
            )
            db.add(store)
            stores_created += 1
            print(f"  Created store: {store.name} (ID: {store.id})")
    db.commit()
    return stores_created


def seed_products(db: Session):
    """Seed products with proper categories."""
    products_created = 0
    
    for category_name, category_data in CATEGORIES.items():
        for prod in category_data["products"]:
            existing = db.query(Product).filter(Product.sku_id == prod["sku_id"]).first()
            
            if existing:
                # Update existing product with category
                existing.category = category_name
                existing.category_id = category_data["id"]
                existing.name = prod["name"]
                existing.shelf_life_days = prod["shelf_life_days"]
            else:
                product = Product(
                    sku_id=prod["sku_id"],
                    name=prod["name"],
                    category=category_name,
                    category_id=category_data["id"],
                    shelf_life_days=prod["shelf_life_days"],
                    transit_days=1 if prod["shelf_life_days"] <= 3 else 2,
                    case_pack_size=random.randint(6, 24),
                    min_order_quantity=1,
                    max_order_quantity=500
                )
                db.add(product)
                products_created += 1
                print(f"  Created: {prod['name']} ({category_name})")
    
    db.commit()
    return products_created


def seed_inventory(db: Session, store_id: int = 235):
    """Seed inventory with proper expiry dates and realistic values."""
    today = date.today()
    products = db.query(Product).all()
    inventory_created = 0
    
    for product in products:
        # Delete existing inventory for today (to refresh)
        db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == store_id,
            InventorySnapshot.product_id == product.id,
            InventorySnapshot.snapshot_date == today
        ).delete()
        
        # Generate realistic inventory
        shelf_life = product.shelf_life_days or 7
        
        # Base quantity varies by category
        if product.category == "Meat":
            base_qty = random.randint(20, 60)
        elif product.category == "Prepared Foods":
            base_qty = random.randint(15, 40)
        elif product.category == "Bakery":
            base_qty = random.randint(30, 80)
        else:
            base_qty = random.randint(50, 150)
        
        quantity = float(base_qty)
        
        # Shelf/backroom split (60-75% on shelf)
        shelf_ratio = random.uniform(0.60, 0.75)
        shelf_quantity = round(quantity * shelf_ratio, 0)
        backroom_quantity = round(quantity - shelf_quantity, 0)
        
        # Calculate expiry date based on shelf life
        # Some items have varying ages - not all fresh today
        avg_age = random.randint(1, max(1, shelf_life // 2))
        expiry_date = today + timedelta(days=shelf_life - avg_age)
        days_until_expiry = (expiry_date - today).days
        
        # Expiry buckets - distributed realistically
        exp_1_3 = int(quantity * random.uniform(0.05, 0.20)) if days_until_expiry <= 5 else int(quantity * random.uniform(0.02, 0.10))
        exp_4_7 = int(quantity * random.uniform(0.15, 0.30))
        exp_8_plus = int(quantity - exp_1_3 - exp_4_7)
        
        expiry_buckets = {
            "1_3": max(0, exp_1_3),
            "4_7": max(0, exp_4_7),
            "8_plus": max(0, exp_8_plus)
        }
        
        # In transit (some items being delivered)
        in_transit = random.randint(0, 20) if random.random() > 0.7 else 0
        
        # To discard (expired items)
        to_discard = random.randint(0, 5) if days_until_expiry <= 2 else 0
        
        # Sold today (realistic daily sales)
        sold_today = random.randint(5, 35)
        
        inventory = InventorySnapshot(
            store_id=store_id,
            product_id=product.id,
            snapshot_date=today,
            quantity=quantity,
            shelf_quantity=shelf_quantity,
            backroom_quantity=backroom_quantity,
            expiry_date=expiry_date,
            days_until_expiry=days_until_expiry,
            expiry_buckets=expiry_buckets,
            in_transit=float(in_transit),
            to_discard=float(to_discard),
            sold_today=float(sold_today)
        )
        db.add(inventory)
        inventory_created += 1
    
    db.commit()
    print(f"  Created {inventory_created} inventory records with expiry dates")
    return inventory_created


def seed_forecasts(db: Session, store_id: int = 235):
    """Seed forecasts for all products for the next 30 days."""
    today = date.today()
    products = db.query(Product).all()
    forecasts_created = 0
    
    # Delete old forecasts
    db.query(Forecast).filter(
        Forecast.store_id == store_id,
        Forecast.forecast_date == today
    ).delete()
    
    for product in products:
        # Base demand varies by category and product
        if product.category == "Fruits":
            base_demand = random.uniform(25, 45)
        elif product.category == "Vegetables":
            base_demand = random.uniform(20, 40)
        elif product.category == "Dairy":
            base_demand = random.uniform(15, 35)
        elif product.category == "Bakery":
            base_demand = random.uniform(30, 60)
        elif product.category == "Meat":
            base_demand = random.uniform(10, 25)
        else:
            base_demand = random.uniform(15, 30)
        
        # Create forecasts for next 30 days
        for day_offset in range(1, 31):
            target_date = today + timedelta(days=day_offset)
            
            # Apply day-of-week variation
            dow = target_date.weekday()
            if dow == 5:  # Saturday
                demand = base_demand * 1.30
            elif dow == 6:  # Sunday
                demand = base_demand * 1.15
            elif dow == 4:  # Friday
                demand = base_demand * 1.10
            elif dow == 0:  # Monday
                demand = base_demand * 0.85
            else:
                demand = base_demand * random.uniform(0.95, 1.05)
            
            # Add some randomness
            demand = demand * random.uniform(0.90, 1.10)
            
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
    """Seed order recommendations based on actual inventory needs."""
    today = date.today()
    products = db.query(Product).all()
    recs_created = 0
    markdown_recs = 0
    
    # Delete existing recommendations for today
    db.query(Recommendation).filter(
        Recommendation.store_id == store_id,
        Recommendation.recommendation_date == today
    ).delete()
    
    # Create recommendations for products that need action
    for product in products:
        inv = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == store_id,
            InventorySnapshot.product_id == product.id,
            InventorySnapshot.snapshot_date == today
        ).first()
        
        if not inv:
            continue
        
        # Calculate if we need to reorder based on backroom stock
        backroom_qty = inv.backroom_quantity or 0
        shelf_qty = inv.shelf_quantity or 0
        days_until_exp = inv.days_until_expiry or 30
        forecasted_demand = (shelf_qty + backroom_qty) * 0.25  # Estimate 25% daily turnover
        
        # Create ORDER recommendation if backroom is low
        if backroom_qty < forecasted_demand * 3:  # Less than 3 days of stock in backroom
            order_qty = max(30, int(forecasted_demand * 7))  # Order a week's worth
            recommendation = Recommendation(
                store_id=store_id,
                product_id=product.id,
                recommendation_date=today,
                order_quantity=float(order_qty),
                status="pending"
            )
            db.add(recommendation)
            recs_created += 1
        
        # Create MARKDOWN recommendation if expiring soon
        if days_until_exp <= 3 and inv.quantity > 0:
            # Calculate markdown discount based on days to expiry
            if days_until_exp <= 1:
                discount = 50.0  # 50% off for items expiring today/tomorrow
            elif days_until_exp <= 2:
                discount = 35.0  # 35% off
            else:
                discount = 25.0  # 25% off
            
            markdown_rec = Recommendation(
                store_id=store_id,
                product_id=product.id,
                recommendation_date=today,
                order_quantity=0.0,  # Not an order
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
    print("="*60 + "\n")
    
    # Initialize database
    try:
        init_db()
        print("[OK] Database initialized\n")
    except Exception as e:
        print(f"[WARN] Database init: {e}\n")
    
    db = SessionLocal()
    
    try:
        print("[1/6] Creating users...")
        create_test_users(db)
        
        print("\n[2/6] Creating stores...")
        seed_stores(db)
        
        print("\n[3/6] Creating products with categories...")
        seed_products(db)
        
        print("\n[4/6] Creating inventory with expiry dates...")
        seed_inventory(db, store_id=235)
        
        print("\n[5/6] Creating 30-day forecasts...")
        seed_forecasts(db, store_id=235)
        
        print("\n[6/6] Creating recommendations...")
        seed_recommendations(db, store_id=235)
        
        print("\n" + "="*60)
        print("  Seeding Complete!")
        print("="*60)
        print("\nLogin credentials:")
        print("  - test_user / test123 (Store Manager)")
        print("  - admin / admin123 (Admin)")
        print("\nData created:")
        print(f"  - {sum(len(c['products']) for c in CATEGORIES.values())} products across {len(CATEGORIES)} categories")
        print("  - Inventory with proper expiry dates")
        print("  - 30-day forecasts for all products")
        print("  - Order recommendations for low-stock items")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

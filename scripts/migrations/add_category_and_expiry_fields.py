"""
Migration: Add category string field and expiry date fields.

This migration adds:
- Product.category (string)
- Product.subcategory (string) 
- InventorySnapshot.expiry_date
- InventorySnapshot.days_until_expiry
- InventorySnapshot.in_transit
- InventorySnapshot.to_discard
- InventorySnapshot.sold_today
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from services.api_gateway.database import engine
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def run_migration():
    """Run the migration."""
    with engine.connect() as conn:
        # Add category column to products
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR"))
            conn.commit()
            print("[OK] Added products.category column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] products.category already exists")
            else:
                print(f"[WARN] products.category: {e}")
        
        # Add subcategory column to products
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN subcategory VARCHAR"))
            conn.commit()
            print("[OK] Added products.subcategory column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] products.subcategory already exists")
            else:
                print(f"[WARN] products.subcategory: {e}")
        
        # Add expiry_date to inventory_snapshots
        try:
            conn.execute(text("ALTER TABLE inventory_snapshots ADD COLUMN expiry_date DATE"))
            conn.commit()
            print("[OK] Added inventory_snapshots.expiry_date column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] inventory_snapshots.expiry_date already exists")
            else:
                print(f"[WARN] inventory_snapshots.expiry_date: {e}")
        
        # Add days_until_expiry to inventory_snapshots
        try:
            conn.execute(text("ALTER TABLE inventory_snapshots ADD COLUMN days_until_expiry INTEGER"))
            conn.commit()
            print("[OK] Added inventory_snapshots.days_until_expiry column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] inventory_snapshots.days_until_expiry already exists")
            else:
                print(f"[WARN] inventory_snapshots.days_until_expiry: {e}")
        
        # Add in_transit to inventory_snapshots
        try:
            conn.execute(text("ALTER TABLE inventory_snapshots ADD COLUMN in_transit FLOAT DEFAULT 0"))
            conn.commit()
            print("[OK] Added inventory_snapshots.in_transit column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] inventory_snapshots.in_transit already exists")
            else:
                print(f"[WARN] inventory_snapshots.in_transit: {e}")
        
        # Add to_discard to inventory_snapshots
        try:
            conn.execute(text("ALTER TABLE inventory_snapshots ADD COLUMN to_discard FLOAT DEFAULT 0"))
            conn.commit()
            print("[OK] Added inventory_snapshots.to_discard column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] inventory_snapshots.to_discard already exists")
            else:
                print(f"[WARN] inventory_snapshots.to_discard: {e}")
        
        # Add sold_today to inventory_snapshots
        try:
            conn.execute(text("ALTER TABLE inventory_snapshots ADD COLUMN sold_today FLOAT DEFAULT 0"))
            conn.commit()
            print("[OK] Added inventory_snapshots.sold_today column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[SKIP] inventory_snapshots.sold_today already exists")
            else:
                print(f"[WARN] inventory_snapshots.sold_today: {e}")
    
    print("\n[DONE] Migration complete!")


if __name__ == "__main__":
    run_migration()


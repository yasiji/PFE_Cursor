"""Migration script to add transit_days to products and create orders table.

This migration adds:
1. transit_days column to products table
2. orders table for tracking replenishment orders

Run this script after updating the models to migrate existing data.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from shared.config import get_config
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def migrate_database():
    """Add transit_days column and create orders table."""
    config = get_config()
    database_url = config.database.url
    
    logger.info(f"Starting migration: Adding transit_days and orders table")
    logger.info(f"Database URL: {database_url}")
    
    # Create engine
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            # Check if columns already exist
            if "sqlite" in database_url:
                # SQLite syntax
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='products'
                """))
                if not result.fetchone():
                    logger.error("Table 'products' does not exist. Run init_database.py first.")
                    return False
                
                # Check if transit_days column exists
                result = conn.execute(text("PRAGMA table_info(products)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'transit_days' not in columns:
                    logger.info("Adding transit_days column to products...")
                    conn.execute(text("""
                        ALTER TABLE products 
                        ADD COLUMN transit_days INTEGER DEFAULT 1
                    """))
                    conn.commit()
                    logger.info("transit_days column added successfully")
                else:
                    logger.info("transit_days column already exists")
                
                # Check if orders table exists
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='orders'
                """))
                if not result.fetchone():
                    logger.info("Creating orders table...")
                    conn.execute(text("""
                        CREATE TABLE orders (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            store_id INTEGER NOT NULL,
                            product_id INTEGER NOT NULL,
                            order_quantity REAL NOT NULL,
                            order_date DATE NOT NULL,
                            expected_arrival_date DATE,
                            actual_arrival_date DATE,
                            status VARCHAR(50) DEFAULT 'pending',
                            transit_days INTEGER,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (store_id) REFERENCES stores(id),
                            FOREIGN KEY (product_id) REFERENCES products(id)
                        )
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_store_id ON orders(store_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_product_id ON orders(product_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_order_date ON orders(order_date)
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_expected_arrival ON orders(expected_arrival_date)
                    """))
                    conn.commit()
                    logger.info("orders table created successfully")
                else:
                    logger.info("orders table already exists")
            else:
                # PostgreSQL syntax
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='products' 
                    AND column_name='transit_days'
                """))
                if not result.fetchone():
                    logger.info("Adding transit_days column to products...")
                    conn.execute(text("""
                        ALTER TABLE products 
                        ADD COLUMN transit_days INTEGER DEFAULT 1
                    """))
                    conn.commit()
                    logger.info("transit_days column added successfully")
                else:
                    logger.info("transit_days column already exists")
                
                # Check if orders table exists
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name='orders'
                """))
                if not result.fetchone():
                    logger.info("Creating orders table...")
                    conn.execute(text("""
                        CREATE TABLE orders (
                            id SERIAL PRIMARY KEY,
                            store_id INTEGER NOT NULL,
                            product_id INTEGER NOT NULL,
                            order_quantity FLOAT NOT NULL,
                            order_date DATE NOT NULL,
                            expected_arrival_date DATE,
                            actual_arrival_date DATE,
                            status VARCHAR(50) DEFAULT 'pending',
                            transit_days INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (store_id) REFERENCES stores(id),
                            FOREIGN KEY (product_id) REFERENCES products(id)
                        )
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_store_id ON orders(store_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_product_id ON orders(product_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_order_date ON orders(order_date)
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_orders_expected_arrival ON orders(expected_arrival_date)
                    """))
                    conn.commit()
                    logger.info("orders table created successfully")
                else:
                    logger.info("orders table already exists")
            
            logger.info("Migration completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed. Check logs for details.")
        sys.exit(1)


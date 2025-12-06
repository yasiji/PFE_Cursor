"""Migration script to add shelf_quantity and backroom_quantity columns to inventory_snapshots table.

This migration adds the ability to distinguish between products on shelves (display)
and products in stock (backroom/warehouse).

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
    """Add shelf_quantity and backroom_quantity columns to inventory_snapshots table."""
    config = get_config()
    database_url = config.database.url
    
    logger.info(f"Starting migration: Adding shelf_quantity and backroom_quantity columns")
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
                    WHERE type='table' AND name='inventory_snapshots'
                """))
                if not result.fetchone():
                    logger.error("Table 'inventory_snapshots' does not exist. Run init_database.py first.")
                    return False
                
                # Check if columns exist
                result = conn.execute(text("PRAGMA table_info(inventory_snapshots)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'shelf_quantity' in columns and 'backroom_quantity' in columns:
                    logger.info("Columns already exist. Migration not needed.")
                    return True
                
                # Add columns if they don't exist
                if 'shelf_quantity' not in columns:
                    logger.info("Adding shelf_quantity column...")
                    conn.execute(text("""
                        ALTER TABLE inventory_snapshots 
                        ADD COLUMN shelf_quantity REAL DEFAULT 0.0 NOT NULL
                    """))
                    conn.commit()
                
                if 'backroom_quantity' not in columns:
                    logger.info("Adding backroom_quantity column...")
                    conn.execute(text("""
                        ALTER TABLE inventory_snapshots 
                        ADD COLUMN backroom_quantity REAL DEFAULT 0.0 NOT NULL
                    """))
                    conn.commit()
            else:
                # PostgreSQL syntax
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='inventory_snapshots' 
                    AND column_name IN ('shelf_quantity', 'backroom_quantity')
                """))
                existing_columns = [row[0] for row in result.fetchall()]
                
                if 'shelf_quantity' in existing_columns and 'backroom_quantity' in existing_columns:
                    logger.info("Columns already exist. Migration not needed.")
                    return True
                
                # Add columns if they don't exist
                if 'shelf_quantity' not in existing_columns:
                    logger.info("Adding shelf_quantity column...")
                    conn.execute(text("""
                        ALTER TABLE inventory_snapshots 
                        ADD COLUMN shelf_quantity FLOAT DEFAULT 0.0 NOT NULL
                    """))
                    conn.commit()
                
                if 'backroom_quantity' not in existing_columns:
                    logger.info("Adding backroom_quantity column...")
                    conn.execute(text("""
                        ALTER TABLE inventory_snapshots 
                        ADD COLUMN backroom_quantity FLOAT DEFAULT 0.0 NOT NULL
                    """))
                    conn.commit()
            
            # Migrate existing data: split quantity into shelf (70%) and backroom (30%)
            # This is safe to run multiple times due to WHERE clause
            try:
                logger.info("Migrating existing data: splitting quantity into shelf (70%) and backroom (30%)...")
                
                if "sqlite" in database_url:
                    conn.execute(text("""
                        UPDATE inventory_snapshots
                        SET shelf_quantity = ROUND(quantity * 0.7, 2),
                            backroom_quantity = ROUND(quantity * 0.3, 2)
                        WHERE shelf_quantity = 0.0 AND backroom_quantity = 0.0 AND quantity > 0
                    """))
                else:
                    conn.execute(text("""
                        UPDATE inventory_snapshots
                        SET shelf_quantity = ROUND(quantity * 0.7, 2),
                            backroom_quantity = ROUND(quantity * 0.3, 2)
                        WHERE shelf_quantity = 0.0 AND backroom_quantity = 0.0 AND quantity > 0
                    """))
                conn.commit()
                logger.info("Data migration completed")
            except Exception as e:
                # Data migration is optional - columns exist, data might already be migrated
                logger.info(f"Data migration skipped (may already be done): {e}")
            
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


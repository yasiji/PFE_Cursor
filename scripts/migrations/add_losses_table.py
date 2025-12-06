"""Migration script to create losses table."""

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
    """Create losses table."""
    config = get_config()
    database_url = config.database.url
    
    logger.info(f"Starting migration: Creating losses table")
    logger.info(f"Database URL: {database_url}")
    
    # Create engine
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            if "sqlite" in database_url:
                # SQLite syntax
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='losses'
                """))
                if result.fetchone():
                    logger.info("losses table already exists")
                    return True
                
                logger.info("Creating losses table...")
                conn.execute(text("""
                    CREATE TABLE losses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        store_id INTEGER NOT NULL,
                        product_id INTEGER,
                        loss_date DATE NOT NULL,
                        loss_type VARCHAR(50) NOT NULL,
                        quantity REAL NOT NULL,
                        cost REAL NOT NULL,
                        revenue_lost REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (store_id) REFERENCES stores(id),
                        FOREIGN KEY (product_id) REFERENCES products(id)
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX idx_losses_store_id ON losses(store_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_losses_product_id ON losses(product_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_losses_loss_date ON losses(loss_date)
                """))
                conn.commit()
                logger.info("losses table created successfully")
            else:
                # PostgreSQL syntax
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name='losses'
                """))
                if result.fetchone():
                    logger.info("losses table already exists")
                    return True
                
                logger.info("Creating losses table...")
                conn.execute(text("""
                    CREATE TABLE losses (
                        id SERIAL PRIMARY KEY,
                        store_id INTEGER NOT NULL,
                        product_id INTEGER,
                        loss_date DATE NOT NULL,
                        loss_type VARCHAR(50) NOT NULL,
                        quantity FLOAT NOT NULL,
                        cost FLOAT NOT NULL,
                        revenue_lost FLOAT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (store_id) REFERENCES stores(id),
                        FOREIGN KEY (product_id) REFERENCES products(id)
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX idx_losses_store_id ON losses(store_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_losses_product_id ON losses(product_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_losses_loss_date ON losses(loss_date)
                """))
                conn.commit()
                logger.info("losses table created successfully")
            
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


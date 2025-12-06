"""Migration script to create notifications table."""

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
    """Create notifications table."""
    config = get_config()
    database_url = config.database.url
    
    logger.info(f"Starting migration: Creating notifications table")
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
                    WHERE type='table' AND name='notifications'
                """))
                if result.fetchone():
                    logger.info("notifications table already exists")
                    return True
                
                logger.info("Creating notifications table...")
                conn.execute(text("""
                    CREATE TABLE notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        store_id INTEGER,
                        type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) DEFAULT 'info',
                        title VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        data TEXT,
                        read BOOLEAN DEFAULT 0 NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (store_id) REFERENCES stores(id)
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_user_id ON notifications(user_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_store_id ON notifications(store_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_read ON notifications(read)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_created_at ON notifications(created_at)
                """))
                conn.commit()
                logger.info("notifications table created successfully")
            else:
                # PostgreSQL syntax
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name='notifications'
                """))
                if result.fetchone():
                    logger.info("notifications table already exists")
                    return True
                
                logger.info("Creating notifications table...")
                conn.execute(text("""
                    CREATE TABLE notifications (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        store_id INTEGER,
                        type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) DEFAULT 'info',
                        title VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        data JSONB,
                        read BOOLEAN DEFAULT FALSE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (store_id) REFERENCES stores(id)
                    )
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_user_id ON notifications(user_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_store_id ON notifications(store_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_read ON notifications(read)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_notifications_created_at ON notifications(created_at)
                """))
                conn.commit()
                logger.info("notifications table created successfully")
            
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


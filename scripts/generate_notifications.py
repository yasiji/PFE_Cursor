"""Background job to generate notifications for all stores.

Run this script periodically (e.g., every 15 minutes) to check for alert conditions
and create notifications for store managers.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from services.api_gateway.database import get_db
from services.api_gateway.models import Store
from services.api_gateway.notification_service import get_notification_service
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def generate_notifications_for_all_stores():
    """Generate notifications for all stores."""
    db: Session = next(get_db())
    notification_service = get_notification_service()
    
    try:
        # Get all stores
        stores = db.query(Store).all()
        logger.info(f"Generating notifications for {len(stores)} stores")
        
        total_notifications = 0
        for store in stores:
            try:
                notifications = notification_service.check_and_create_notifications(
                    store_id=str(store.id),
                    db=db
                )
                total_notifications += len(notifications)
                if notifications:
                    logger.info(f"Created {len(notifications)} notifications for store {store.id}")
            except Exception as e:
                logger.error(f"Error generating notifications for store {store.id}: {e}")
                continue
        
        logger.info(f"Total notifications created: {total_notifications}")
        return total_notifications
    except Exception as e:
        logger.error(f"Error in notification generation: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        count = generate_notifications_for_all_stores()
        print(f"✅ Generated {count} notifications")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


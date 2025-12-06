"""
Ensure test user exists in the database.

This script is called during startup to guarantee the test user is available for login.
It's idempotent - safe to run multiple times.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.api_gateway.database import SessionLocal
from services.api_gateway.models import User, Store
from services.api_gateway.auth import get_password_hash


def ensure_test_user():
    """Ensure test user and store exist."""
    db = SessionLocal()
    
    try:
        # Ensure store 235 exists
        store = db.query(Store).filter(Store.id == 235).first()
        if not store:
            store = Store(
                id=235,
                store_id="235",
                name="Test Store NYC",
                city_id=1
            )
            db.add(store)
            db.commit()
            print("[Created] Store 235 (Test Store NYC)")
        else:
            print("[Exists] Store 235")
        
        # Ensure test_user exists
        user = db.query(User).filter(User.username == "test_user").first()
        if not user:
            user = User(
                username="test_user",
                email="test@example.com",
                hashed_password=get_password_hash("test123"),
                role="store_manager",
                store_id=235,
                is_active=True
            )
            db.add(user)
            db.commit()
            print("[Created] User: test_user (password: test123)")
        else:
            print("[Exists] User: test_user")
        
        # Ensure admin user exists (optional)
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                store_id=235,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("[Created] User: admin (password: admin123)")
        else:
            print("[Exists] User: admin")
        
        print("\n[OK] Test users ready:")
        print("     - test_user / test123 (store_manager)")
        print("     - admin / admin123 (admin)")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(ensure_test_user())


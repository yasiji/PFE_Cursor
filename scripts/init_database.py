"""Initialize database for API gateway."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.api_gateway.database import init_db, Base, engine
from services.api_gateway.models import User, Store, Product, Recommendation, Forecast, InventorySnapshot, MarkdownHistory
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def main():
    """Initialize database."""
    print("=" * 60)
    print("Initializing Database")
    print("=" * 60)
    print()
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"✅ Data directory: {data_dir.absolute()}")
    
    # Initialize database
    try:
        print("Creating database tables...")
        init_db()
        print("✅ Database initialized successfully!")
        print()
        print(f"Database location: data/replenishment.db")
        print()
        print("You can now:")
        print("1. Start the API server: uvicorn services.api_gateway.main:app --reload")
        print("2. Create users via API: POST /api/v1/auth/register")
        print("3. Or use: python test_web_app.py")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


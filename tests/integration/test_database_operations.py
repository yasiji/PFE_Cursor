"""Integration tests for database operations."""

import pytest

# Skip if dependencies not available
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import date, datetime, timedelta
    
    from services.api_gateway.database import Base
    from services.api_gateway.models import Store, Product, Recommendation, Forecast, User
    from services.api_gateway.auth import get_password_hash
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    pytestmark = pytest.mark.skip("API gateway dependencies not available")


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


class TestStoreOperations:
    """Test store database operations."""
    
    def test_create_store(self, db):
        """Test creating a store."""
        store = Store(store_id="235", name="Test Store")
        db.add(store)
        db.commit()
        
        assert store.id is not None
        assert store.store_id == "235"
        assert store.name == "Test Store"
    
    def test_get_store(self, db):
        """Test retrieving a store."""
        store = Store(store_id="236", name="Another Store")
        db.add(store)
        db.commit()
        
        retrieved = db.query(Store).filter(Store.store_id == "236").first()
        assert retrieved is not None
        assert retrieved.name == "Another Store"
    
    def test_store_unique_constraint(self, db):
        """Test store unique constraint."""
        store1 = Store(store_id="237", name="Store 1")
        db.add(store1)
        db.commit()
        
        store2 = Store(store_id="237", name="Store 2")
        db.add(store2)
        with pytest.raises(Exception):  # Should raise integrity error
            db.commit()


class TestProductOperations:
    """Test product database operations."""
    
    def test_create_product(self, db):
        """Test creating a product."""
        product = Product(sku_id="123", name="Test Product", category_id=4)
        db.add(product)
        db.commit()
        
        assert product.id is not None
        assert product.sku_id == "123"
        assert product.name == "Test Product"
    
    def test_get_product(self, db):
        """Test retrieving a product."""
        product = Product(sku_id="456", name="Another Product")
        db.add(product)
        db.commit()
        
        retrieved = db.query(Product).filter(Product.sku_id == "456").first()
        assert retrieved is not None
        assert retrieved.name == "Another Product"


class TestRecommendationOperations:
    """Test recommendation database operations."""
    
    def test_create_recommendation(self, db):
        """Test creating a recommendation."""
        # Create store and product first
        store = Store(store_id="235", name="Test Store")
        product = Product(sku_id="123", name="Test Product")
        db.add(store)
        db.add(product)
        db.commit()
        
        recommendation = Recommendation(
            store_id=store.id,
            product_id=product.id,
            recommendation_date=date.today(),
            order_quantity=25.0,
            status="pending"
        )
        db.add(recommendation)
        db.commit()
        
        assert recommendation.id is not None
        assert recommendation.order_quantity == 25.0
        assert recommendation.status == "pending"
    
    def test_recommendation_relationships(self, db):
        """Test recommendation relationships."""
        store = Store(store_id="235", name="Test Store")
        product = Product(sku_id="123", name="Test Product")
        db.add(store)
        db.add(product)
        db.commit()
        
        recommendation = Recommendation(
            store_id=store.id,
            product_id=product.id,
            recommendation_date=date.today(),
            order_quantity=25.0
        )
        db.add(recommendation)
        db.commit()
        
        # Test relationships
        assert recommendation.store.store_id == "235"
        assert recommendation.product.sku_id == "123"


class TestForecastOperations:
    """Test forecast database operations."""
    
    def test_create_forecast(self, db):
        """Test creating a forecast."""
        store = Store(store_id="235", name="Test Store")
        product = Product(sku_id="123", name="Test Product")
        db.add(store)
        db.add(product)
        db.commit()
        
        forecast = Forecast(
            store_id=store.id,
            product_id=product.id,
            forecast_date=date.today(),
            target_date=date.today() + timedelta(days=1),
            predicted_demand=12.5,
            model_type="lightgbm"
        )
        db.add(forecast)
        db.commit()
        
        assert forecast.id is not None
        assert forecast.predicted_demand == 12.5
        assert forecast.model_type == "lightgbm"


class TestUserOperations:
    """Test user database operations."""
    
    def test_create_user(self, db):
        """Test creating a user."""
        user = User(
            username="test_user",
            email="test@example.com",
            hashed_password=get_password_hash("password"),
            role="store_manager"
        )
        db.add(user)
        db.commit()
        
        assert user.id is not None
        assert user.username == "test_user"
        assert user.role == "store_manager"
    
    def test_user_unique_username(self, db):
        """Test user unique username constraint."""
        user1 = User(
            username="unique_user",
            email="user1@example.com",
            hashed_password=get_password_hash("password"),
            role="store_manager"
        )
        db.add(user1)
        db.commit()
        
        user2 = User(
            username="unique_user",
            email="user2@example.com",
            hashed_password=get_password_hash("password"),
            role="store_manager"
        )
        db.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            db.commit()


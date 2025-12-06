"""Database models for API Gateway."""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from services.api_gateway.database import Base


class Store(Base):
    """Store master data."""
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    city_id = Column(Integer, nullable=True)
    management_group_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_snapshots = relationship("InventorySnapshot", back_populates="store")
    forecasts = relationship("Forecast", back_populates="store")
    recommendations = relationship("Recommendation", back_populates="store")


class Product(Base):
    """Product/SKU master data."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    category_id = Column(Integer, nullable=True)  # Legacy - kept for compatibility
    category = Column(String, nullable=True)  # Human-readable category name
    subcategory_id = Column(Integer, nullable=True)
    subcategory = Column(String, nullable=True)  # Human-readable subcategory name
    shelf_life_days = Column(Integer, nullable=True)
    transit_days = Column(Integer, default=1, nullable=True)  # Default transit time in days
    case_pack_size = Column(Integer, default=1)
    min_order_quantity = Column(Integer, default=1)
    max_order_quantity = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_snapshots = relationship("InventorySnapshot", back_populates="product")
    forecasts = relationship("Forecast", back_populates="product")
    recommendations = relationship("Recommendation", back_populates="product")


class InventorySnapshot(Base):
    """Inventory snapshot at a point in time."""
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=0.0)  # Total quantity (shelf + backroom)
    shelf_quantity = Column(Float, nullable=False, default=0.0)  # Quantity on display shelves
    backroom_quantity = Column(Float, nullable=False, default=0.0)  # Quantity in backroom/warehouse
    expiry_date = Column(Date, nullable=True)  # Earliest expiry date for this batch
    days_until_expiry = Column(Integer, nullable=True)  # Calculated days until expiry
    expiry_buckets = Column(JSON, nullable=True)  # {days_remaining: quantity}
    in_transit = Column(Float, nullable=True, default=0.0)  # Quantity in transit
    to_discard = Column(Float, nullable=True, default=0.0)  # Quantity to be discarded
    sold_today = Column(Float, nullable=True, default=0.0)  # Units sold today
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="inventory_snapshots")
    product = relationship("Product", back_populates="inventory_snapshots")
    
    @property
    def total_quantity(self) -> float:
        """Computed property: total quantity (shelf + backroom)."""
        return self.shelf_quantity + self.backroom_quantity


class Forecast(Base):
    """Demand forecast records."""
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    target_date = Column(Date, nullable=False, index=True)
    predicted_demand = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    model_type = Column(String, nullable=False, default="lightgbm")
    confidence_level = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="forecasts")
    product = relationship("Product", back_populates="forecasts")


class Recommendation(Base):
    """Replenishment recommendations."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    recommendation_date = Column(Date, nullable=False, index=True)
    order_quantity = Column(Float, nullable=False)
    markdown_discount_percent = Column(Float, nullable=True)
    markdown_effective_date = Column(Date, nullable=True)
    markdown_reason = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected, executed
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="recommendations")
    product = relationship("Product", back_populates="recommendations")


class User(Base):
    """User accounts for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="store_manager")  # store_manager, regional_manager, admin
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)  # For store managers
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarkdownHistory(Base):
    """History of markdown actions."""
    __tablename__ = "markdown_history"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    markdown_date = Column(Date, nullable=False, index=True)
    discount_percent = Column(Float, nullable=False)
    units_sold = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    waste_avoided = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductPrice(Base):
    """Product pricing information."""
    __tablename__ = "product_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True, index=True)  # NULL means current price
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", backref="prices")


class ProductCost(Base):
    """Product cost information (cost per unit)."""
    __tablename__ = "product_costs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    cost_per_unit = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True, index=True)  # NULL means current cost
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", backref="costs")


class Order(Base):
    """Order tracking for replenishment - supports multi-product orders."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)  # Nullable for multi-product
    order_quantity = Column(Float, nullable=True)  # Total quantity (sum of lines) or single product qty
    order_date = Column(Date, nullable=False, index=True)
    expected_arrival_date = Column(Date, nullable=True, index=True)
    actual_arrival_date = Column(Date, nullable=True)
    status = Column(String, default="pending")  # pending, approved, ordered, in_transit, delivered, cancelled
    transit_days = Column(Integer, nullable=True)  # Transit time for this order
    total_items = Column(Integer, default=1)  # Number of unique products in order
    notes = Column(Text, nullable=True)  # Order notes from approval
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store = relationship("Store", backref="orders")
    product = relationship("Product", backref="orders")
    order_lines = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")


class OrderLine(Base):
    """Individual line items within an order for multi-product orders."""
    __tablename__ = "order_lines"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=True)  # Price at time of order
    status = Column(String, default="pending")  # Line-level status
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="order_lines")
    product = relationship("Product")
    recommendation = relationship("Recommendation")


class Notification(Base):
    """Notification for users about critical events."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    type = Column(String, nullable=False)  # empty_shelf, low_stock, expiring, order_arrived, stockout_risk
    severity = Column(String, default="info")  # info, warning, error, critical
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional context (product_id, sku_id, etc.)
    read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", backref="notifications")
    store = relationship("Store", backref="notifications")


class Loss(Base):
    """Loss tracking for waste, expiry, and markdowns."""
    __tablename__ = "losses"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    loss_date = Column(Date, nullable=False, index=True)
    loss_type = Column(String, nullable=False)  # waste, expiry, markdown
    quantity = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)  # Cost of lost items
    revenue_lost = Column(Float, nullable=False)  # Potential revenue lost
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    store = relationship("Store", backref="losses")
    product = relationship("Product", backref="losses")

"""Pydantic schemas for API request/response models."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Forecast Schemas
class ForecastRequest(BaseModel):
    """Request schema for forecast endpoint."""
    store_id: str = Field(..., description="Store identifier", min_length=1)
    sku_id: str = Field(..., description="SKU/Product identifier", min_length=1)
    horizon_days: int = Field(1, ge=1, le=14, description="Forecast horizon in days")
    include_uncertainty: bool = Field(False, description="Include prediction intervals")


class ForecastItem(BaseModel):
    """Single forecast item."""
    date: date
    predicted_demand: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class ForecastResponse(BaseModel):
    """Response schema for forecast endpoint."""
    store_id: str
    sku_id: str
    forecasts: List[ForecastItem]
    model_type: str = "lightgbm"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# Replenishment Schemas
class InventoryItem(BaseModel):
    """Current inventory item."""
    sku_id: str
    quantity: float = Field(..., ge=0)
    expiry_date: Optional[date] = None


class ReplenishmentRequest(BaseModel):
    """Request schema for replenishment plan endpoint."""
    store_id: str = Field(..., description="Store identifier")
    target_date: date = Field(..., description="Target date for replenishment plan", alias="date")
    current_inventory: List[InventoryItem] = Field(default_factory=list, description="Current inventory snapshot")
    
    class Config:
        populate_by_name = True


class MarkdownRecommendation(BaseModel):
    """Markdown recommendation."""
    discount_percent: float = Field(..., ge=0, le=100)
    effective_date: date
    reason: str


class ReplenishmentItem(BaseModel):
    """Single replenishment recommendation."""
    sku_id: str
    order_quantity: float = Field(..., ge=0)
    markdown: Optional[MarkdownRecommendation] = None


class ReplenishmentResponse(BaseModel):
    """Response schema for replenishment plan endpoint."""
    store_id: str
    date: date
    recommendations: List[ReplenishmentItem]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# Health Check Schema
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Error Schemas
class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    message: str
    status_code: int


# Price Management Schemas
class ProductPriceCreate(BaseModel):
    """Schema for creating a product price."""
    product_id: int = Field(..., description="Product ID")
    price: float = Field(..., gt=0, description="Price per unit")
    effective_date: date = Field(default_factory=date.today, description="Date when price becomes effective")
    end_date: Optional[date] = Field(None, description="Date when price ends (NULL for current price)")


class ProductPriceResponse(BaseModel):
    """Schema for product price response."""
    id: int
    product_id: int
    price: float
    effective_date: date
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductCostCreate(BaseModel):
    """Schema for creating a product cost."""
    product_id: int = Field(..., description="Product ID")
    cost_per_unit: float = Field(..., gt=0, description="Cost per unit")
    effective_date: date = Field(default_factory=date.today, description="Date when cost becomes effective")
    end_date: Optional[date] = Field(None, description="Date when cost ends (NULL for current cost)")


class ProductCostResponse(BaseModel):
    """Schema for product cost response."""
    id: int
    product_id: int
    cost_per_unit: float
    effective_date: date
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

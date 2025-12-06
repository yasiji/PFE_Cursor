"""Price and cost management routes."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from services.api_gateway.database import get_db
from services.api_gateway.models import ProductPrice, ProductCost, Product
from services.api_gateway.schemas import (
    ProductPriceCreate,
    ProductPriceResponse,
    ProductCostCreate,
    ProductCostResponse
)
from services.api_gateway.auth import get_current_user, require_role
from services.api_gateway.models import User
from shared.logging_setup import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


# ==================== PRICE MANAGEMENT ====================

@router.get("/products/{product_id}/current", response_model=ProductPriceResponse)
async def get_current_price(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current price for a product."""
    today = date.today()
    
    price = db.query(ProductPrice).filter(
        ProductPrice.product_id == product_id,
        ProductPrice.effective_date <= today,
        or_(
            ProductPrice.end_date.is_(None),
            ProductPrice.end_date >= today
        )
    ).order_by(ProductPrice.effective_date.desc()).first()
    
    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No current price found for product {product_id}"
        )
    
    return price


@router.get("/products/{product_id}/history", response_model=List[ProductPriceResponse])
async def get_price_history(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get price history for a product."""
    prices = db.query(ProductPrice).filter(
        ProductPrice.product_id == product_id
    ).order_by(ProductPrice.effective_date.desc()).all()
    
    return prices


@router.post("/products/{product_id}", response_model=ProductPriceResponse, status_code=status.HTTP_201_CREATED)
async def create_price(
    product_id: int,
    price_data: ProductPriceCreate,
    current_user: User = Depends(require_role(["admin", "regional_manager"])),
    db: Session = Depends(get_db)
):
    """Create a new price for a product."""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    # Verify product_id matches
    if price_data.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product ID in URL must match product_id in body"
        )
    
    # If this is a new current price, end the previous current price
    if price_data.end_date is None:
        # End all current prices (where end_date is NULL)
        db.query(ProductPrice).filter(
            ProductPrice.product_id == product_id,
            ProductPrice.end_date.is_(None)
        ).update({"end_date": price_data.effective_date})
    
    # Create new price
    new_price = ProductPrice(
        product_id=product_id,
        price=price_data.price,
        effective_date=price_data.effective_date,
        end_date=price_data.end_date
    )
    
    db.add(new_price)
    db.commit()
    db.refresh(new_price)
    
    logger.info(f"Created new price for product {product_id}: ${price_data.price}")
    return new_price


@router.put("/products/{product_id}/current", response_model=ProductPriceResponse)
async def update_current_price(
    product_id: int,
    new_price: float,
    current_user: User = Depends(require_role(["admin", "regional_manager"])),
    db: Session = Depends(get_db)
):
    """Update the current price for a product (creates new price entry and ends old one)."""
    if new_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price must be greater than 0"
        )
    
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    today = date.today()
    
    # End all current prices
    db.query(ProductPrice).filter(
        ProductPrice.product_id == product_id,
        ProductPrice.end_date.is_(None)
    ).update({"end_date": today})
    
    # Create new current price
    new_price_entry = ProductPrice(
        product_id=product_id,
        price=new_price,
        effective_date=today,
        end_date=None
    )
    
    db.add(new_price_entry)
    db.commit()
    db.refresh(new_price_entry)
    
    logger.info(f"Updated current price for product {product_id}: ${new_price}")
    return new_price_entry


# ==================== COST MANAGEMENT ====================

@router.get("/products/{product_id}/cost/current", response_model=ProductCostResponse)
async def get_current_cost(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current cost for a product."""
    today = date.today()
    
    cost = db.query(ProductCost).filter(
        ProductCost.product_id == product_id,
        ProductCost.effective_date <= today,
        or_(
            ProductCost.end_date.is_(None),
            ProductCost.end_date >= today
        )
    ).order_by(ProductCost.effective_date.desc()).first()
    
    if not cost:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No current cost found for product {product_id}"
        )
    
    return cost


@router.get("/products/{product_id}/cost/history", response_model=List[ProductCostResponse])
async def get_cost_history(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cost history for a product."""
    costs = db.query(ProductCost).filter(
        ProductCost.product_id == product_id
    ).order_by(ProductCost.effective_date.desc()).all()
    
    return costs


@router.post("/products/{product_id}/cost", response_model=ProductCostResponse, status_code=status.HTTP_201_CREATED)
async def create_cost(
    product_id: int,
    cost_data: ProductCostCreate,
    current_user: User = Depends(require_role(["admin", "regional_manager"])),
    db: Session = Depends(get_db)
):
    """Create a new cost for a product."""
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    # Verify product_id matches
    if cost_data.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product ID in URL must match product_id in body"
        )
    
    # If this is a new current cost, end the previous current cost
    if cost_data.end_date is None:
        # End all current costs (where end_date is NULL)
        db.query(ProductCost).filter(
            ProductCost.product_id == product_id,
            ProductCost.end_date.is_(None)
        ).update({"end_date": cost_data.effective_date})
    
    # Create new cost
    new_cost = ProductCost(
        product_id=product_id,
        cost_per_unit=cost_data.cost_per_unit,
        effective_date=cost_data.effective_date,
        end_date=cost_data.end_date
    )
    
    db.add(new_cost)
    db.commit()
    db.refresh(new_cost)
    
    logger.info(f"Created new cost for product {product_id}: ${cost_data.cost_per_unit}")
    return new_cost


@router.put("/products/{product_id}/cost/current", response_model=ProductCostResponse)
async def update_current_cost(
    product_id: int,
    new_cost: float,
    current_user: User = Depends(require_role(["admin", "regional_manager"])),
    db: Session = Depends(get_db)
):
    """Update the current cost for a product (creates new cost entry and ends old one)."""
    if new_cost <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cost must be greater than 0"
        )
    
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    today = date.today()
    
    # End all current costs
    db.query(ProductCost).filter(
        ProductCost.product_id == product_id,
        ProductCost.end_date.is_(None)
    ).update({"end_date": today})
    
    # Create new current cost
    new_cost_entry = ProductCost(
        product_id=product_id,
        cost_per_unit=new_cost,
        effective_date=today,
        end_date=None
    )
    
    db.add(new_cost_entry)
    db.commit()
    db.refresh(new_cost_entry)
    
    logger.info(f"Updated current cost for product {product_id}: ${new_cost}")
    return new_cost_entry


"""
Markdown management routes - apply discounts to near-expiry products.
"""

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from services.api_gateway.database import get_db
from services.api_gateway.models import User, Store, Product, InventorySnapshot, MarkdownHistory
from services.api_gateway.auth import get_current_user
from shared.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/markdowns", tags=["markdowns"])


class ApplyMarkdownRequest(BaseModel):
    """Request model for applying markdown."""
    product_id: int
    discount_percent: float = Field(..., ge=0, le=100)
    reason: Optional[str] = None


class MarkdownResponse(BaseModel):
    """Response model for markdown."""
    id: int
    store_id: int
    product_id: int
    sku_id: str
    markdown_date: date
    discount_percent: float
    units_sold: Optional[float] = None
    revenue: Optional[float] = None
    waste_avoided: Optional[float] = None

    class Config:
        from_attributes = True


@router.post("/apply")
async def apply_markdown(
    store_id: str,
    request: ApplyMarkdownRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply a markdown (discount) to a product in a store.
    
    Typically used for near-expiry products to reduce waste.
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
        
        # Authorization check
        if current_user.role == "store_manager":
            if current_user.store_id != int(store_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to apply markdowns for this store"
                )
        
        # Get product
        product = db.query(Product).filter(Product.id == request.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Get current inventory
        today = date.today()
        inventory = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.product_id == request.product_id,
            InventorySnapshot.snapshot_date == today
        ).first()
        
        if not inventory or inventory.quantity == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No inventory available for markdown"
            )
        
        # Create markdown history record
        markdown = MarkdownHistory(
            store_id=int(store_id),
            product_id=request.product_id,
            markdown_date=today,
            discount_percent=request.discount_percent,
            units_sold=None,  # Will be updated when sales are recorded
            revenue=None,
            waste_avoided=None
        )
        
        db.add(markdown)
        db.commit()
        db.refresh(markdown)
        
        logger.info(
            f"Markdown applied by {current_user.username}",
            store_id=store_id,
            product_id=request.product_id,
            sku_id=product.sku_id,
            discount_percent=request.discount_percent
        )
        
        return {
            "message": "Markdown applied successfully",
            "markdown_id": markdown.id,
            "store_id": int(store_id),
            "product_id": request.product_id,
            "sku_id": product.sku_id,
            "discount_percent": request.discount_percent,
            "markdown_date": today.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying markdown: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error applying markdown"
        )


@router.get("/{store_id}/history", response_model=List[MarkdownResponse])
async def get_markdown_history(
    store_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get markdown history for a store.
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
        
        # Authorization check
        if current_user.role == "store_manager":
            if current_user.store_id != int(store_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view markdown history for this store"
                )
        
        # Build query
        query = db.query(MarkdownHistory).filter(
            MarkdownHistory.store_id == int(store_id)
        )
        
        if start_date:
            query = query.filter(MarkdownHistory.markdown_date >= date.fromisoformat(start_date))
        if end_date:
            query = query.filter(MarkdownHistory.markdown_date <= date.fromisoformat(end_date))
        
        markdowns = query.order_by(MarkdownHistory.markdown_date.desc()).limit(100).all()
        
        # Format response
        result = []
        for markdown in markdowns:
            product = db.query(Product).filter(Product.id == markdown.product_id).first()
            result.append(MarkdownResponse(
                id=markdown.id,
                store_id=markdown.store_id,
                product_id=markdown.product_id,
                sku_id=product.sku_id if product else "Unknown",
                markdown_date=markdown.markdown_date,
                discount_percent=markdown.discount_percent,
                units_sold=markdown.units_sold,
                revenue=markdown.revenue,
                waste_avoided=markdown.waste_avoided
            ))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting markdown history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving markdown history"
        )


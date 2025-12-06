"""
Inventory management routes - discard expired items.
"""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from services.api_gateway.database import get_db
from services.api_gateway.models import User, Store, Product, InventorySnapshot
from services.api_gateway.auth import get_current_user
from shared.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


class DiscardRequest(BaseModel):
    """Request model for discarding inventory."""
    product_id: int
    quantity: float = Field(..., gt=0)
    reason: Optional[str] = None


@router.post("/{store_id}/discard")
async def discard_inventory(
    store_id: str,
    request: DiscardRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Discard (remove) inventory items, typically expired products.
    
    This reduces the inventory quantity and should be used for waste tracking.
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
                    detail="Not authorized to discard inventory for this store"
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
        
        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No inventory found for this product"
            )
        
        # Check if enough quantity available
        if inventory.quantity < request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory. Available: {inventory.quantity}, Requested: {request.quantity}"
            )
        
        # Update inventory quantity
        inventory.quantity -= request.quantity
        
        # Update expiry buckets if needed (remove from expiring buckets)
        if inventory.expiry_buckets:
            # Simple logic: reduce from 1_3 days bucket first
            if inventory.expiry_buckets.get("1_3", 0) > 0:
                reduce_from = min(request.quantity, inventory.expiry_buckets.get("1_3", 0))
                inventory.expiry_buckets["1_3"] = max(0, inventory.expiry_buckets["1_3"] - reduce_from)
                request.quantity -= reduce_from
            
            # Then from 4_7 days bucket
            if request.quantity > 0 and inventory.expiry_buckets.get("4_7", 0) > 0:
                reduce_from = min(request.quantity, inventory.expiry_buckets.get("4_7", 0))
                inventory.expiry_buckets["4_7"] = max(0, inventory.expiry_buckets["4_7"] - reduce_from)
                request.quantity -= reduce_from
            
            # Finally from 8_plus bucket
            if request.quantity > 0 and inventory.expiry_buckets.get("8_plus", 0) > 0:
                reduce_from = min(request.quantity, inventory.expiry_buckets.get("8_plus", 0))
                inventory.expiry_buckets["8_plus"] = max(0, inventory.expiry_buckets["8_plus"] - reduce_from)
        
        db.commit()
        db.refresh(inventory)
        
        logger.info(
            f"Inventory discarded by {current_user.username}",
            store_id=store_id,
            product_id=request.product_id,
            sku_id=product.sku_id,
            quantity=request.quantity,
            reason=request.reason
        )
        
        return {
            "message": "Inventory discarded successfully",
            "store_id": int(store_id),
            "product_id": request.product_id,
            "sku_id": product.sku_id,
            "quantity_discarded": request.quantity,
            "remaining_quantity": inventory.quantity,
            "reason": request.reason
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discarding inventory: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error discarding inventory"
        )


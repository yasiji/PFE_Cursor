"""
Order management routes - approval, rejection, and execution.
"""

from datetime import date, datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.api_gateway.database import get_db
from services.api_gateway.models import User, Store, Recommendation, Order
from services.api_gateway.auth import get_current_user
from services.api_gateway.order_service import get_order_service
from shared.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


class CreateOrderRequest(BaseModel):
    """Request model for creating an order."""
    store_id: str
    recommendation_ids: List[int]
    order_date: Optional[str] = None  # ISO date string, defaults to today


class UpdateOrderStatusRequest(BaseModel):
    """Request model for updating order status."""
    status: str
    actual_arrival_date: Optional[str] = None  # ISO date string


class OrderApprovalRequest(BaseModel):
    """Request model for order approval."""
    notes: Optional[str] = None


class OrderRejectionRequest(BaseModel):
    """Request model for order rejection."""
    reason: str


@router.post("/{order_id}/approve")
async def approve_order(
    order_id: int,
    request: OrderApprovalRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a pending order recommendation.
    
    Only store managers can approve orders for their store.
    Regional managers and admins can approve any order.
    """
    try:
        # Get the recommendation
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == order_id
        ).first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Authorization check
        if current_user.role == "store_manager":
            if current_user.store_id != recommendation.store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to approve orders for this store"
                )
        
        # Check if already processed
        if recommendation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order is already {recommendation.status}"
            )
        
        # Update recommendation
        recommendation.status = "approved"
        recommendation.approved_by = current_user.username
        recommendation.approved_at = datetime.utcnow()
        if request and request.notes:
            recommendation.markdown_reason = request.notes  # Reuse field for notes
        
        db.commit()
        db.refresh(recommendation)
        
        logger.info(
            f"Order {order_id} approved by {current_user.username}",
            order_id=order_id,
            store_id=recommendation.store_id,
            product_id=recommendation.product_id
        )
        
        return {
            "message": "Order approved successfully",
            "order_id": order_id,
            "status": "approved"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving order: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error approving order"
        )


@router.post("/{order_id}/reject")
async def reject_order(
    order_id: int,
    request: OrderRejectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a pending order recommendation.
    
    Only store managers can reject orders for their store.
    Regional managers and admins can reject any order.
    """
    try:
        # Get the recommendation
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == order_id
        ).first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Authorization check
        if current_user.role == "store_manager":
            if current_user.store_id != recommendation.store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to reject orders for this store"
                )
        
        # Check if already processed
        if recommendation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order is already {recommendation.status}"
            )
        
        # Update recommendation
        recommendation.status = "rejected"
        recommendation.approved_by = current_user.username
        recommendation.approved_at = datetime.utcnow()
        recommendation.markdown_reason = request.reason
        
        db.commit()
        db.refresh(recommendation)
        
        logger.info(
            f"Order {order_id} rejected by {current_user.username}",
            order_id=order_id,
            store_id=recommendation.store_id,
            product_id=recommendation.product_id,
            reason=request.reason
        )
        
        return {
            "message": "Order rejected successfully",
            "order_id": order_id,
            "status": "rejected"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting order: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error rejecting order"
        )


@router.post("/{order_id}/execute")
async def execute_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark an approved order as executed (order placed with supplier).
    
    Only store managers can execute orders for their store.
    """
    try:
        # Get the recommendation
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == order_id
        ).first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Authorization check
        if current_user.role == "store_manager":
            if current_user.store_id != recommendation.store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to execute orders for this store"
                )
        
        # Check if approved
        if recommendation.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order must be approved before execution. Current status: {recommendation.status}"
            )
        
        # Update recommendation
        recommendation.status = "executed"
        recommendation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(recommendation)
        
        logger.info(
            f"Order {order_id} executed by {current_user.username}",
            order_id=order_id,
            store_id=recommendation.store_id,
            product_id=recommendation.product_id
        )
        
        return {
            "message": "Order executed successfully",
            "order_id": order_id,
            "status": "executed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing order: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error executing order"
        )


@router.post("", response_model=Dict)
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create an order from approved recommendations."""
    try:
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(request.store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create orders for this store"
            )
        
        # Parse order date
        if request.order_date:
            order_date = date.fromisoformat(request.order_date)
        else:
            order_date = date.today()
        
        # Create order
        order_service = get_order_service()
        order = order_service.create_order_from_recommendations(
            store_id=request.store_id,
            recommendation_ids=request.recommendation_ids,
            order_date=order_date,
            db=db
        )
        
        return {
            "message": "Order created successfully",
            "order_id": order.id,
            "status": order.status,
            "expected_arrival_date": order.expected_arrival_date.isoformat() if order.expected_arrival_date else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating order"
        )


@router.get("/{order_id}", response_model=Dict)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order details with tracking information."""
    try:
        order_service = get_order_service()
        order_details = order_service.get_order_details(order_id, db)
        
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != order_details["store_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this order"
            )
        
        return order_details
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving order"
        )


@router.put("/{order_id}/status", response_model=Dict)
async def update_order_status(
    order_id: int,
    request: UpdateOrderStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update order status (e.g., mark as delivered)."""
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != order.store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this order"
            )
        
        # Parse actual arrival date
        actual_arrival = None
        if request.actual_arrival_date:
            actual_arrival = date.fromisoformat(request.actual_arrival_date)
        
        order_service = get_order_service()
        updated_order = order_service.update_order_status(
            order_id=order_id,
            new_status=request.status,
            actual_arrival_date=actual_arrival,
            db=db
        )
        
        return {
            "message": "Order status updated successfully",
            "order_id": order_id,
            "status": updated_order.status,
            "actual_arrival_date": updated_order.actual_arrival_date.isoformat() if updated_order.actual_arrival_date else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating order status"
        )


@router.get("/stores/{store_id}/orders", response_model=List[Dict])
async def get_store_orders(
    store_id: str,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get orders for a store with optional filters."""
    try:
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view orders for this store"
            )
        
        # Parse dates
        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = date.fromisoformat(start_date)
        if end_date:
            end_date_obj = date.fromisoformat(end_date)
        
        order_service = get_order_service()
        orders = order_service.get_store_orders(
            store_id=store_id,
            status=status,
            start_date=start_date_obj,
            end_date=end_date_obj,
            db=db
        )
        
        return orders
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting store orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving orders"
        )


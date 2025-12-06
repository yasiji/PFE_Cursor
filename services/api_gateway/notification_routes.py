"""Notification API routes."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.api_gateway.database import get_db
from services.api_gateway.models import Notification, User
from services.api_gateway.auth import get_current_user
from services.api_gateway.notification_service import get_notification_service
from shared.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    """Notification response model."""
    id: int
    user_id: int
    store_id: Optional[int]
    type: str
    severity: str
    title: str
    message: str
    data: Optional[dict] = None
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    read: Optional[bool] = Query(None, description="Filter by read status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's notifications."""
    try:
        query = db.query(Notification).filter(Notification.user_id == current_user.id)
        
        if read is not None:
            query = query.filter(Notification.read == read)
        
        if severity:
            query = query.filter(Notification.severity == severity)
        
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
        
        return [NotificationResponse.model_validate(n) for n in notifications]
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving notifications"
        )


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications."""
    try:
        count = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.read == False
        ).count()
        
        return {"unread_count": count}
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving unread count"
        )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        notification.read = True
        db.commit()
        db.refresh(notification)
        
        return NotificationResponse.model_validate(notification)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating notification"
        )


@router.post("/read-all", response_model=dict)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    try:
        updated = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.read == False
        ).update({"read": True})
        
        db.commit()
        
        return {"updated_count": updated}
    except Exception as e:
        logger.error(f"Error marking all as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating notifications"
        )


@router.post("/generate", response_model=dict)
async def generate_notifications(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger notification generation for a store."""
    try:
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to generate notifications for this store"
            )
        
        notification_service = get_notification_service()
        notifications = notification_service.check_and_create_notifications(
            store_id=store_id,
            db=db,
            user_id=current_user.id if current_user.role == "store_manager" else None
        )
        
        return {
            "generated_count": len(notifications),
            "notifications": [NotificationResponse.model_validate(n).model_dump() for n in notifications]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating notifications"
        )


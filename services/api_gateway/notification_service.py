"""Service for generating and managing notifications."""

from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from services.api_gateway.models import (
    Notification, InventorySnapshot, Product, Order, User, Store
)
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for checking conditions and creating notifications."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def check_and_create_notifications(
        self,
        store_id: str,
        db: Session,
        user_id: Optional[int] = None
    ) -> List[Notification]:
        """
        Check for alert conditions and create notifications.
        
        Args:
            store_id: Store identifier
            db: Database session
            user_id: Optional user ID (if None, creates for all store managers)
            
        Returns:
            List of created notifications
        """
        notifications = []
        today = date.today()
        
        # Get store
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            return notifications
        
        # Get users for this store (if user_id not specified)
        if user_id:
            users = [db.query(User).filter(User.id == user_id).first()]
        else:
            users = db.query(User).filter(
                User.store_id == int(store_id),
                User.role == "store_manager"
            ).all()
        
        if not users:
            return notifications
        
        # Get current inventory
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == today
        ).all()
        
        # 1. Check for empty shelves
        empty_shelf_items = []
        for inv in inventory_snapshots:
            shelf_qty = getattr(inv, 'shelf_quantity', None)
            if shelf_qty is None:
                shelf_qty = inv.quantity * 0.7  # Fallback
            if shelf_qty <= 0 and inv.quantity > 0:
                product = db.query(Product).filter(Product.id == inv.product_id).first()
                if product:
                    empty_shelf_items.append({
                        'product_name': product.name or product.sku_id,
                        'sku_id': product.sku_id,
                        'backroom_qty': getattr(inv, 'backroom_quantity', inv.quantity * 0.3)
                    })
        
        if empty_shelf_items:
            for user in users:
                notification = self._create_notification(
                    db=db,
                    user_id=user.id,
                    store_id=int(store_id),
                    type="empty_shelf",
                    severity="warning",
                    title=f"{len(empty_shelf_items)} Empty Shelf{'s' if len(empty_shelf_items) > 1 else ''}",
                    message=f"{len(empty_shelf_items)} product(s) have empty shelves but stock in backroom. Need refill.",
                    data={"items": empty_shelf_items[:5]}  # Limit to 5 for message
                )
                if notification:
                    notifications.append(notification)
        
        # 2. Check for low stock items
        low_stock_items = []
        for inv in inventory_snapshots:
            total_qty = inv.quantity
            if total_qty > 0 and total_qty < 10:  # Low stock threshold
                product = db.query(Product).filter(Product.id == inv.product_id).first()
                if product:
                    low_stock_items.append({
                        'product_name': product.name or product.sku_id,
                        'sku_id': product.sku_id,
                        'quantity': total_qty
                    })
        
        if low_stock_items:
            for user in users:
                notification = self._create_notification(
                    db=db,
                    user_id=user.id,
                    store_id=int(store_id),
                    type="low_stock",
                    severity="warning",
                    title=f"{len(low_stock_items)} Low Stock Item{'s' if len(low_stock_items) > 1 else ''}",
                    message=f"{len(low_stock_items)} product(s) are running low on stock (<10 units). Consider ordering.",
                    data={"items": low_stock_items[:5]}
                )
                if notification:
                    notifications.append(notification)
        
        # 3. Check for expiring items (1-3 days)
        expiring_items = []
        for inv in inventory_snapshots:
            expiry_buckets = inv.expiry_buckets or {}
            qty_1_3 = expiry_buckets.get("1_3", 0.0)
            if qty_1_3 > 0:
                product = db.query(Product).filter(Product.id == inv.product_id).first()
                if product:
                    expiring_items.append({
                        'product_name': product.name or product.sku_id,
                        'sku_id': product.sku_id,
                        'quantity': qty_1_3
                    })
        
        if expiring_items:
            for user in users:
                notification = self._create_notification(
                    db=db,
                    user_id=user.id,
                    store_id=int(store_id),
                    type="expiring",
                    severity="error",
                    title=f"{len(expiring_items)} Item{'s' if len(expiring_items) > 1 else ''} Expiring Soon",
                    message=f"{len(expiring_items)} product(s) are expiring in 1-3 days. Apply markdowns or discard.",
                    data={"items": expiring_items[:5]}
                )
                if notification:
                    notifications.append(notification)
        
        # 4. Check for orders arriving today
        orders_arriving = db.query(Order).filter(
            Order.store_id == int(store_id),
            Order.status.in_(["ordered", "in_transit"]),
            Order.expected_arrival_date == today
        ).all()
        
        if orders_arriving:
            for user in users:
                notification = self._create_notification(
                    db=db,
                    user_id=user.id,
                    store_id=int(store_id),
                    type="order_arrived",
                    severity="info",
                    title=f"{len(orders_arriving)} Order{'s' if len(orders_arriving) > 1 else ''} Arriving Today",
                    message=f"{len(orders_arriving)} order(s) are expected to arrive today. Check delivery status.",
                    data={"order_ids": [o.id for o in orders_arriving]}
                )
                if notification:
                    notifications.append(notification)
        
        # 5. Check for stockout risks (forecast > available inventory)
        # This would require forecast data, simplified for now
        stockout_risks = []
        for inv in inventory_snapshots:
            if inv.quantity < 5:  # Very low stock
                product = db.query(Product).filter(Product.id == inv.product_id).first()
                if product:
                    stockout_risks.append({
                        'product_name': product.name or product.sku_id,
                        'sku_id': product.sku_id,
                        'quantity': inv.quantity
                    })
        
        if stockout_risks:
            for user in users:
                notification = self._create_notification(
                    db=db,
                    user_id=user.id,
                    store_id=int(store_id),
                    type="stockout_risk",
                    severity="critical",
                    title=f"{len(stockout_risks)} Stockout Risk{'s' if len(stockout_risks) > 1 else ''}",
                    message=f"{len(stockout_risks)} product(s) are at risk of stockout (<5 units). Urgent order needed.",
                    data={"items": stockout_risks[:5]}
                )
                if notification:
                    notifications.append(notification)
        
        return notifications
    
    def _create_notification(
        self,
        db: Session,
        user_id: int,
        store_id: int,
        type: str,
        severity: str,
        title: str,
        message: str,
        data: Optional[Dict] = None
    ) -> Optional[Notification]:
        """Create a notification if it doesn't already exist (avoid duplicates)."""
        # Check if similar notification already exists (within last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        existing = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.store_id == store_id,
            Notification.type == type,
            Notification.read == False,
            Notification.created_at >= one_hour_ago
        ).first()
        
        if existing:
            return None  # Don't create duplicate
        
        notification = Notification(
            user_id=user_id,
            store_id=store_id,
            type=type,
            severity=severity,
            title=title,
            message=message,
            data=data or {},
            read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification


def get_notification_service() -> NotificationService:
    """Get or create the global NotificationService singleton."""
    global _notification_service_instance
    if '_notification_service_instance' not in globals():
        _notification_service_instance = NotificationService()
    return _notification_service_instance


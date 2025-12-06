"""Service for managing orders from recommendations to delivery."""

from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from services.api_gateway.models import Order, OrderLine, Recommendation, Product, Store
from services.api_gateway.price_service import get_product_price
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class OrderService:
    """Service for order management workflow - supports multi-product orders."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def create_order_from_recommendations(
        self,
        store_id: str,
        recommendation_ids: List[int],
        order_date: date,
        db: Session,
        notes: Optional[str] = None
    ) -> Order:
        """
        Create an order from approved recommendations.
        
        Supports multi-product orders by creating OrderLine items for each recommendation.
        
        Args:
            store_id: Store identifier
            recommendation_ids: List of recommendation IDs to include
            order_date: Date the order is placed
            db: Database session
            notes: Optional notes for the order
            
        Returns:
            Created Order object with all order lines
        """
        # Get recommendations
        recommendations = db.query(Recommendation).filter(
            Recommendation.id.in_(recommendation_ids),
            Recommendation.store_id == int(store_id),
            Recommendation.status == "approved"
        ).all()
        
        if not recommendations:
            raise ValueError("No approved recommendations found")
        
        # Calculate total quantity and max transit time
        total_quantity = 0.0
        max_transit_days = 1
        
        for rec in recommendations:
            product = db.query(Product).filter(Product.id == rec.product_id).first()
            if product:
                total_quantity += rec.order_quantity
                if product.transit_days and product.transit_days > max_transit_days:
                    max_transit_days = product.transit_days
        
        # Calculate expected arrival date based on longest transit time
        expected_arrival = order_date + timedelta(days=max_transit_days)
        
        # Create the main order
        order = Order(
            store_id=int(store_id),
            product_id=recommendations[0].product_id if len(recommendations) == 1 else None,
            order_quantity=total_quantity,
            order_date=order_date,
            expected_arrival_date=expected_arrival,
            status="ordered",
            transit_days=max_transit_days,
            total_items=len(recommendations),
            notes=notes
        )
        
        db.add(order)
        db.flush()  # Get the order ID
        
        # Create order lines for each recommendation (multi-product support)
        for rec in recommendations:
            product = db.query(Product).filter(Product.id == rec.product_id).first()
            unit_price = get_product_price(db, product_id=rec.product_id) if product else None
            
            order_line = OrderLine(
                order_id=order.id,
                product_id=rec.product_id,
                recommendation_id=rec.id,
                quantity=rec.order_quantity,
                unit_price=unit_price,
                status="ordered"
            )
            db.add(order_line)
            
            # Update recommendation status
            rec.status = "executed"
        
        db.commit()
        db.refresh(order)
        
        self.logger.info(
            f"Created order {order.id} with {len(recommendations)} products, "
            f"total quantity: {total_quantity}"
        )
        return order
    
    def get_order_details(
        self,
        order_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Get detailed order information including all order lines."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        product = db.query(Product).filter(Product.id == order.product_id).first() if order.product_id else None
        store = db.query(Store).filter(Store.id == order.store_id).first()
        
        # Get order lines (multi-product support)
        order_lines_data = []
        if hasattr(order, 'order_lines') and order.order_lines:
            for line in order.order_lines:
                line_product = db.query(Product).filter(Product.id == line.product_id).first()
                order_lines_data.append({
                    "id": line.id,
                    "product_id": line.product_id,
                    "product_name": line_product.name if line_product else None,
                    "sku_id": line_product.sku_id if line_product else None,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "total_value": (line.quantity * line.unit_price) if line.unit_price else None,
                    "status": line.status
                })
        
        # Calculate status timeline
        timeline = []
        timeline.append({
            "status": "created",
            "date": order.created_at.isoformat(),
            "description": "Order created"
        })
        
        if order.status in ["ordered", "in_transit", "delivered"]:
            timeline.append({
                "status": "ordered",
                "date": order.order_date.isoformat(),
                "description": "Order placed with supplier"
            })
        
        if order.status in ["in_transit", "delivered"]:
            timeline.append({
                "status": "in_transit",
                "date": order.order_date.isoformat(),
                "description": "Order in transit"
            })
        
        if order.status == "delivered" and order.actual_arrival_date:
            timeline.append({
                "status": "delivered",
                "date": order.actual_arrival_date.isoformat(),
                "description": "Order delivered"
            })
        
        # Calculate total order value
        total_value = sum(
            (line.quantity * line.unit_price) if line.unit_price else 0 
            for line in (order.order_lines or [])
        ) if hasattr(order, 'order_lines') else None
        
        return {
            "id": order.id,
            "store_id": order.store_id,
            "store_name": store.name if store else None,
            "product_id": order.product_id,
            "product_name": product.name if product else "Multiple Products",
            "sku_id": product.sku_id if product else None,
            "order_quantity": order.order_quantity,
            "total_items": order.total_items or 1,
            "total_value": total_value,
            "order_lines": order_lines_data,
            "order_date": order.order_date.isoformat(),
            "expected_arrival_date": order.expected_arrival_date.isoformat() if order.expected_arrival_date else None,
            "actual_arrival_date": order.actual_arrival_date.isoformat() if order.actual_arrival_date else None,
            "status": order.status,
            "transit_days": order.transit_days,
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "timeline": timeline,
            "is_late": self._is_order_late(order),
            "days_until_arrival": self._days_until_arrival(order)
        }
    
    def update_order_status(
        self,
        order_id: int,
        new_status: str,
        actual_arrival_date: Optional[date] = None,
        db: Session = None
    ) -> Order:
        """Update order status."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        valid_statuses = ["pending", "approved", "ordered", "in_transit", "delivered", "cancelled"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
        
        order.status = new_status
        if actual_arrival_date:
            order.actual_arrival_date = actual_arrival_date
        
        db.commit()
        db.refresh(order)
        
        self.logger.info(f"Updated order {order_id} status to {new_status}")
        return order
    
    def get_store_orders(
        self,
        store_id: str,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get orders for a store with optional filters."""
        query = db.query(Order).filter(Order.store_id == int(store_id))
        
        if status:
            query = query.filter(Order.status == status)
        
        if start_date:
            query = query.filter(Order.order_date >= start_date)
        
        if end_date:
            query = query.filter(Order.order_date <= end_date)
        
        orders = query.order_by(Order.order_date.desc()).all()
        
        result = []
        for order in orders:
            product = db.query(Product).filter(Product.id == order.product_id).first()
            result.append({
                "id": order.id,
                "product_id": order.product_id,
                "product_name": product.name if product else None,
                "sku_id": product.sku_id if product else None,
                "order_quantity": order.order_quantity,
                "order_date": order.order_date.isoformat(),
                "expected_arrival_date": order.expected_arrival_date.isoformat() if order.expected_arrival_date else None,
                "actual_arrival_date": order.actual_arrival_date.isoformat() if order.actual_arrival_date else None,
                "status": order.status,
                "transit_days": order.transit_days,
                "is_late": self._is_order_late(order),
                "days_until_arrival": self._days_until_arrival(order)
            })
        
        return result
    
    def _is_order_late(self, order: Order) -> bool:
        """Check if order is late."""
        if not order.expected_arrival_date:
            return False
        today = date.today()
        if order.status == "delivered" and order.actual_arrival_date:
            return order.actual_arrival_date > order.expected_arrival_date
        return today > order.expected_arrival_date and order.status != "delivered"
    
    def _days_until_arrival(self, order: Order) -> Optional[int]:
        """Calculate days until expected arrival."""
        if not order.expected_arrival_date:
            return None
        today = date.today()
        delta = (order.expected_arrival_date - today).days
        return delta if delta >= 0 else None


def get_order_service() -> OrderService:
    """Get or create the global OrderService singleton."""
    global _order_service_instance
    if '_order_service_instance' not in globals():
        _order_service_instance = OrderService()
    return _order_service_instance


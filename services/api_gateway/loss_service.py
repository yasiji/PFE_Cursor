"""Service for calculating and tracking losses (waste, expiry, markdowns)."""

from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from services.api_gateway.models import Loss, InventorySnapshot, Product, ProductCost, ProductPrice
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class LossService:
    """Service for calculating and tracking losses."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def calculate_daily_losses(
        self,
        store_id: str,
        target_date: date,
        db: Session
    ) -> Dict[str, float]:
        """
        Calculate daily losses for a store.
        
        Args:
            store_id: Store identifier
            target_date: Date to calculate losses for
            db: Database session
            
        Returns:
            Dictionary with loss breakdown
        """
        # Get inventory snapshots
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == target_date
        ).all()
        
        waste_loss = 0.0
        markdown_loss = 0.0
        expiry_loss = 0.0
        
        for inv in inventory_snapshots:
            product = db.query(Product).filter(Product.id == inv.product_id).first()
            if not product:
                continue
            
            # Get cost per unit
            cost_record = db.query(ProductCost).filter(
                ProductCost.product_id == product.id,
                ProductCost.effective_date <= target_date,
                (ProductCost.end_date.is_(None) | (ProductCost.end_date >= target_date))
            ).order_by(ProductCost.effective_date.desc()).first()
            
            cost_per_unit = cost_record.cost_per_unit if cost_record else 0.0
            
            # Get price per unit
            price_record = db.query(ProductPrice).filter(
                ProductPrice.product_id == product.id,
                ProductPrice.effective_date <= target_date,
                (ProductPrice.end_date.is_(None) | (ProductPrice.end_date >= target_date))
            ).order_by(ProductPrice.effective_date.desc()).first()
            
            price_per_unit = price_record.price if price_record else 0.0
            
            # Calculate expiry losses (items expiring in 1-3 days that might not sell)
            expiry_buckets = inv.expiry_buckets or {}
            qty_expiring_1_3 = expiry_buckets.get("1_3", 0.0)
            if qty_expiring_1_3 > 0:
                # Estimate 30% won't sell before expiry
                estimated_waste = qty_expiring_1_3 * 0.3
                expiry_loss += estimated_waste * cost_per_unit
                waste_loss += estimated_waste * cost_per_unit
            
            # Calculate markdown losses (if markdowns were applied)
            # This would come from markdown history, simplified for now
            # Assume 20% of expiring items get markdowns at 50% discount
            if qty_expiring_1_3 > 0:
                markdown_qty = qty_expiring_1_3 * 0.2
                discount_percent = 50.0
                revenue_lost = markdown_qty * price_per_unit * (discount_percent / 100)
                markdown_loss += revenue_lost
        
        total_loss = waste_loss + markdown_loss + expiry_loss
        
        return {
            "waste_loss": round(waste_loss, 2),
            "markdown_loss": round(markdown_loss, 2),
            "expiry_loss": round(expiry_loss, 2),
            "total_loss": round(total_loss, 2),
            "date": target_date.isoformat()
        }
    
    def get_losses_for_period(
        self,
        store_id: str,
        start_date: date,
        end_date: date,
        db: Session,
        loss_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get losses for a date range.
        
        Args:
            store_id: Store identifier
            start_date: Start date
            end_date: End date
            db: Database session
            loss_type: Optional filter by loss type
            
        Returns:
            List of loss records
        """
        query = db.query(Loss).filter(
            Loss.store_id == int(store_id),
            Loss.loss_date >= start_date,
            Loss.loss_date <= end_date
        )
        
        if loss_type:
            query = query.filter(Loss.loss_type == loss_type)
        
        losses = query.order_by(Loss.loss_date.desc()).all()
        
        return [
            {
                "id": loss.id,
                "store_id": loss.store_id,
                "product_id": loss.product_id,
                "loss_date": loss.loss_date.isoformat(),
                "loss_type": loss.loss_type,
                "quantity": loss.quantity,
                "cost": loss.cost,
                "revenue_lost": loss.revenue_lost,
                "created_at": loss.created_at.isoformat()
            }
            for loss in losses
        ]
    
    def create_loss_record(
        self,
        store_id: str,
        product_id: Optional[int],
        loss_date: date,
        loss_type: str,
        quantity: float,
        cost: float,
        revenue_lost: float,
        db: Session
    ) -> Loss:
        """Create a loss record."""
        loss = Loss(
            store_id=int(store_id),
            product_id=product_id,
            loss_date=loss_date,
            loss_type=loss_type,
            quantity=quantity,
            cost=cost,
            revenue_lost=revenue_lost
        )
        db.add(loss)
        db.commit()
        db.refresh(loss)
        return loss


def get_loss_service() -> LossService:
    """Get or create the global LossService singleton."""
    global _loss_service_instance
    if '_loss_service_instance' not in globals():
        _loss_service_instance = LossService()
    return _loss_service_instance


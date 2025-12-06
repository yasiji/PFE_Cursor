"""Store-specific routes for products, inventory, stats, and sales."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from services.api_gateway.database import get_db
from services.api_gateway.models import Store, Product, InventorySnapshot, Forecast, Recommendation, User
from services.api_gateway.auth import get_current_user
from services.api_gateway.sales_data_service import get_sales_service
from services.api_gateway.price_service import get_product_price
from services.api_gateway.profit_service import calculate_store_profit, calculate_product_profit
from services.api_gateway.forecast_accuracy_service import calculate_forecast_accuracy, get_product_forecast_accuracy
from services.api_gateway.top_products_service import get_top_products
from services.api_gateway.forecast_insights_service import get_forecast_insights
from services.api_gateway.sales_patterns_service import get_sales_patterns
from shared.logging_setup import get_logger

# ForecastingService will be imported locally where needed to avoid circular imports

logger = get_logger(__name__)


def _generate_recommendations(db: Session, store_id: int, target_date: date) -> List:
    """
    Generate recommendations based on current inventory state.
    
    Creates recommendations for:
    - Low stock items (need to order)
    - Expiring items (need markdown)
    """
    from services.api_gateway.models import InventorySnapshot, Product, Recommendation
    
    recommendations = []
    
    # Get today's inventory
    inventory_snapshots = db.query(InventorySnapshot).filter(
        InventorySnapshot.store_id == store_id,
        InventorySnapshot.snapshot_date == target_date
    ).all()
    
    for inv in inventory_snapshots:
        product = db.query(Product).filter(Product.id == inv.product_id).first()
        if not product:
            continue
        
        backroom_qty = inv.backroom_quantity or 0
        shelf_qty = inv.shelf_quantity or 0
        days_until_exp = inv.days_until_expiry if inv.days_until_expiry else 30
        forecasted_demand = (shelf_qty + backroom_qty) * 0.25  # 25% daily turnover estimate
        
        # Create ORDER recommendation if backroom is low
        if backroom_qty < forecasted_demand * 3:  # Less than 3 days of stock
            order_qty = max(30, int(forecasted_demand * 7))
            rec = Recommendation(
                store_id=store_id,
                product_id=product.id,
                recommendation_date=target_date,
                order_quantity=float(order_qty),
                status="pending"
            )
            db.add(rec)
            recommendations.append(rec)
        
        # Create MARKDOWN recommendation if expiring soon
        if days_until_exp <= 3 and inv.quantity > 0:
            if days_until_exp <= 1:
                discount = 50.0
            elif days_until_exp <= 2:
                discount = 35.0
            else:
                discount = 25.0
            
            rec = Recommendation(
                store_id=store_id,
                product_id=product.id,
                recommendation_date=target_date,
                order_quantity=0.0,
                markdown_discount_percent=discount,
                markdown_effective_date=target_date,
                markdown_reason=f"Expiring in {days_until_exp} day(s)",
                status="pending"
            )
            db.add(rec)
            recommendations.append(rec)
    
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Error saving generated recommendations: {e}")
        db.rollback()
    
    return recommendations

router = APIRouter(prefix="/api/v1/stores", tags=["stores"])


# Response Models
class ProductResponse(BaseModel):
    """Product response model."""
    sku_id: str
    name: Optional[str]
    category: Optional[str]
    price: float = 0.0
    current_stock: float = 0.0
    items_sold_today: int = 0
    items_sold_week: int = 0
    items_sold_month: int = 0
    expiry_date: Optional[str] = None
    days_until_expiry: Optional[int] = None
    items_on_shelves: float = 0.0
    items_to_preorder: int = 0
    items_discarded: int = 0
    status: str = "normal"

    class Config:
        from_attributes = True


class InventoryItemResponse(BaseModel):
    """Inventory item response."""
    sku_id: str
    name: str
    category: Optional[str]
    current_quantity: float  # Total quantity (shelf + backroom) - kept for backward compatibility
    shelf_quantity: float = 0.0  # Quantity on display shelves
    backroom_quantity: float = 0.0  # Quantity in backroom/warehouse
    total_quantity: float = 0.0  # Computed: shelf_quantity + backroom_quantity
    expiry_date: Optional[str]
    days_until_expiry: Optional[int]
    quantity_expiring_1_3_days: float = 0.0
    quantity_expiring_4_7_days: float = 0.0
    quantity_expiring_8_plus_days: float = 0.0
    in_transit: float = 0.0
    to_be_discarded: float = 0.0
    status: str = "normal"

    class Config:
        from_attributes = True


class StoreStatsResponse(BaseModel):
    """Store statistics response."""
    sales_today: float = 0.0
    revenue_today: float = 0.0
    profit_today: float = 0.0
    margin_percent: float = 0.0
    items_sold: int = 0
    items_on_shelves: int = 0  # Total items on shelves
    items_in_stock: int = 0  # Total items in backroom/warehouse
    total_items: int = 0  # Total items (shelf + stock)
    items_expiring: int = 0
    low_stock_items: int = 0
    empty_shelves: int = 0
    losses_today: Dict[str, float] = {}  # waste_loss, markdown_loss, total_loss


class SalesDataResponse(BaseModel):
    """Sales data response."""
    date: str
    sales: float
    forecast: float = 0.0
    revenue: float
    profit: float = 0.0
    margin_percent: float = 0.0


class ForecastAccuracyResponse(BaseModel):
    """Forecast accuracy response."""
    mae: float = 0.0
    mape: float = 0.0
    wape: float = 0.0
    bias: float = 0.0
    sample_size: int = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    error: Optional[str] = None


class TopProductResponse(BaseModel):
    """Top product response."""
    sku_id: str
    name: str
    category: Optional[str] = None
    sales_volume: float = 0.0
    revenue: float = 0.0
    profit: float = 0.0
    margin_percent: float = 0.0
    growth_rate: float = 0.0
    price: float = 0.0


class ForecastInsightItem(BaseModel):
    """Single forecast insight item."""
    type: str
    title: str
    message: str
    severity: str


class ForecastPeriodResponse(BaseModel):
    """Forecast period response."""
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    forecasted_items: int = 0
    forecasted_sales: float = 0.0
    forecasted_revenue: float = 0.0
    forecasted_profit: float = 0.0
    forecasted_margin: float = 0.0
    daily_avg_items: int = 0
    daily_avg_sales: float = 0.0
    daily_avg_revenue: float = 0.0
    daily_avg_profit: float = 0.0
    daily_avg_margin: float = 0.0


class ForecastInsightsResponse(BaseModel):
    """Forecast insights response."""
    tomorrow: ForecastPeriodResponse
    next_week: ForecastPeriodResponse
    next_month: ForecastPeriodResponse
    insights: List[ForecastInsightItem]
    error: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Recommendation response."""
    id: int
    sku_id: str
    name: str
    order_quantity: float
    current_stock: float
    forecasted_demand: float
    markdown: Optional[Dict] = None
    status: str
    confidence: float = 0.85


class RefillItemResponse(BaseModel):
    """Refill item response."""
    sku_id: str
    product_name: str
    category: Optional[str] = "General"
    current_shelf_quantity: float
    current_backroom_quantity: float
    total_quantity: float = 0.0
    forecasted_demand_tomorrow: float
    recommended_shelf_quantity: float
    refill_quantity: float  # How much to move from backroom to shelf
    order_quantity: float  # How much to order (if needed)
    in_transit_quantity: float
    expected_arrival_date: Optional[str] = None
    transit_days: int = 0
    days_until_expiry: Optional[int] = None
    expiry_date: Optional[str] = None
    expiry_buckets: Optional[Dict[str, float]] = None
    needs_attention: bool = False
    factors: Dict[str, Any]  # weather, day_of_week, holiday, etc.


class RefillPlanResponse(BaseModel):
    """Refill plan response."""
    store_id: str
    target_date: str
    total_items_to_refill: int
    total_items_to_order: int
    total_in_transit: int
    refill_items: List[RefillItemResponse]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DailyForecastResponse(BaseModel):
    """Daily forecast response."""
    date: str
    predicted_demand: float
    predicted_revenue: float
    predicted_profit: float
    predicted_loss: float
    net_profit: float
    predicted_margin: float
    factors: Dict[str, Any]


class ExtendedForecastResponse(BaseModel):
    """Extended 30-day forecast response."""
    store_id: str
    forecast_period: str
    daily_forecasts: List[DailyForecastResponse]
    summary: Dict[str, float]


@router.get("/{store_id}/products", response_model=List[ProductResponse])
async def get_store_products(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all products for a store with current inventory and sales data.
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this store's products")
        
        # Get latest inventory snapshot (try today first, then most recent)
        today = date.today()
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == today
        ).all()
        
        # If no snapshot for today, get the most recent one
        if not inventory_snapshots:
            latest_snapshot = db.query(InventorySnapshot).filter(
                InventorySnapshot.store_id == int(store_id)
            ).order_by(InventorySnapshot.snapshot_date.desc()).first()
            
            if latest_snapshot:
                inventory_snapshots = db.query(InventorySnapshot).filter(
                    InventorySnapshot.store_id == int(store_id),
                    InventorySnapshot.snapshot_date == latest_snapshot.snapshot_date
                ).all()
                logger.info(f"Using product inventory from {latest_snapshot.snapshot_date} (no data for today)")
        
        # Create inventory map
        inventory_map = {inv.product_id: inv for inv in inventory_snapshots}
        
        # Get products that have inventory records (for data consistency)
        product_ids_with_inventory = set(inventory_map.keys())
        products = db.query(Product).filter(Product.id.in_(product_ids_with_inventory)).limit(100).all()
        
        # If no products with inventory, fall back to all products
        if not products:
            products = db.query(Product).limit(100).all()
        
        # Get sales data service
        sales_service = get_sales_service()
        
        # Build response
        result = []
        for product in products:
            inv = inventory_map.get(product.id)
            
            # Get real sales data for this product
            sales_stats = sales_service.get_product_sales(
                store_id=store_id,
                sku_id=product.sku_id,
                start_date=today - timedelta(days=30),
                end_date=today
            )
            
            # Get items_sold_today - prefer inventory.sold_today if available
            items_sold_today = sales_stats['items_sold_today']
            
            # First check if inventory has sold_today field
            if inv and hasattr(inv, 'sold_today') and inv.sold_today is not None and inv.sold_today > 0:
                items_sold_today = int(inv.sold_today)
            elif items_sold_today == 0 and sales_service.latest_date and today > sales_service.latest_date:
                # Use forecast for today - use singleton
                from services.api_gateway.services import get_forecasting_service
                forecasting_service = get_forecasting_service()
                try:
                    forecasts = forecasting_service.forecast(
                        store_id=store_id,
                        sku_id=product.sku_id,
                        horizon_days=1,
                        include_uncertainty=False
                    )
                    if forecasts and len(forecasts) > 0:
                        items_sold_today = int(forecasts[0].get('predicted_demand', 0.0))
                except Exception as e:
                    logger.warning(f"Error forecasting for product {product.sku_id}: {e}")
            
            # Get product price from database
            price = get_product_price(db, sku_id=product.sku_id)
            
            # Get recommendation for pre-order (from Recommendation table)
            recommendation = db.query(Recommendation).filter(
                Recommendation.store_id == int(store_id),
                Recommendation.product_id == product.id,
                Recommendation.recommendation_date == today,
                Recommendation.status == "pending"
            ).first()
            
            items_to_preorder = int(recommendation.order_quantity) if recommendation else 0
            
            # Calculate expiry date from inventory expiry buckets
            expiry_date = None
            days_until_expiry = None
            if inv and inv.expiry_buckets:
                # Calculate earliest expiry date from buckets
                # Assume items in 1_3 bucket expire in 2 days, 4_7 in 5 days, 8_plus in 10 days
                if inv.expiry_buckets.get("1_3", 0) > 0:
                    days_until_expiry = 2
                elif inv.expiry_buckets.get("4_7", 0) > 0:
                    days_until_expiry = 5
                elif inv.expiry_buckets.get("8_plus", 0) > 0:
                    days_until_expiry = 10
                
                if days_until_expiry:
                    expiry_date = (today + timedelta(days=days_until_expiry)).isoformat()
            
            # Determine status
            if inv and inv.quantity < 10:
                status = "low_stock"
            elif inv and inv.expiry_buckets and inv.expiry_buckets.get("1_3", 0) > 0:
                status = "expiring"
            else:
                status = "normal"
            
            # Calculate total stock (shelf + backroom)
            if inv:
                shelf_qty = inv.shelf_quantity if inv.shelf_quantity else 0.0
                backroom_qty = inv.backroom_quantity if inv.backroom_quantity else 0.0
                total_stock = shelf_qty + backroom_qty
            else:
                shelf_qty = 0.0
                backroom_qty = 0.0
                total_stock = 0.0
            
            result.append(ProductResponse(
                sku_id=product.sku_id,
                name=product.name or f"Product {product.sku_id}",
                category=product.category or "General",
                price=price,
                current_stock=total_stock,
                items_sold_today=items_sold_today,
                items_sold_week=sales_stats['items_sold_week'],
                items_sold_month=sales_stats['items_sold_month'],
                expiry_date=inv.expiry_date.isoformat() if inv and inv.expiry_date else expiry_date,
                days_until_expiry=inv.days_until_expiry if inv and inv.days_until_expiry is not None else days_until_expiry,
                items_on_shelves=shelf_qty,
                items_to_preorder=items_to_preorder,
                items_discarded=int(inv.to_discard) if inv and inv.to_discard else 0,
                status=status
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error getting store products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving products"
        )


@router.get("/{store_id}/inventory", response_model=List[InventoryItemResponse])
async def get_store_inventory(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current inventory for a store with expiry tracking."""
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this store's inventory")
        
        # Get the most recent inventory snapshot (not just today's, in case data wasn't updated today)
        today = date.today()
        # First try today's snapshot
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == today
        ).all()
        
        # If no snapshot for today, get the most recent one
        if not inventory_snapshots:
            latest_snapshot = db.query(InventorySnapshot).filter(
                InventorySnapshot.store_id == int(store_id)
            ).order_by(InventorySnapshot.snapshot_date.desc()).first()
            
            if latest_snapshot:
                # Get all snapshots for that date
                inventory_snapshots = db.query(InventorySnapshot).filter(
                    InventorySnapshot.store_id == int(store_id),
                    InventorySnapshot.snapshot_date == latest_snapshot.snapshot_date
                ).all()
                logger.info(f"Using inventory snapshot from {latest_snapshot.snapshot_date} (no data for today)")
        
        result = []
        for inv in inventory_snapshots:
            product = db.query(Product).filter(Product.id == inv.product_id).first()
            if not product:
                continue
            
            # Parse expiry buckets if available
            expiry_buckets = inv.expiry_buckets or {}
            qty_1_3 = expiry_buckets.get("1_3", 0.0)
            qty_4_7 = expiry_buckets.get("4_7", 0.0)
            qty_8_plus = expiry_buckets.get("8_plus", 0.0)
            
            # Determine status
            if qty_1_3 > 0:
                status = "expiring"
            elif inv.quantity < 10:
                status = "low_stock"
            else:
                status = "normal"
            
            # Get shelf and backroom quantities (default to splitting existing quantity if not set)
            shelf_qty = getattr(inv, 'shelf_quantity', None)
            backroom_qty = getattr(inv, 'backroom_quantity', None)
            
            # If shelf/backroom not set, split existing quantity (70% shelf, 30% backroom as default)
            if shelf_qty is None or backroom_qty is None:
                if inv.quantity > 0:
                    shelf_qty = round(inv.quantity * 0.7, 2)  # Default: 70% on shelf
                    backroom_qty = round(inv.quantity * 0.3, 2)  # Default: 30% in backroom
                else:
                    shelf_qty = 0.0
                    backroom_qty = 0.0
            
            total_qty = shelf_qty + backroom_qty
            
            # Get actual expiry date and days from inventory
            expiry_date_str = None
            days_until_exp = None
            if hasattr(inv, 'expiry_date') and inv.expiry_date:
                expiry_date_str = inv.expiry_date.isoformat()
                days_until_exp = (inv.expiry_date - today).days
            elif hasattr(inv, 'days_until_expiry') and inv.days_until_expiry is not None:
                days_until_exp = inv.days_until_expiry
                expiry_date_str = (today + timedelta(days=inv.days_until_expiry)).isoformat()
            
            # Get in_transit and to_discard from inventory
            in_transit = getattr(inv, 'in_transit', 0.0) or 0.0
            to_discard = getattr(inv, 'to_discard', 0.0) or 0.0
            
            result.append(InventoryItemResponse(
                sku_id=product.sku_id,
                name=product.name or f"Product {product.sku_id}",
                category=product.category or "General",
                current_quantity=inv.quantity,  # Keep for backward compatibility
                shelf_quantity=shelf_qty,
                backroom_quantity=backroom_qty,
                total_quantity=total_qty,
                expiry_date=expiry_date_str,
                days_until_expiry=days_until_exp,
                quantity_expiring_1_3_days=qty_1_3,
                quantity_expiring_4_7_days=qty_4_7,
                quantity_expiring_8_plus_days=qty_8_plus,
                in_transit=in_transit,
                to_be_discarded=to_discard,
                status=status
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error getting store inventory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving inventory"
        )


@router.get("/{store_id}/refill-plan", response_model=RefillPlanResponse)
async def get_refill_plan(
    store_id: str,
    target_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get refill plan for a store (how much to refill shelves for tomorrow).
    
    Shows exactly how much to move from backroom to shelves based on forecast,
    current inventory, and transit time.
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this store's refill plan"
            )
        
        # Parse target date (default to tomorrow)
        if target_date:
            target_date_obj = date.fromisoformat(target_date)
        else:
            target_date_obj = date.today() + timedelta(days=1)
        
        # Get refill service
        from services.api_gateway.refill_service import get_refill_service
        refill_service = get_refill_service()
        
        # Calculate refill plan
        refill_items = refill_service.calculate_refill_plan(
            store_id=store_id,
            target_date=target_date_obj,
            db=db
        )
        
        # Calculate summary statistics
        total_refill = sum(item['refill_quantity'] for item in refill_items)
        total_order = sum(item['order_quantity'] for item in refill_items)
        total_in_transit = sum(item['in_transit_quantity'] for item in refill_items)
        
        # Convert to response format
        refill_items_response = [
            RefillItemResponse(**item) for item in refill_items
        ]
        
        return RefillPlanResponse(
            store_id=store_id,
            target_date=target_date_obj.isoformat(),
            total_items_to_refill=int(total_refill),
            total_items_to_order=int(total_order),
            total_in_transit=int(total_in_transit),
            refill_items=refill_items_response
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}"
        )
    except Exception as e:
        logger.error(f"Error getting refill plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving refill plan"
        )


@router.get("/{store_id}/forecast-extended", response_model=ExtendedForecastResponse)
async def get_extended_forecast(
    store_id: str,
    category: Optional[str] = None,
    product: Optional[str] = None,
    horizon_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get 30-day day-by-day forecast with revenue, profit, and loss breakdown.
    
    Returns detailed daily forecasts showing:
    - Predicted demand
    - Predicted revenue
    - Predicted profit
    - Predicted loss (from waste/expiry)
    - Net profit (profit - loss)
    - Margin percentage
    - Factors affecting each day (weather, day of week, holiday)
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this store's forecast"
            )
        
        # Get extended forecast service
        from services.api_gateway.extended_forecast_service import get_extended_forecast_service
        extended_service = get_extended_forecast_service()
        
        # Generate forecast (limit to 30 days for performance)
        horizon_days = min(max(horizon_days, 1), 30)  # Clamp between 1 and 30
        forecast_data = extended_service.generate_30_day_forecast(
            store_id=store_id,
            db=db,
            category_filter=category,
            product_filter=product,
            horizon_days=horizon_days
        )
        
        # Convert to response format
        daily_forecasts = [
            DailyForecastResponse(**f) for f in forecast_data['daily_forecasts']
        ]
        
        return ExtendedForecastResponse(
            store_id=forecast_data['store_id'],
            forecast_period=forecast_data['forecast_period'],
            daily_forecasts=daily_forecasts,
            summary=forecast_data['summary']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extended forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving extended forecast"
        )


@router.get("/{store_id}/stats", response_model=StoreStatsResponse)
async def get_store_stats(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get store statistics and KPIs."""
    try:
        today = date.today()
        
        # Get inventory snapshots
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == today
        ).all()
        
        # Calculate stats with shelf/backroom separation
        total_shelf = 0.0
        total_backroom = 0.0
        total_stock = 0.0
        
        for inv in inventory_snapshots:
            shelf_qty = getattr(inv, 'shelf_quantity', None)
            backroom_qty = getattr(inv, 'backroom_quantity', None)
            
            if shelf_qty is not None and backroom_qty is not None:
                total_shelf += shelf_qty
                total_backroom += backroom_qty
                total_stock += shelf_qty + backroom_qty
            else:
                # Fallback: split existing quantity
                if inv.quantity > 0:
                    shelf_qty = inv.quantity * 0.7
                    backroom_qty = inv.quantity * 0.3
                    total_shelf += shelf_qty
                    total_backroom += backroom_qty
                total_stock += inv.quantity
        
        low_stock_count = sum(1 for inv in inventory_snapshots if inv.quantity < 10)
        expiring_count = sum(
            1 for inv in inventory_snapshots
            if inv.expiry_buckets and inv.expiry_buckets.get("1_3", 0) > 0
        )
        
        # Get sales service
        sales_service = get_sales_service()
        
        # Use singleton forecasting service
        from services.api_gateway.services import get_forecasting_service
        forecasting_service = get_forecasting_service()
        
        # Check if today is in the dataset
        today = date.today()
        if sales_service.latest_date and today > sales_service.latest_date:
            # Today is in the future - use FORECAST instead of historical data
            logger.info(f"Today ({today}) is after dataset latest date ({sales_service.latest_date}), using forecast")
            
            # Get forecast for today by aggregating forecasts for sample products
            products = db.query(Product).limit(5).all()  # Reduced to 5 for performance
            total_forecasted_sales = 0.0
            total_forecasted_items = 0
            
            for product in products[:3]:  # Use only 3 products for faster response
                try:
                    forecasts = forecasting_service.forecast(
                        store_id=store_id,
                        sku_id=product.sku_id,
                        horizon_days=1,
                        include_uncertainty=False
                    )
                    if forecasts and len(forecasts) > 0:
                        forecast_value = forecasts[0].get('predicted_demand', 0.0)
                        total_forecasted_sales += forecast_value
                        total_forecasted_items += int(forecast_value)
                except Exception as e:
                    logger.warning(f"Error forecasting for product {product.sku_id}: {e}")
                    continue
            
            # Scale up based on sample (estimate for all products)
            if len(products) > 0:
                total_products = db.query(Product).count()
                if total_products > len(products):
                    scale_factor = total_products / max(len(products), 1)
                    total_forecasted_sales *= scale_factor
                    total_forecasted_items = int(total_forecasted_items * scale_factor)
            
            # Calculate revenue from forecast using average price
            from services.api_gateway.price_service import get_average_price_for_store
            avg_price = get_average_price_for_store(db, store_id=store_id)
            forecasted_revenue = total_forecasted_sales * avg_price
            
            # Calculate profit for forecast
            forecast_profit_data = calculate_store_profit(
                db=db,
                store_id=store_id,
                revenue=forecasted_revenue,
                items_sold=total_forecasted_items,
                target_date=today
            )
            
            sales_stats = {
                'sales_today': total_forecasted_sales,
                'revenue_today': forecasted_revenue,
                'items_sold': total_forecasted_items,
                'profit_today': forecast_profit_data['profit'],
                'margin_percent': forecast_profit_data['margin_percent']
            }
        else:
            # Today is in dataset - use historical data
            sales_stats = sales_service.get_store_stats(store_id=store_id, target_date=today)
        
        # Calculate profit and margin (if not already calculated for forecast case)
        if 'profit_today' not in sales_stats:
            profit_data = calculate_store_profit(
                db=db,
                store_id=store_id,
                revenue=sales_stats['revenue_today'],
                items_sold=sales_stats['items_sold'],
                target_date=today
            )
            profit_today = profit_data['profit']
            margin_percent = profit_data['margin_percent']
        else:
            profit_today = sales_stats['profit_today']
            margin_percent = sales_stats['margin_percent']
        
        # Calculate losses for today
        from services.api_gateway.loss_service import get_loss_service
        loss_service = get_loss_service()
        losses = loss_service.calculate_daily_losses(
            store_id=store_id,
            target_date=today,
            db=db
        )
        
        return StoreStatsResponse(
            sales_today=sales_stats['sales_today'],
            revenue_today=sales_stats['revenue_today'],
            profit_today=profit_today,
            margin_percent=margin_percent,
            items_sold=sales_stats['items_sold'],
            items_on_shelves=int(total_shelf),
            items_in_stock=int(total_backroom),
            total_items=int(total_stock),
            items_expiring=expiring_count,
            low_stock_items=low_stock_count,
            empty_shelves=0,  # Would come from shelf tracking
            losses_today={
                "waste_loss": losses.get("waste_loss", 0.0),
                "markdown_loss": losses.get("markdown_loss", 0.0),
                "expiry_loss": losses.get("expiry_loss", 0.0),
                "total_loss": losses.get("total_loss", 0.0)
            }
        )
    except Exception as e:
        logger.error(f"Error getting store stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving store statistics"
        )


@router.get("/{store_id}/losses", response_model=List[Dict])
async def get_store_losses(
    store_id: str,
    start_date: str,
    end_date: str,
    loss_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get losses for a store within a date range.
    
    Args:
        store_id: Store identifier
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        loss_type: Optional filter by loss type (waste, expiry, markdown)
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        # Authorization check
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this store's losses"
            )
        
        start_date_obj = date.fromisoformat(start_date)
        end_date_obj = date.fromisoformat(end_date)
        
        from services.api_gateway.loss_service import get_loss_service
        loss_service = get_loss_service()
        
        losses = loss_service.get_losses_for_period(
            store_id=store_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            db=db,
            loss_type=loss_type
        )
        
        return losses
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting store losses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving losses"
        )


@router.get("/{store_id}/sales", response_model=List[SalesDataResponse])
async def get_store_sales(
    store_id: str,
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sales data for a store within a date range.
    Returns real data from FreshRetailNet-50K dataset.
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this store's sales data")

        # Parse dates
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        original_end = end_dt  # Store original for forecast generation
        
        # Get real sales data
        sales_service = get_sales_service()
        
        # Store original date range for forecast generation
        historical_end = end_dt
        
        # Adjust date range for historical data (but keep original for forecasts)
        if sales_service.latest_date:
            if start_dt > sales_service.latest_date:
                # If start date is after dataset, use last period from dataset
                historical_end = sales_service.latest_date
                period_days = (end_dt - start_dt).days
                start_dt = historical_end - timedelta(days=min(period_days, 90))
                logger.info(f"Adjusted historical date range to dataset range: {start_dt} to {historical_end}")
            elif end_dt > sales_service.latest_date:
                # If end date is after dataset, cap historical data at latest date
                historical_end = sales_service.latest_date
                # Adjust start to maintain requested period
                period_days = (end_dt - start_dt).days
                start_dt = historical_end - timedelta(days=min(period_days, 90))
                logger.info(f"Adjusted historical date range to dataset range: {start_dt} to {historical_end}")
        
        # Get historical sales data
        sales_data = sales_service.get_store_sales(
            store_id=store_id,
            start_date=start_dt,
            end_date=historical_end
        )
        
        # Use singleton forecasting service for future dates
        from services.api_gateway.services import get_forecasting_service
        forecasting_service = get_forecasting_service()
        
        # Convert to response format
        result = []
        today = date.today()
        
        # Process historical data
        for item in sales_data:
            item_date = item['date'] if isinstance(item['date'], date) else date.fromisoformat(str(item['date']))
            
            # Get forecast for this date if available in DB
            forecast = db.query(Forecast).filter(
                Forecast.store_id == int(store_id),
                Forecast.target_date == item_date
            ).first()
            
            forecast_value = forecast.predicted_demand if forecast else item['sales'] * 0.95
            
            # Recalculate revenue using actual average price
            from services.api_gateway.price_service import get_average_price_for_store
            avg_price = get_average_price_for_store(db, store_id=store_id, target_date=item_date)
            actual_revenue = item['sales'] * avg_price
            
            # Calculate profit for this day
            daily_profit_data = calculate_store_profit(
                db=db,
                store_id=store_id,
                revenue=actual_revenue,
                items_sold=item['items_sold'],
                target_date=item_date
            )
            
            result.append(SalesDataResponse(
                date=item_date.isoformat(),
                sales=item['sales'],
                forecast=forecast_value,
                revenue=actual_revenue,
                profit=daily_profit_data['profit'],
                margin_percent=daily_profit_data['margin_percent']
            ))
        
        # If original end_date is in the future, add forecasts for future dates
        if original_end > today and original_end > (sales_service.latest_date if sales_service.latest_date else today):
            # Get a sample product to generate store-level forecast
            products = db.query(Product).limit(5).all()
            
            # Generate forecasts for each future date
            # Start from the day after latest dataset date or today, whichever is later
            forecast_start = max(today + timedelta(days=1), (sales_service.latest_date + timedelta(days=1)) if sales_service.latest_date else today + timedelta(days=1))
            forecast_dates = []
            temp_date = forecast_start
            while temp_date <= original_end:
                forecast_dates.append(temp_date)
                temp_date += timedelta(days=1)
            
            # Aggregate forecasts across products for each date
            for forecast_date in forecast_dates:
                daily_forecast = 0.0
                for product in products:
                    try:
                        # Calculate days ahead from latest dataset date or today
                        base_date = sales_service.latest_date if sales_service.latest_date else today
                        days_ahead = (forecast_date - base_date).days
                        if days_ahead > 0:
                            forecasts = forecasting_service.forecast(
                                store_id=store_id,
                                sku_id=product.sku_id,
                                horizon_days=min(days_ahead, 14),
                                include_uncertainty=False
                            )
                            if forecasts and len(forecasts) >= days_ahead:
                                daily_forecast += forecasts[days_ahead - 1].get('predicted_demand', 0.0)
                    except Exception as e:
                        logger.warning(f"Error forecasting for {product.sku_id} on {forecast_date}: {e}")
                        continue
                
                # Add forecast entry
                from services.api_gateway.price_service import get_average_price_for_store
                avg_price = get_average_price_for_store(db, store_id=store_id)
                forecast_revenue = daily_forecast * avg_price
                
                # Calculate profit for forecast
                forecast_profit_data = calculate_store_profit(
                    db=db,
                    store_id=store_id,
                    revenue=forecast_revenue,
                    items_sold=int(daily_forecast),
                    target_date=forecast_date
                )
                
                result.append(SalesDataResponse(
                    date=forecast_date.isoformat(),
                    sales=0.0,  # No actual sales for future dates
                    forecast=daily_forecast,
                    revenue=forecast_revenue,
                    profit=forecast_profit_data['profit'],
                    margin_percent=forecast_profit_data['margin_percent']
                ))
        
        # Sort by date
        result.sort(key=lambda x: x.date)
        
        return result
    except Exception as e:
        logger.error(f"Error getting store sales: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving sales data"
        )


@router.get("/{store_id}/forecast-accuracy", response_model=ForecastAccuracyResponse)
async def get_forecast_accuracy(
    store_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get forecast accuracy metrics for a store.
    
    Compares forecasts with actual sales over the specified number of days.
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
        # Calculate accuracy
        accuracy = calculate_forecast_accuracy(
            db=db,
            store_id=store_id,
            days=days
        )
        
        return ForecastAccuracyResponse(**accuracy)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating forecast accuracy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating forecast accuracy"
        )


@router.get("/{store_id}/top-products", response_model=List[TopProductResponse])
async def get_top_products_endpoint(
    store_id: str,
    limit: int = 10,
    sort_by: str = "sales_volume",
    period_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top products for a store.
    
    Sort options: sales_volume, revenue, profit, growth
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
        # Validate sort_by
        valid_sorts = ["sales_volume", "revenue", "profit", "growth"]
        if sort_by not in valid_sorts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"sort_by must be one of: {', '.join(valid_sorts)}"
            )
        
        # Get top products
        top_products = get_top_products(
            db=db,
            store_id=store_id,
            limit=limit,
            sort_by=sort_by,
            period_days=period_days
        )
        
        return [TopProductResponse(**p) for p in top_products]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving top products"
        )


@router.get("/{store_id}/forecast-insights", response_model=ForecastInsightsResponse)
async def get_forecast_insights_endpoint(
    store_id: str,
    horizon_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get forecast insights for a store.
    
    Provides tomorrow's forecast, next week forecast, next month forecast,
    and key insights about demand trends and profitability.
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
        # Get forecast insights
        insights = get_forecast_insights(
            db=db,
            store_id=store_id,
            horizon_days=horizon_days
        )
        
        # Convert to response models
        return ForecastInsightsResponse(
            tomorrow=ForecastPeriodResponse(**insights.get('tomorrow', {})),
            next_week=ForecastPeriodResponse(**insights.get('next_week', {})),
            next_month=ForecastPeriodResponse(**insights.get('next_month', {})),
            insights=[ForecastInsightItem(**i) for i in insights.get('insights', [])],
            error=insights.get('error')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting forecast insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving forecast insights"
        )


@router.get("/{store_id}/sales-patterns")
async def get_sales_patterns_endpoint(
    store_id: str,
    period_days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sales pattern analysis for a store.
    
    Analyzes patterns by:
    - Day of week
    - Weather conditions
    - Holidays (if data available)
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
        # Get sales patterns
        patterns = get_sales_patterns(
            db=db,
            store_id=store_id,
            period_days=period_days
        )
        
        return patterns
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sales patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving sales patterns"
        )


@router.get("/{store_id}/recommendations", response_model=List[RecommendationResponse])
async def get_store_recommendations(
    store_id: str,
    status: Optional[str] = "pending",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get order and markdown recommendations for a store.
    
    Returns pending recommendations by default, but can filter by status.
    Includes both order recommendations (for low stock) and markdown recommendations (for expiring items).
    """
    try:
        # Ensure the store exists
        store = db.query(Store).filter(Store.id == int(store_id)).first()
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
        if current_user.role == "store_manager" and current_user.store_id != int(store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
        today = date.today()
        
        # Get recommendations for today and upcoming days
        query = db.query(Recommendation).filter(
            Recommendation.store_id == int(store_id),
            Recommendation.recommendation_date >= today - timedelta(days=1),  # Include yesterday's pending
            Recommendation.recommendation_date <= today + timedelta(days=7)   # Include next week
        )
        
        if status:
            query = query.filter(Recommendation.status == status)
        
        recommendations = query.all()
        
        # If no recommendations exist, generate them on the fly
        if not recommendations:
            logger.info(f"No recommendations found for store {store_id}, generating...")
            recommendations = _generate_recommendations(db, int(store_id), today)
        
        # Get inventory for current stock
        inventory_snapshots = db.query(InventorySnapshot).filter(
            InventorySnapshot.store_id == int(store_id),
            InventorySnapshot.snapshot_date == today
        ).all()
        inventory_map = {inv.product_id: inv for inv in inventory_snapshots}
        
        # Get forecasts for forecasted_demand using singleton
        from services.api_gateway.services import get_forecasting_service
        forecasting_service = get_forecasting_service()
        
        result = []
        for rec in recommendations:
            product = db.query(Product).filter(Product.id == rec.product_id).first()
            if not product:
                continue
            
            inv = inventory_map.get(rec.product_id)
            current_stock = inv.quantity if inv else 0.0
            
            # Get forecast for this product
            try:
                forecasts = forecasting_service.forecast(
                    store_id=store_id,
                    sku_id=product.sku_id,
                    horizon_days=7,
                    include_uncertainty=False
                )
                forecasted_demand = sum(f.get('predicted_demand', 0.0) for f in forecasts) if forecasts else rec.order_quantity
            except:
                forecasted_demand = rec.order_quantity
            
            markdown = None
            if rec.markdown_discount_percent:
                markdown = {
                    'discount_percent': rec.markdown_discount_percent,
                    'effective_date': rec.markdown_effective_date.isoformat() if rec.markdown_effective_date else None,
                    'reason': rec.markdown_reason or 'Near expiry'
                }
            
            result.append(RecommendationResponse(
                id=rec.id,
                sku_id=product.sku_id,
                name=product.name or f"Product {product.sku_id}",
                order_quantity=rec.order_quantity,
                current_stock=current_stock,
                forecasted_demand=forecasted_demand,
                markdown=markdown,
                status=rec.status,
                confidence=0.85  # Could calculate from forecast accuracy
            ))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving recommendations"
        )


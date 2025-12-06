"""Batch job to generate and save replenishment recommendations."""

from datetime import date, datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from services.api_gateway.database import get_db, init_db
from services.api_gateway.models import Store, Product, Recommendation, Forecast
from services.api_gateway.services import ForecastingService, ReplenishmentService
from services.api_gateway.services import load_mvp_data
from shared.config import get_config
from shared.logging_setup import get_logger
from shared.column_mappings import COLUMN_MAPPINGS

logger = get_logger(__name__)
config = get_config()


def generate_recommendations_for_all_stores(
    target_date: date,
    db: Session
) -> int:
    """
    Generate replenishment recommendations for all stores.
    
    Args:
        target_date: Target date for recommendations
        db: Database session
        
    Returns:
        Number of recommendations generated
    """
    logger.info(f"Generating recommendations for date: {target_date}")
    
    # Initialize services
    forecasting_service = ForecastingService()
    replenishment_service = ReplenishmentService()
    
    # Load data
    try:
        df, store_col, sku_col, date_col, sales_col = load_mvp_data()
        
        # Get unique store-SKU combinations
        store_skus = df[[store_col, sku_col]].drop_duplicates()
        
        recommendations_count = 0
        
        # Process each store-SKU combination
        for idx, row in store_skus.iterrows():
            store_id = str(row[store_col])
            sku_id = str(row[sku_col])
            
            try:
                # Generate forecast
                forecasts = forecasting_service.forecast(
                    store_id=store_id,
                    sku_id=sku_id,
                    horizon_days=7,
                    include_uncertainty=False
                )
                
                if not forecasts:
                    continue
                
                # Get average forecasted demand
                avg_forecast = sum(f['predicted_demand'] for f in forecasts) / len(forecasts)
                
                # Get or create store
                store = db.query(Store).filter(Store.store_id == store_id).first()
                if not store:
                    store = Store(store_id=store_id)
                    db.add(store)
                    db.flush()
                
                # Get or create product
                product = db.query(Product).filter(Product.sku_id == sku_id).first()
                if not product:
                    product = Product(sku_id=sku_id)
                    db.add(product)
                    db.flush()
                
                # Calculate order quantity (simplified - would use actual inventory)
                order_qty = max(0, avg_forecast * 7 - 50)  # Simplified calculation
                
                # Check if recommendation already exists
                existing = db.query(Recommendation).filter(
                    Recommendation.store_id == store.id,
                    Recommendation.product_id == product.id,
                    Recommendation.recommendation_date == target_date
                ).first()
                
                if existing:
                    # Update existing recommendation
                    existing.order_quantity = order_qty
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new recommendation
                    recommendation = Recommendation(
                        store_id=store.id,
                        product_id=product.id,
                        recommendation_date=target_date,
                        order_quantity=order_qty,
                        status="pending"
                    )
                    db.add(recommendation)
                    recommendations_count += 1
                
            except Exception as e:
                logger.warning(f"Error processing {store_id}-{sku_id}: {e}")
                continue
        
        # Commit all recommendations
        db.commit()
        logger.info(f"Generated {recommendations_count} recommendations")
        return recommendations_count
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        db.rollback()
        raise


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("BATCH RECOMMENDATION GENERATION")
    print("="*80)
    
    # Initialize database
    init_db()
    
    # Get target date (tomorrow by default)
    target_date = date.today() + timedelta(days=1)
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        count = generate_recommendations_for_all_stores(target_date, db)
        print(f"\n✅ Successfully generated {count} recommendations for {target_date}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()


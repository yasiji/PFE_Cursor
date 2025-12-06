"""
Script to run offline simulation comparing heuristic vs model-based policy.

This script:
1. Loads MVP subset data
2. Simulates heuristic policy (simple rule-based)
3. Simulates model-based policy (LightGBM + order-up-to)
4. Compares results (waste, stockouts, service level)
5. Generates comparison report
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from shared.config import get_config
from shared.logging_setup import setup_logging, get_logger
from shared.column_mappings import COLUMN_MAPPINGS
from services.ingestion.datasets import load_freshretailnet_dataset
from services.forecasting.features.aggregate_daily import aggregate_to_daily
from services.forecasting.models.baseline import MovingAverageForecaster
from services.forecasting.models.lightgbm_model import LightGBMForecaster
from services.forecasting.features.feature_engineering import create_forecast_features
from services.replenishment.policy import OrderUpToPolicy
from services.replenishment.expiry import InventoryAgeTracker
from services.replenishment.markdown import MarkdownPolicy

# Setup
setup_logging()
logger = get_logger(__name__)
config = get_config()


def load_mvp_data():
    """Load MVP subset data."""
    logger.info("Loading MVP subset data")
    
    dataset = load_freshretailnet_dataset()
    df = dataset['train'].to_pandas()
    
    store_col = COLUMN_MAPPINGS.get('store_id', 'store_id')
    sku_col = COLUMN_MAPPINGS.get('sku_id', 'product_id')
    date_col = COLUMN_MAPPINGS.get('date_col', 'dt')
    sales_col = COLUMN_MAPPINGS.get('sales_col', 'sale_amount')
    category_col = COLUMN_MAPPINGS.get('category_col', 'first_category_id')
    
    # Load MVP stores
    mvp_file = Path(config.data.processed_path) / "mvp_selection" / "mvp_subset.txt"
    stores = []
    if mvp_file.exists():
        with open(mvp_file, 'r') as f:
            lines = f.readlines()
        in_stores_section = False
        for line in lines:
            if "Selected Stores" in line:
                in_stores_section = True
                continue
            if in_stores_section and line.strip() and not line.strip().startswith("Selected SKUs"):
                try:
                    stores.append(int(line.strip()))
                except ValueError:
                    pass
            if "Selected SKUs" in line:
                break
    
    if stores:
        df = df[df[store_col].isin(stores)].copy()
    
    if df[date_col].dtype == 'object':
        df[date_col] = pd.to_datetime(df[date_col])
    
    logger.info(f"Loaded {len(df):,} records")
    
    return df, store_col, sku_col, date_col, sales_col, category_col


def simulate_heuristic_policy(sim_data, store_col, sku_col, initial_inventory=50.0):
    """Simulate simple heuristic policy."""
    logger.info("Simulating heuristic policy")
    
    results = []
    
    for (store_id, sku_id), group_df in list(sim_data.groupby([store_col, sku_col]))[:100]:  # Limit for speed
        group_df = group_df.sort_values('date')
        
        inventory = initial_inventory
        total_ordered = 0.0
        total_waste = 0.0
        total_stockouts = 0.0
        total_demand = 0.0
        
        for _, row in group_df.iterrows():
            demand = row['demand']
            total_demand += demand
            
            # Simple heuristic: order if inventory < threshold
            if inventory < 20:
                order_qty = 50.0
                total_ordered += order_qty
                inventory += order_qty
            
            # Sales
            sales = min(demand, inventory)
            stockouts = max(0, demand - inventory)
            total_stockouts += stockouts
            
            inventory -= sales
            
            # Simple waste: 5% daily
            waste = inventory * 0.05
            total_waste += waste
            inventory -= waste
        
        results.append({
            store_col: store_id,
            sku_col: sku_id,
            'policy': 'heuristic',
            'total_demand': total_demand,
            'total_ordered': total_ordered,
            'total_waste': total_waste,
            'total_stockouts': total_stockouts,
            'service_level': (total_demand - total_stockouts) / total_demand if total_demand > 0 else 0,
            'waste_rate': total_waste / total_ordered if total_ordered > 0 else 0
        })
    
    return pd.DataFrame(results)


def simulate_model_based_policy(
    train_data, 
    sim_data, 
    store_col, 
    sku_col, 
    category_col, 
    date_col,
    lightgbm_model=None,
    use_lightgbm=True,
    initial_inventory=50.0
):
    """
    Simulate model-based policy with LightGBM forecasting.
    
    Args:
        train_data: Training data
        sim_data: Simulation data
        store_col: Store column name
        sku_col: SKU column name
        category_col: Category column name
        date_col: Date column name
        lightgbm_model: Pre-trained LightGBM model (optional)
        use_lightgbm: Whether to use LightGBM (True) or Moving Average (False)
        initial_inventory: Starting inventory level
    """
    logger.info(f"Simulating model-based policy (LightGBM={use_lightgbm})")
    
    results = []
    policy = OrderUpToPolicy()
    markdown_policy = MarkdownPolicy()
    
    # Load LightGBM model if available and requested
    if use_lightgbm and lightgbm_model is None:
        model_path = Path(config.data.models_dir) / "lightgbm_model.pkl"
        if model_path.exists():
            try:
                import joblib
                lightgbm_model = joblib.load(model_path)
                logger.info("✅ Loaded pre-trained LightGBM model")
            except Exception as e:
                logger.warning(f"Could not load LightGBM model: {e}, using Moving Average")
                use_lightgbm = False
        else:
            logger.warning("LightGBM model not found, using Moving Average")
            use_lightgbm = False
    
    store_skus = list(sim_data.groupby([store_col, sku_col]).groups.keys())[:100]  # Limit for speed
    
    for (store_id, sku_id) in store_skus:
        try:
            train_group = train_data[
                (train_data[store_col] == store_id) & 
                (train_data[sku_col] == sku_id)
            ].sort_values('date')
            
            sim_group = sim_data[
                (sim_data[store_col] == store_id) & 
                (sim_data[sku_col] == sku_id)
            ].sort_values('date')
            
            if len(train_group) < 7 or len(sim_group) == 0:
                continue
            
            # Prepare data for forecasting
            train_df = train_group.copy()
            train_df[store_col] = store_id
            train_df[sku_col] = sku_id
            
            # Get shelf-life
            category_id = train_group[category_col].iloc[0] if category_col in train_group.columns else None
            shelf_life = config.shelf_life.get_shelf_life(category_id) if category_id else 5
            
            # Initialize inventory tracking
            inventory = initial_inventory
            total_ordered = 0.0
            total_waste = 0.0
            total_stockouts = 0.0
            total_demand = 0.0
            total_markdown_sales = 0.0
            total_markdown_revenue = 0.0
            
            current_date = sim_group['date'].min()
            tracker = InventoryAgeTracker(current_date)
            
            # Add initial inventory to tracker
            if inventory > 0:
                expiry_date = current_date + timedelta(days=shelf_life)
                tracker.add_inventory(inventory, expiry_date)
            
            # Prepare feature columns for LightGBM (if using)
            feature_cols = None
            if use_lightgbm and lightgbm_model is not None:
                try:
                    # Create features for a sample to get feature columns
                    sample_features = create_forecast_features(
                        train_df.tail(14),
                        date_col=date_col,
                        target_col='demand',
                        store_col=store_col,
                        sku_col=sku_col
                    )
                    # Get feature columns (exclude metadata)
                    exclude_cols = [date_col, store_col, sku_col, 'demand', category_col]
                    feature_cols = [col for col in sample_features.columns if col not in exclude_cols]
                except Exception as e:
                    logger.warning(f"Could not create features for {store_id}-{sku_id}: {e}, using Moving Average")
                    use_lightgbm = False
            
            for _, row in sim_group.iterrows():
                date = row['date']
                demand = row['demand']
                total_demand += demand
                discount_pct = 0.0  # Initialize discount
                
                # Update tracker date
                tracker.current_date = date
                for bucket in tracker.buckets:
                    bucket.update_days_until_expiry(date)
                
                # Check for markdown opportunities (before sales)
                expiring_soon = tracker.get_expiring_units(3)  # Units expiring in next 3 days
                if expiring_soon > 0:
                    # Get discount for nearest expiry
                    nearest_expiry = min([b.days_until_expiry for b in tracker.buckets if b.days_until_expiry is not None and b.days_until_expiry <= 3], default=None)
                    if nearest_expiry is not None:
                        discount_pct = markdown_policy.get_discount_for_expiry(
                            days_until_expiry=nearest_expiry,
                            current_inventory=inventory
                        )
                        if discount_pct > 0:
                            # Estimate demand uplift from markdown
                            base_demand = demand
                            uplifted_demand = markdown_policy.estimate_demand_uplift(
                                base_demand=base_demand,
                                discount_percent=discount_pct,
                                price_elasticity=-2.0
                            )
                            demand = uplifted_demand  # Use uplifted demand for this day
                
                # Forecast demand for next 7 days
                if use_lightgbm and lightgbm_model is not None and feature_cols:
                    try:
                        # Create features for forecast
                        forecast_input = train_df.tail(14).copy()
                        forecast_features = create_forecast_features(
                            forecast_input,
                            date_col=date_col,
                            target_col='demand',
                            store_col=store_col,
                            sku_col=sku_col
                        )
                        
                        # Ensure all feature columns exist
                        for col in feature_cols:
                            if col not in forecast_features.columns:
                                forecast_features[col] = 0
                        
                        # Predict using LightGBM
                        X_pred = forecast_features[feature_cols].fillna(0)
                        forecasted_daily = lightgbm_model.predict(X_pred.iloc[-1:].values)[0]
                        forecasted_demand = max(0, forecasted_daily * 7)  # 7-day forecast
                    except Exception as e:
                        logger.debug(f"LightGBM prediction failed for {store_id}-{sku_id}: {e}, using Moving Average")
                        # Fallback to Moving Average
                        forecast_model = MovingAverageForecaster(window=7)
                        forecast_model.train(
                            pd.DataFrame({'date': train_df['date'], 'demand': train_df['demand']}),
                            target_col='demand'
                        )
                        forecast = forecast_model.predict(
                            pd.DataFrame({'date': train_df.tail(7)['date'], 'demand': train_df.tail(7)['demand']}),
                            horizon=7
                        )
                        forecasted_demand = forecast['predicted_demand'].mean() * 7
                else:
                    # Use Moving Average
                    forecast_model = MovingAverageForecaster(window=7)
                    forecast_model.train(
                        pd.DataFrame({'date': train_df['date'], 'demand': train_df['demand']}),
                        target_col='demand'
                    )
                    forecast = forecast_model.predict(
                        pd.DataFrame({'date': train_df.tail(7)['date'], 'demand': train_df.tail(7)['demand']}),
                        horizon=7
                    )
                    forecasted_demand = forecast['predicted_demand'].mean() * 7
                
                # Calculate expiring units
                expiring_units = tracker.get_expiring_units(7)
                
                # Calculate order quantity
                order_qty = policy.calculate_order_quantity(
                    forecasted_demand=forecasted_demand,
                    current_inventory=inventory,
                    inbound_orders=0.0,
                    expiring_units=expiring_units,
                    max_sellable_before_expiry=tracker.get_max_sellable_before_expiry(
                        forecasted_daily_demand=forecasted_demand / 7,
                        coverage_days=7
                    ) if len(tracker.buckets) > 0 else None
                )
                
                if order_qty > 0:
                    total_ordered += order_qty
                    inventory += order_qty
                    expiry_date = date + timedelta(days=shelf_life)
                    tracker.add_inventory(order_qty, expiry_date)
                
                # Sales (limited by inventory)
                sales = min(demand, inventory)
                stockouts = max(0, demand - inventory)
                total_stockouts += stockouts
                inventory -= sales
                
                # Track markdown sales
                if discount_pct > 0 and sales > 0:
                    total_markdown_sales += sales
                    # Assume unit price = 10, cost = 5 for revenue calculation
                    unit_price = 10.0
                    discounted_price = unit_price * (1 - discount_pct / 100.0)
                    total_markdown_revenue += sales * discounted_price
                
                # Waste: units that expire today
                tracker.current_date = date
                expired_buckets = []
                for bucket in tracker.buckets:
                    bucket.update_days_until_expiry(date)
                    if bucket.days_until_expiry == 0 and bucket.quantity > 0:
                        waste = bucket.quantity
                        total_waste += waste
                        inventory -= waste
                        expired_buckets.append(bucket)
                
                # Remove expired buckets
                for bucket in expired_buckets:
                    tracker.buckets.remove(bucket)
                
                # Update training data for next iteration
                train_df = pd.concat([
                    train_df,
                    pd.DataFrame([{
                        date_col: date, 
                        'demand': row['demand'],  # Use actual demand, not uplifted
                        store_col: store_id, 
                        sku_col: sku_id
                    }])
                ], ignore_index=True)
            
            results.append({
                store_col: store_id,
                sku_col: sku_id,
                'policy': 'model_based',
                'total_demand': total_demand,
                'total_ordered': total_ordered,
                'total_waste': total_waste,
                'total_stockouts': total_stockouts,
                'total_markdown_sales': total_markdown_sales,
                'total_markdown_revenue': total_markdown_revenue,
                'service_level': (total_demand - total_stockouts) / total_demand if total_demand > 0 else 0,
                'waste_rate': total_waste / total_ordered if total_ordered > 0 else 0
            })
        except Exception as e:
            logger.warning(f"Error for {store_id}-{sku_id}: {e}")
            continue
    
    return pd.DataFrame(results)


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("OFFLINE SIMULATION - POLICY COMPARISON")
    print("="*80)
    
    # Load data
    df, store_col, sku_col, date_col, sales_col, category_col = load_mvp_data()
    
    # Aggregate to daily
    df_daily = aggregate_to_daily(
        df,
        date_col=date_col,
        value_col=sales_col,
        group_cols=[store_col, sku_col],
        agg_func='sum'
    )
    df_daily = df_daily.rename(columns={date_col: 'date', sales_col: 'demand'})
    df_daily = df_daily.sort_values(['date', store_col, sku_col])
    
    # Split train/sim
    sim_start = df_daily['date'].max() - timedelta(days=30)
    train_data = df_daily[df_daily['date'] <= sim_start].copy()
    sim_data = df_daily[df_daily['date'] > sim_start].copy()
    
    logger.info(f"Train: {len(train_data):,} records")
    logger.info(f"Sim: {len(sim_data):,} records")
    
    # Run simulations
    print("\n1. Running heuristic policy simulation...")
    heuristic_results = simulate_heuristic_policy(sim_data, store_col, sku_col)
    
    print("\n2. Running model-based policy simulation...")
    # Try to load LightGBM model
    lightgbm_model = None
    model_path = Path(config.data.models_dir) / "lightgbm_model.pkl"
    if model_path.exists():
        try:
            import joblib
            model_data = joblib.load(model_path)
            lightgbm_model = model_data.get('model')
            logger.info("✅ Loaded LightGBM model for simulation")
        except Exception as e:
            logger.warning(f"Could not load LightGBM model: {e}")
    
    model_results = simulate_model_based_policy(
        train_data, sim_data, store_col, sku_col, category_col, 'date',
        lightgbm_model=lightgbm_model,
        use_lightgbm=(lightgbm_model is not None)
    )
    
    # Compare results
    all_results = pd.concat([heuristic_results, model_results], ignore_index=True)
    
    agg_dict = {
        'total_demand': 'sum',
        'total_ordered': 'sum',
        'total_waste': 'sum',
        'total_stockouts': 'sum',
        'service_level': 'mean',
        'waste_rate': 'mean'
    }
    
    # Add markdown metrics if available
    if 'total_markdown_sales' in all_results.columns:
        agg_dict['total_markdown_sales'] = 'sum'
        agg_dict['total_markdown_revenue'] = 'sum'
    
    comparison = all_results.groupby('policy').agg(agg_dict).reset_index()
    
    comparison['waste_pct'] = (comparison['total_waste'] / comparison['total_ordered'] * 100).round(2)
    comparison['stockout_pct'] = (comparison['total_stockouts'] / comparison['total_demand'] * 100).round(2)
    comparison['service_level_pct'] = (comparison['service_level'] * 100).round(2)
    
    # Calculate waste reduction from markdowns
    if 'total_markdown_sales' in comparison.columns:
        comparison['waste_after_markdown'] = comparison['total_waste'] - comparison['total_markdown_sales']
        comparison['waste_after_markdown_pct'] = (comparison['waste_after_markdown'] / comparison['total_ordered'] * 100).round(2)
    
    print("\n" + "="*80)
    print("SIMULATION RESULTS")
    print("="*80)
    display_cols = ['policy', 'service_level_pct', 'waste_pct', 'stockout_pct', 'total_ordered']
    if 'waste_after_markdown_pct' in comparison.columns:
        display_cols.append('waste_after_markdown_pct')
    print(comparison[display_cols].to_string(index=False))
    
    # Save results
    output_dir = Path(config.data.processed_path) / "simulation_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    comparison.to_csv(output_dir / "simulation_comparison.csv", index=False)
    all_results.to_csv(output_dir / "simulation_detailed_results.csv", index=False)
    
    print(f"\n[OK] Results saved to {output_dir}")
    
    # Calculate improvements
    if len(comparison) == 2:
        heuristic = comparison[comparison['policy'] == 'heuristic'].iloc[0]
        model = comparison[comparison['policy'] == 'model_based'].iloc[0]
        
        print("\n" + "="*80)
        print("IMPROVEMENTS (Model-based vs Heuristic)")
        print("="*80)
        print(f"Service Level: {model['service_level_pct']:.2f}% vs {heuristic['service_level_pct']:.2f}%")
        print(f"Waste Rate: {model['waste_pct']:.2f}% vs {heuristic['waste_pct']:.2f}%")
        print(f"Stockout Rate: {model['stockout_pct']:.2f}% vs {heuristic['stockout_pct']:.2f}%")
        
        if heuristic['waste_pct'] > 0:
            waste_improvement = ((heuristic['waste_pct'] - model['waste_pct']) / heuristic['waste_pct'] * 100)
            print(f"\nWaste Reduction: {waste_improvement:.1f}%")
        
        if heuristic['stockout_pct'] > 0:
            stockout_improvement = ((heuristic['stockout_pct'] - model['stockout_pct']) / heuristic['stockout_pct'] * 100)
            print(f"Stockout Reduction: {stockout_improvement:.1f}%")
    
    logger.info("Simulation complete")


if __name__ == "__main__":
    main()


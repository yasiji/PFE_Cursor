"""
Script to train and evaluate baseline forecasting models on MVP subset.

This script:
1. Loads MVP subset data
2. Aggregates to daily level
3. Splits into train/test
4. Trains baseline models
5. Evaluates and compares performance
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import timedelta

from shared.config import get_config
from shared.logging_setup import setup_logging, get_logger
from shared.column_mappings import COLUMN_MAPPINGS
from services.ingestion.datasets import load_freshretailnet_dataset
from services.forecasting.features.aggregate_daily import aggregate_to_daily
from services.forecasting.models.baseline import (
    LastValueForecaster,
    MovingAverageForecaster,
    SeasonalNaiveForecaster
)
from services.forecasting.evaluators import ForecastEvaluator

# Setup
setup_logging()
logger = get_logger(__name__)
config = get_config()


def load_mvp_data():
    """Load and filter MVP subset data."""
    logger.info("Loading MVP subset data")
    
    # Load dataset
    dataset = load_freshretailnet_dataset()
    df = dataset['train'].to_pandas()
    
    # Get column mappings
    store_col = COLUMN_MAPPINGS.get('store_id', 'store_id')
    sku_col = COLUMN_MAPPINGS.get('sku_id', 'product_id')
    date_col = COLUMN_MAPPINGS.get('date_col', 'dt')
    sales_col = COLUMN_MAPPINGS.get('sales_col', 'sale_amount')
    
    # Load MVP store list
    mvp_file = Path(config.data.processed_path) / "mvp_selection" / "mvp_subset.txt"
    if mvp_file.exists():
        with open(mvp_file, 'r') as f:
            lines = f.readlines()
        # Extract store IDs (they're listed after "Selected Stores")
        stores = []
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
            logger.info(f"Filtering to {len(stores)} MVP stores")
            df = df[df[store_col].isin(stores)].copy()
        else:
            logger.warning("Could not parse MVP stores, using all data")
    else:
        logger.warning(f"MVP file not found at {mvp_file}, using all data")
    
    # Convert date column
    if df[date_col].dtype == 'object':
        df[date_col] = pd.to_datetime(df[date_col])
    
    logger.info(f"Loaded data: {len(df)} records, {df[store_col].nunique()} stores, {df[sku_col].nunique()} SKUs")
    
    return df, store_col, sku_col, date_col, sales_col


def prepare_daily_series(df, store_col, sku_col, date_col, sales_col):
    """Aggregate hourly data to daily and prepare time series."""
    logger.info("Aggregating to daily level")
    
    # Aggregate to daily
    df_daily = aggregate_to_daily(
        df,
        date_col=date_col,
        value_col=sales_col,
        group_cols=[store_col, sku_col],
        agg_func='sum'
    )
    
    # Rename columns for clarity
    df_daily = df_daily.rename(columns={
        date_col: 'date',
        sales_col: 'demand'
    })
    
    # Sort by date
    df_daily = df_daily.sort_values(['date', store_col, sku_col])
    
    logger.info(f"Daily aggregation complete: {len(df_daily)} records")
    logger.info(f"Date range: {df_daily['date'].min()} to {df_daily['date'].max()}")
    
    return df_daily


def split_train_test(df_daily, test_days=14):
    """Split data into train and test sets."""
    logger.info(f"Splitting data: last {test_days} days for testing")
    
    # Get date range
    max_date = df_daily['date'].max()
    split_date = max_date - timedelta(days=test_days)
    
    train = df_daily[df_daily['date'] <= split_date].copy()
    test = df_daily[df_daily['date'] > split_date].copy()
    
    logger.info(f"Train: {len(train)} records ({train['date'].min()} to {train['date'].max()})")
    logger.info(f"Test: {len(test)} records ({test['date'].min()} to {test['date'].max()})")
    
    return train, test, split_date


def train_and_evaluate_baselines(train, test, store_col, sku_col):
    """Train and evaluate all baseline models."""
    logger.info("Training and evaluating baseline models")
    
    results = {}
    
    # Group by store-SKU for evaluation
    test_grouped = test.groupby([store_col, sku_col])
    train_grouped = train.groupby([store_col, sku_col])
    
    # Get unique store-SKU combinations
    store_skus = list(test_grouped.groups.keys())
    logger.info(f"Evaluating on {len(store_skus)} store-SKU combinations")
    
    # Models to evaluate
    models = {
        'LastValue': LastValueForecaster(),
        'MovingAverage_7': MovingAverageForecaster(window=7),
        'MovingAverage_14': MovingAverageForecaster(window=14),
        'SeasonalNaive_7': SeasonalNaiveForecaster(season_length=7),
    }
    
    all_predictions = []
    
    for model_name, model in models.items():
        logger.info(f"Training {model_name}...")
        
        predictions_list = []
        
        # Train and predict for each store-SKU
        for (store_id, sku_id) in store_skus[:100]:  # Limit to first 100 for speed
            try:
                # Get training data for this store-SKU
                train_series = train_grouped.get_group((store_id, sku_id)).sort_values('date')
                test_series = test_grouped.get_group((store_id, sku_id)).sort_values('date')
                
                if len(train_series) < 7:  # Need minimum data
                    continue
                
                # Prepare data
                train_data = pd.DataFrame({
                    'date': train_series['date'],
                    'demand': train_series['demand']
                })
                
                # Train model
                model.train(train_data, target_col='demand')
                
                # Predict
                horizon = len(test_series)
                preds = model.predict(train_data, horizon=horizon)
                
                # Add metadata
                preds[store_col] = store_id
                preds[sku_col] = sku_id
                preds['actual'] = test_series['demand'].values
                preds['model'] = model_name
                
                predictions_list.append(preds)
                
            except Exception as e:
                logger.warning(f"Error for {store_id}-{sku_id}: {e}")
                continue
        
        if predictions_list:
            all_predictions.extend(predictions_list)
            
            # Evaluate
            combined_preds = pd.concat(predictions_list, ignore_index=True)
            actual = pd.Series(combined_preds['actual'].values)
            predicted = pd.Series(combined_preds['predicted_demand'].values)
            
            metrics = ForecastEvaluator.evaluate(actual, predicted)
            
            results[model_name] = metrics
            logger.info(f"{model_name} - MAE: {metrics['mae']:.3f}, RMSE: {metrics['rmse']:.3f}, MAPE: {metrics['mape']:.2f}%")
    
    # Create comparison table
    comparison = pd.DataFrame(results).T
    comparison = comparison.sort_values('mae')
    
    logger.info("\nModel Comparison (sorted by MAE):")
    logger.info(comparison.to_string())
    
    return results, comparison, all_predictions


def save_results(results, comparison, predictions, output_dir):
    """Save evaluation results."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save comparison table
    comparison_path = output_dir / "baseline_model_comparison.csv"
    comparison.to_csv(comparison_path)
    logger.info(f"Saved comparison to {comparison_path}")
    
    # Save detailed results
    results_path = output_dir / "baseline_model_results.json"
    import json
    # Convert numpy types to native Python types for JSON
    results_json = {}
    for model, metrics in results.items():
        results_json[model] = {k: float(v) if isinstance(v, (np.integer, np.floating)) else v 
                               for k, v in metrics.items()}
    
    with open(results_path, 'w') as f:
        json.dump(results_json, f, indent=2)
    logger.info(f"Saved results to {results_path}")
    
    # Save predictions sample
    if predictions:
        preds_df = pd.concat(predictions, ignore_index=True)
        preds_path = output_dir / "baseline_predictions_sample.csv"
        preds_df.head(1000).to_csv(preds_path, index=False)
        logger.info(f"Saved predictions sample to {preds_path}")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("BASELINE MODEL TRAINING AND EVALUATION")
    print("="*80)
    
    # Load data
    df, store_col, sku_col, date_col, sales_col = load_mvp_data()
    
    # Prepare daily series
    df_daily = prepare_daily_series(df, store_col, sku_col, date_col, sales_col)
    
    # Split train/test
    train, test, split_date = split_train_test(df_daily, test_days=14)
    
    # Train and evaluate
    results, comparison, predictions = train_and_evaluate_baselines(
        train, test, store_col, sku_col
    )
    
    # Save results
    output_dir = Path(config.data.processed_path) / "baseline_results"
    save_results(results, comparison, predictions, output_dir)
    
    print("\n" + "="*80)
    print("BASELINE EVALUATION COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_dir}")
    print("\nModel Performance Summary:")
    print(comparison.to_string())
    
    logger.info("Baseline model training and evaluation completed")


if __name__ == "__main__":
    main()


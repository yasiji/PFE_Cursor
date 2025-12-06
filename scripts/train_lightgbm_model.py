"""
Script to train and evaluate LightGBM model on MVP subset.

This script:
1. Loads MVP subset data
2. Creates features using feature engineering pipeline
3. Trains LightGBM model
4. Evaluates and compares with baselines
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
from services.forecasting.features.feature_engineering import (
    create_forecast_features,
    get_feature_columns
)
from services.forecasting.models.lightgbm_model import LightGBMForecaster
from services.forecasting.models.baseline import MovingAverageForecaster
from services.forecasting.evaluators import ForecastEvaluator

# Setup
setup_logging()
logger = get_logger(__name__)
config = get_config()


def load_mvp_data():
    """Load and filter MVP subset data."""
    logger.info("Loading MVP subset data")
    
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
    
    # Convert date column
    if df[date_col].dtype == 'object':
        df[date_col] = pd.to_datetime(df[date_col])
    
    logger.info(f"Loaded data: {len(df)} records")
    
    return df, store_col, sku_col, date_col, sales_col


def prepare_daily_series(df, store_col, sku_col, date_col, sales_col):
    """Aggregate to daily and prepare time series."""
    logger.info("Aggregating to daily level")
    
    df_daily = aggregate_to_daily(
        df,
        date_col=date_col,
        value_col=sales_col,
        group_cols=[store_col, sku_col],
        agg_func='sum'
    )
    
    df_daily = df_daily.rename(columns={
        date_col: 'date',
        sales_col: 'demand'
    })
    
    df_daily = df_daily.sort_values(['date', store_col, sku_col])
    
    logger.info(f"Daily aggregation: {len(df_daily)} records")
    
    return df_daily


def split_train_test(df_daily, test_days=14, val_days=7):
    """Split data into train, validation, and test sets."""
    logger.info(f"Splitting data: {val_days} days validation, {test_days} days testing")
    
    max_date = df_daily['date'].max()
    test_start = max_date - timedelta(days=test_days)
    val_start = test_start - timedelta(days=val_days)
    
    train = df_daily[df_daily['date'] <= val_start].copy()
    val = df_daily[(df_daily['date'] > val_start) & (df_daily['date'] <= test_start)].copy()
    test = df_daily[df_daily['date'] > test_start].copy()
    
    logger.info(f"Train: {len(train)} records ({train['date'].min()} to {train['date'].max()})")
    logger.info(f"Val: {len(val)} records ({val['date'].min()} to {val['date'].max()})")
    logger.info(f"Test: {len(test)} records ({test['date'].min()} to {test['date'].max()})")
    
    return train, val, test


def train_and_evaluate_lightgbm(train, val, test, store_col, sku_col):
    """Train LightGBM model and evaluate."""
    logger.info("Training LightGBM model")
    
    # Create features for training data
    logger.info("Creating features for training data")
    train_features = create_forecast_features(
        train,
        date_col='date',
        target_col='demand',
        store_col=store_col,
        sku_col=sku_col
    )
    
    # Create features for validation data
    logger.info("Creating features for validation data")
    val_features = create_forecast_features(
        val,
        date_col='date',
        target_col='demand',
        store_col=store_col,
        sku_col=sku_col
    )
    
    # Create features for test data
    logger.info("Creating features for test data")
    test_features = create_forecast_features(
        test,
        date_col='date',
        target_col='demand',
        store_col=store_col,
        sku_col=sku_col
    )
    
    # Get feature columns (exclude metadata)
    exclude_cols = ['date', store_col, sku_col, 'demand']
    feature_cols = get_feature_columns(train_features, exclude_cols=exclude_cols)
    
    logger.info(f"Using {len(feature_cols)} features")
    
    # Sample data for faster training (use subset of store-SKU combinations)
    train_grouped = train_features.groupby([store_col, sku_col])
    store_skus = list(train_grouped.groups.keys())[:200]  # Limit to 200 for speed
    
    train_sample = train_features[train_features.groupby([store_col, sku_col]).ngroup().isin(range(len(store_skus)))].copy()
    val_sample = val_features[val_features.groupby([store_col, sku_col]).ngroup().isin(range(len(store_skus)))].copy()
    test_sample = test_features[test_features.groupby([store_col, sku_col]).ngroup().isin(range(len(store_skus)))].copy()
    
    logger.info(f"Training on {len(train_sample)} records, {len(store_skus)} store-SKU combinations")
    
    # Train model
    model = LightGBMForecaster(
        name="lightgbm",
        num_boost_round=200,
        early_stopping_rounds=20
    )
    
    model.train(
        train_sample,
        target_col='demand',
        feature_cols=feature_cols,
        val_data=val_sample
    )
    
    # Evaluate on test set
    logger.info("Evaluating on test set")
    test_sample_sorted = test_sample.sort_values([store_col, sku_col, 'date'])
    
    predictions_list = []
    test_grouped = test_sample_sorted.groupby([store_col, sku_col])
    
    for (store_id, sku_id), group_df in list(test_grouped)[:100]:  # Limit to 100 for speed
        try:
            # Get corresponding training data for this store-SKU
            train_group = train_sample[train_sample[store_col] == store_id]
            train_group = train_group[train_group[sku_col] == sku_id].sort_values('date')
            
            if len(train_group) < 7:
                continue
            
            # Prepare features for prediction
            pred_data = group_df.copy()
            
            # Predict
            preds = model.predict(pred_data, horizon=len(group_df), feature_cols=feature_cols)
            
            # Add metadata
            preds[store_col] = store_id
            preds[sku_col] = sku_id
            preds['actual'] = group_df['demand'].values
            preds['date'] = group_df['date'].values
            
            predictions_list.append(preds)
        except Exception as e:
            logger.warning(f"Error for {store_id}-{sku_id}: {e}")
            continue
    
    if predictions_list:
        combined_preds = pd.concat(predictions_list, ignore_index=True)
        actual = pd.Series(combined_preds['actual'].values)
        predicted = pd.Series(combined_preds['predicted_demand'].values)
        
        metrics = ForecastEvaluator.evaluate(actual, predicted)
        
        logger.info(f"LightGBM - MAE: {metrics['mae']:.3f}, RMSE: {metrics['rmse']:.3f}, MAPE: {metrics['mape']:.2f}%")
        
        # Compare with baseline
        baseline_model = MovingAverageForecaster(window=7)
        baseline_train = train_sample.sort_values([store_col, sku_col, 'date'])
        baseline_predictions = []
        
        for (store_id, sku_id), group_df in list(test_grouped)[:100]:
            try:
                train_group = baseline_train[baseline_train[store_col] == store_id]
                train_group = train_group[train_group[sku_col] == sku_id].sort_values('date')
                
                if len(train_group) < 7:
                    continue
                
                baseline_model.train(
                    pd.DataFrame({'date': train_group['date'], 'demand': train_group['demand']}),
                    target_col='demand'
                )
                
                preds = baseline_model.predict(
                    pd.DataFrame({'date': train_group['date'], 'demand': train_group['demand']}),
                    horizon=len(group_df)
                )
                
                baseline_predictions.append({
                    'actual': group_df['demand'].values,
                    'predicted': preds['predicted_demand'].values
                })
            except Exception:
                continue
        
        if baseline_predictions:
            baseline_actual = pd.Series(np.concatenate([p['actual'] for p in baseline_predictions]))
            baseline_predicted = pd.Series(np.concatenate([p['predicted'] for p in baseline_predictions]))
            baseline_metrics = ForecastEvaluator.evaluate(baseline_actual, baseline_predicted)
            
            logger.info(f"Baseline (MA_7) - MAE: {baseline_metrics['mae']:.3f}, RMSE: {baseline_metrics['rmse']:.3f}, MAPE: {baseline_metrics['mape']:.2f}%")
            
            improvement = {
                'mae': (baseline_metrics['mae'] - metrics['mae']) / baseline_metrics['mae'] * 100,
                'mape': (baseline_metrics['mape'] - metrics['mape']) / baseline_metrics['mape'] * 100
            }
            
            logger.info(f"Improvement: MAE {improvement['mae']:.1f}%, MAPE {improvement['mape']:.1f}%")
        
        return metrics, combined_preds, model
    
    return None, None, None


def save_results(metrics, predictions, model, output_dir):
    """Save evaluation results."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save metrics
    if metrics:
        import json
        metrics_path = output_dir / "lightgbm_results.json"
        metrics_json = {k: float(v) if isinstance(v, (np.integer, np.floating)) else v 
                       for k, v in metrics.items()}
        with open(metrics_path, 'w') as f:
            json.dump(metrics_json, f, indent=2)
        logger.info(f"Saved metrics to {metrics_path}")
    
    # Save predictions
    if predictions is not None:
        preds_path = output_dir / "lightgbm_predictions.csv"
        predictions.to_csv(preds_path, index=False)
        logger.info(f"Saved predictions to {preds_path}")
    
    # Save model
    if model:
        model_path = output_dir / "lightgbm_model.pkl"
        model.save(str(model_path))
        logger.info(f"Saved model to {model_path}")
    
    # Save feature importance
    if model and model.get_feature_importance():
        importance = model.get_feature_importance()
        importance_df = pd.DataFrame([
            {'feature': k, 'importance': v} 
            for k, v in sorted(importance.items(), key=lambda x: x[1], reverse=True)
        ])
        importance_path = output_dir / "lightgbm_feature_importance.csv"
        importance_df.to_csv(importance_path, index=False)
        logger.info(f"Saved feature importance to {importance_path}")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("LIGHTGBM MODEL TRAINING AND EVALUATION")
    print("="*80)
    
    # Load data
    df, store_col, sku_col, date_col, sales_col = load_mvp_data()
    
    # Prepare daily series
    df_daily = prepare_daily_series(df, store_col, sku_col, date_col, sales_col)
    
    # Split train/val/test
    train, val, test = split_train_test(df_daily, test_days=14, val_days=7)
    
    # Train and evaluate
    metrics, predictions, model = train_and_evaluate_lightgbm(
        train, val, test, store_col, sku_col
    )
    
    # Save results
    if metrics:
        output_dir = Path(config.data.processed_path) / "lightgbm_results"
        save_results(metrics, predictions, model, output_dir)
        
        print("\n" + "="*80)
        print("LIGHTGBM EVALUATION COMPLETE")
        print("="*80)
        print(f"\nResults saved to: {output_dir}")
        print("\nModel Performance:")
        print(f"  MAE: {metrics['mae']:.3f}")
        print(f"  RMSE: {metrics['rmse']:.3f}")
        print(f"  MAPE: {metrics['mape']:.2f}%")
        print(f"  WAPE: {metrics['wape']:.2f}%")
        print(f"  Bias: {metrics['bias']:.3f}")
    
    logger.info("LightGBM training and evaluation completed")


if __name__ == "__main__":
    main()


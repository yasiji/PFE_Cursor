"""Utility functions for Streamlit dashboard data loading."""

from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import joblib
import streamlit as st

from shared.config import get_config
from shared.column_mappings import COLUMN_MAPPINGS
from shared.logging_setup import get_logger
from services.ingestion.datasets import load_freshretailnet_dataset
from services.forecasting.features.aggregate_daily import aggregate_to_daily

logger = get_logger(__name__)
config = get_config()


@st.cache_data
def load_mvp_data() -> Tuple[pd.DataFrame, dict]:
    """
    Load MVP subset data for dashboard.
    
    Returns:
        Tuple of (DataFrame, column_mapping_dict)
    """
    try:
        dataset = load_freshretailnet_dataset(use_local=True)
        df = dataset['train'].to_pandas()
        
        # Get column mappings
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
        
        column_map = {
            'store_col': store_col,
            'sku_col': sku_col,
            'date_col': date_col,
            'sales_col': sales_col,
            'category_col': category_col
        }
        
        return df, column_map
    except Exception as e:
        logger.error(f"Error loading MVP data: {e}")
        return pd.DataFrame(), {}


@st.cache_data
def load_daily_aggregated_data() -> Tuple[pd.DataFrame, dict]:
    """
    Load and aggregate data to daily level.
    
    Returns:
        Tuple of (daily DataFrame, column_mapping_dict)
    """
    df, column_map = load_mvp_data()
    
    if df.empty:
        return df, column_map
    
    store_col = column_map['store_col']
    sku_col = column_map['sku_col']
    date_col = column_map['date_col']
    sales_col = column_map['sales_col']
    
    # Aggregate to daily
    df_daily = aggregate_to_daily(
        df,
        date_col=date_col,
        value_col=sales_col,
        group_cols=[store_col, sku_col],
        agg_func='sum'
    )
    
    df_daily = df_daily.rename(columns={sales_col: 'demand'})
    df_daily = df_daily.sort_values([date_col, store_col, sku_col])
    
    return df_daily, column_map


@st.cache_resource
def load_lightgbm_model():
    """Load trained LightGBM model."""
    model_path = Path(config.data.models_dir) / "lightgbm_model.pkl"
    if model_path.exists():
        try:
            model_data = joblib.load(model_path)
            return model_data
        except Exception as e:
            logger.error(f"Error loading LightGBM model: {e}")
            return None
    return None


@st.cache_data
def load_simulation_results() -> Optional[pd.DataFrame]:
    """Load simulation comparison results."""
    results_path = Path(config.data.processed_path) / "simulation_results" / "simulation_comparison.csv"
    if results_path.exists():
        try:
            return pd.read_csv(results_path)
        except Exception as e:
            logger.error(f"Error loading simulation results: {e}")
            return None
    return None


@st.cache_data
def load_baseline_results() -> Optional[pd.DataFrame]:
    """Load baseline model comparison results."""
    results_path = Path(config.data.processed_path) / "baseline_results" / "baseline_model_comparison.csv"
    if results_path.exists():
        try:
            return pd.read_csv(results_path)
        except Exception as e:
            logger.error(f"Error loading baseline results: {e}")
            return None
    return None


@st.cache_data
def load_lightgbm_results() -> Optional[dict]:
    """Load LightGBM model results."""
    results_path = Path(config.data.processed_path) / "lightgbm_results" / "lightgbm_results.json"
    if results_path.exists():
        try:
            import json
            with open(results_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading LightGBM results: {e}")
            return None
    return None


@st.cache_data
def load_feature_importance() -> Optional[pd.DataFrame]:
    """Load LightGBM feature importance."""
    importance_path = Path(config.data.processed_path) / "lightgbm_results" / "lightgbm_feature_importance.csv"
    if importance_path.exists():
        try:
            return pd.read_csv(importance_path)
        except Exception as e:
            logger.error(f"Error loading feature importance: {e}")
            return None
    return None


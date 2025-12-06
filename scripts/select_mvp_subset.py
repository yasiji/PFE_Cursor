"""
Script to help select MVP subset of stores and categories.

Usage:
    python scripts/select_mvp_subset.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from shared.config import get_config
from shared.logging_setup import setup_logging, get_logger
from shared.column_mappings import COLUMN_MAPPINGS
from services.ingestion.datasets import load_freshretailnet_dataset

# Setup logging
setup_logging(service_name="mvp-selection")
logger = get_logger(__name__)


def select_mvp_subset(
    min_stores: int = 5,
    max_stores: int = 10,
    min_skus_per_store: int = 10,
    categories: list[str] | None = None
):
    """
    Select a subset of stores and SKUs for MVP development.

    Args:
        min_stores: Minimum number of stores to select
        max_stores: Maximum number of stores to select
        min_skus_per_store: Minimum number of SKUs per store
        categories: List of categories to include (if None, include all)
    """
    config = get_config()
    
    logger.info("Loading dataset for MVP subset selection")
    
    # Load dataset
    dataset = load_freshretailnet_dataset()
    
    # Use train split (adjust as needed)
    train_split = list(dataset.keys())[0]  # Get first split
    df = dataset[train_split].to_pandas()
    
    logger.info("Dataset loaded", shape=df.shape, columns=list(df.columns))
    
    # Use column mappings from auto-mapping
    store_col = COLUMN_MAPPINGS.get('store_id', 'store_id')
    sku_col = COLUMN_MAPPINGS.get('sku_id', 'product_id')
    category_col = COLUMN_MAPPINGS.get('category_col', 'first_category_id')
    sales_col = COLUMN_MAPPINGS.get('sales_col', 'sale_amount')
    
    print("\n" + "="*80)
    print("MVP Subset Selection")
    print("="*80)
    
    # Check if columns exist
    available_cols = set(df.columns)
    required_cols = {store_col, sku_col, category_col, sales_col}
    missing_cols = required_cols - available_cols
    
    if missing_cols:
        print(f"\n⚠️  Warning: Expected columns not found: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        print("\nPlease update column names in this script after dataset inspection (T-010).")
        return
    
    # Basic statistics
    num_stores = df[store_col].nunique()
    num_skus = df[sku_col].nunique()
    num_categories = df[category_col].nunique() if category_col in df.columns else 0
    
    print(f"\nDataset Statistics:")
    print(f"  Total stores: {num_stores}")
    print(f"  Total SKUs: {num_skus}")
    print(f"  Total categories: {num_categories}")
    print(f"  Total records: {len(df)}")
    
    # Filter by categories if specified
    if categories and category_col in df.columns:
        df_filtered = df[df[category_col].isin(categories)].copy()
        print(f"\nAfter filtering by categories {categories}:")
        print(f"  Stores: {df_filtered[store_col].nunique()}")
        print(f"  SKUs: {df_filtered[sku_col].nunique()}")
    else:
        df_filtered = df.copy()
    
    # Select stores with most data
    store_stats = df_filtered.groupby(store_col).agg({
        sku_col: 'nunique',
        sales_col: 'sum'
    }).reset_index()
    store_stats.columns = [store_col, 'num_skus', 'total_sales']
    
    # Filter stores with minimum SKUs
    store_stats = store_stats[store_stats['num_skus'] >= min_skus_per_store]
    
    # Sort by total sales and select top stores
    store_stats = store_stats.sort_values('total_sales', ascending=False)
    selected_stores = store_stats.head(max_stores)[store_col].tolist()
    
    print(f"\nSelected Stores (top {len(selected_stores)} by sales):")
    for store in selected_stores:
        store_info = store_stats[store_stats[store_col] == store].iloc[0]
        print(f"  {store}: {store_info['num_skus']} SKUs, {store_info['total_sales']:.0f} total sales")
    
    # Get SKUs for selected stores
    df_selected = df_filtered[df_filtered[store_col].isin(selected_stores)].copy()
    selected_skus = df_selected[sku_col].unique().tolist()
    
    print(f"\nSelected SKUs: {len(selected_skus)}")
    
    # Category distribution
    if category_col in df_selected.columns:
        category_dist = df_selected.groupby(category_col)[sku_col].nunique().sort_values(ascending=False)
        print(f"\nCategory Distribution:")
        for cat, count in category_dist.items():
            print(f"  {cat}: {count} SKUs")
    
    # Save selection to file
    output_dir = Path(config.data.processed_path) / "mvp_selection"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    selection_info = {
        'selected_stores': selected_stores,
        'selected_skus': selected_skus,
        'num_stores': len(selected_stores),
        'num_skus': len(selected_skus),
    }
    
    # Save as text file
    info_path = output_dir / "mvp_subset.txt"
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write("MVP Subset Selection\n")
        f.write("="*80 + "\n\n")
        f.write(f"Selected Stores ({len(selected_stores)}):\n")
        for store in selected_stores:
            f.write(f"  {store}\n")
        f.write(f"\nSelected SKUs: {len(selected_skus)}\n")
        f.write(f"\nTotal Records: {len(df_selected)}\n")
    
    print(f"\n✅ Selection saved to {info_path}")
    
    # Save selected data sample
    sample_path = output_dir / "mvp_subset_sample.csv"
    df_selected.head(1000).to_csv(sample_path, index=False)
    print(f"✅ Sample data saved to {sample_path}")
    
    logger.info(
        "MVP subset selected",
        num_stores=len(selected_stores),
        num_skus=len(selected_skus),
        total_records=len(df_selected)
    )
    
    return selected_stores, selected_skus


if __name__ == "__main__":
    # Example usage - adjust parameters as needed
    select_mvp_subset(
        min_stores=5,
        max_stores=10,
        min_skus_per_store=10,
        categories=None  # Set to ['fruits', 'vegetables'] to filter categories
    )


"""
Automated script to infer column mappings and generate data dictionary.

This script:
1. Loads the dataset
2. Automatically infers column mappings based on patterns
3. Generates data_dictionary.md
4. Updates notebooks/scripts with inferred mappings
"""

import sys
import re
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from shared.config import get_config
from shared.logging_setup import setup_logging, get_logger
from services.ingestion.datasets import load_freshretailnet_dataset

# Setup logging
setup_logging(service_name="auto-field-mapping")
logger = get_logger(__name__)


def infer_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """
    Automatically infer column mappings based on column names and data types.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dictionary mapping business entities to column names
    """
    mappings = {}
    columns_lower = {col.lower(): col for col in df.columns}
    
    # Store ID patterns
    store_patterns = ['store_id', 'store', 'store_code', 'shop_id', 'location_id']
    for pattern in store_patterns:
        if pattern in columns_lower:
            mappings['store_id'] = columns_lower[pattern]
            break
    
    # SKU/Product ID patterns
    sku_patterns = ['product_id', 'sku_id', 'sku', 'product', 'item_id', 'item', 'article_id']
    for pattern in sku_patterns:
        if pattern in columns_lower:
            mappings['sku_id'] = columns_lower[pattern]
            break
    
    # Date/Timestamp patterns
    date_patterns = ['dt', 'date', 'timestamp', 'datetime', 'time', 'day', 'created_at']
    for pattern in date_patterns:
        if pattern in columns_lower:
            col = columns_lower[pattern]
            # Check if it's actually a date type or string that looks like date
            if pd.api.types.is_datetime64_any_dtype(df[col]) or 'date' in col.lower() or 'time' in col.lower() or col.lower() == 'dt':
                mappings['date_col'] = col
                break
    
    # Sales/Quantity/Demand patterns
    sales_patterns = ['sale_amount', 'quantity', 'sales', 'demand', 'qty', 'units', 'volume', 'amount']
    for pattern in sales_patterns:
        if pattern in columns_lower:
            col = columns_lower[pattern]
            # Prefer numeric columns
            if pd.api.types.is_numeric_dtype(df[col]):
                mappings['sales_col'] = col
                break
    
    # Category patterns
    category_patterns = ['first_category_id', 'second_category_id', 'third_category_id', 'category', 'cat', 'product_category', 'category_name', 'type']
    for pattern in category_patterns:
        if pattern in columns_lower:
            mappings['category_col'] = columns_lower[pattern]
            break
    
    # Stockout patterns
    stockout_patterns = ['stock_hour6_22_cnt', 'hours_stock_status', 'stockout', 'out_of_stock', 'stock_out', 'oos', 'in_stock', 'available']
    for pattern in stockout_patterns:
        if pattern in columns_lower:
            mappings['stockout_col'] = columns_lower[pattern]
            break
    
    # Price patterns
    price_patterns = ['price', 'unit_price', 'selling_price', 'cost']
    for pattern in price_patterns:
        if pattern in columns_lower:
            mappings['price_col'] = columns_lower[pattern]
            break
    
    # Weather patterns
    weather_patterns = ['avg_temperature', 'precpt', 'avg_humidity', 'avg_wind_level', 'weather', 'temperature', 'temp', 'precipitation', 'rain']
    for pattern in weather_patterns:
        if pattern in columns_lower:
            mappings['weather_col'] = columns_lower[pattern]
            break
    
    # Promotion patterns
    promo_patterns = ['promo', 'promotion', 'discount', 'on_sale', 'special']
    for pattern in promo_patterns:
        if pattern in columns_lower:
            mappings['promo_col'] = columns_lower[pattern]
            break
    
    # Stock/Inventory patterns
    stock_patterns = ['stock', 'inventory', 'on_hand', 'balance', 'quantity_on_hand']
    for pattern in stock_patterns:
        if pattern in columns_lower and pattern not in ['stockout']:
            mappings['stock_col'] = columns_lower[pattern]
            break
    
    return mappings


def generate_data_dictionary(df: pd.DataFrame, mappings: Dict[str, str]) -> str:
    """
    Generate data dictionary markdown content.
    
    Args:
        df: DataFrame
        mappings: Column mappings
        
    Returns:
        Markdown string
    """
    content = ["# Data Dictionary - FreshRetailNet-50K\n"]
    content.append("This document maps the FreshRetailNet-50K dataset fields to business entities.\n")
    content.append("> **Auto-generated** by `scripts/auto_map_fields.py`\n")
    
    content.append("\n## Dataset Overview\n")
    content.append(f"- **Total Rows:** {len(df):,}")
    content.append(f"- **Total Columns:** {len(df.columns)}")
    content.append(f"- **Columns:** {', '.join(df.columns)}\n")
    
    content.append("\n## Business Entity Mappings\n")
    content.append("### Store\n")
    if 'store_id' in mappings:
        content.append(f"- **Store ID** → Column: `{mappings['store_id']}`")
        content.append(f"  - Unique stores: {df[mappings['store_id']].nunique()}")
    else:
        content.append("- **Store ID** → ⚠️ Not found (check column names)")
    
    content.append("\n### Product / SKU\n")
    if 'sku_id' in mappings:
        content.append(f"- **SKU ID** → Column: `{mappings['sku_id']}`")
        content.append(f"  - Unique SKUs: {df[mappings['sku_id']].nunique()}")
    else:
        content.append("- **SKU ID** → ⚠️ Not found (check column names)")
    
    content.append("\n### Sales Transactions\n")
    if 'sales_col' in mappings:
        content.append(f"- **Sales/Quantity** → Column: `{mappings['sales_col']}`")
        content.append(f"  - Data type: {df[mappings['sales_col']].dtype}")
        content.append(f"  - Min: {df[mappings['sales_col']].min()}, Max: {df[mappings['sales_col']].max()}")
        content.append(f"  - Mean: {df[mappings['sales_col']].mean():.2f}")
    else:
        content.append("- **Sales/Quantity** → ⚠️ Not found (check column names)")
    
    content.append("\n### Date/Time\n")
    if 'date_col' in mappings:
        content.append(f"- **Date/Timestamp** → Column: `{mappings['date_col']}`")
        content.append(f"  - Data type: {df[mappings['date_col']].dtype}")
        if pd.api.types.is_datetime64_any_dtype(df[mappings['date_col']]):
            content.append(f"  - Range: {df[mappings['date_col']].min()} to {df[mappings['date_col']].max()}")
    else:
        content.append("- **Date/Timestamp** → ⚠️ Not found (check column names)")
    
    content.append("\n### Category\n")
    if 'category_col' in mappings:
        content.append(f"- **Category** → Column: `{mappings['category_col']}`")
        content.append(f"  - Unique categories: {df[mappings['category_col']].nunique()}")
        content.append(f"  - Categories: {', '.join(map(str, df[mappings['category_col']].unique()[:10]))}")
    else:
        content.append("- **Category** → ⚠️ Not found (check column names)")
    
    content.append("\n### Stockout Status\n")
    if 'stockout_col' in mappings:
        content.append(f"- **Stockout** → Column: `{mappings['stockout_col']}`")
        if df[mappings['stockout_col']].dtype == 'bool' or df[mappings['stockout_col']].dtype == 'int64':
            stockout_rate = df[mappings['stockout_col']].mean() * 100
            content.append(f"  - Stockout rate: {stockout_rate:.2f}%")
    else:
        content.append("- **Stockout** → ⚠️ Not found (check column names)")
    
    content.append("\n## All Columns\n")
    content.append("| Column | Data Type | Unique Values | Missing % | Description |\n")
    content.append("|--------|-----------|--------------|-----------|-------------|\n")
    
    for col in df.columns:
        dtype = str(df[col].dtype)
        
        # Handle array columns
        try:
            sample = df[col].dropna()
            is_array_col = False
            if len(sample) > 0:
                first_val = sample.iloc[0]
                if isinstance(first_val, (list, np.ndarray)):
                    is_array_col = True
                    unique = "Array/Sequence"
                else:
                    unique = df[col].nunique()
            else:
                unique = 0
        except Exception:
            unique = "N/A"
        
        missing_pct = (df[col].isnull().sum() / len(df) * 100)
        description = "Auto-inferred"  # Could be enhanced
        
        # Try to infer description
        col_lower = col.lower()
        if 'store' in col_lower:
            description = "Store identifier"
        elif 'sku' in col_lower or 'product' in col_lower:
            description = "Product/SKU identifier"
        elif 'date' in col_lower or 'time' in col_lower:
            description = "Date/timestamp"
        elif 'quantity' in col_lower or 'sales' in col_lower:
            description = "Sales quantity"
        elif 'category' in col_lower:
            description = "Product category"
        elif 'stockout' in col_lower or 'stock' in col_lower:
            description = "Stock/stockout status"
        elif 'price' in col_lower:
            description = "Price information"
        elif 'weather' in col_lower:
            description = "Weather data"
        elif 'promo' in col_lower:
            description = "Promotion/discount"
        
        # Format unique value count
        if isinstance(unique, (int, float)):
            unique_str = f"{unique:,}"
        else:
            unique_str = str(unique)
        
        content.append(f"| `{col}` | {dtype} | {unique_str} | {missing_pct:.2f}% | {description} |\n")
    
    return "".join(content)


def update_scripts_with_mappings(mappings: Dict[str, str]):
    """Update scripts and notebooks with inferred mappings."""
    # Create a Python file with mappings that can be imported
    mappings_file = Path(__file__).parent.parent / "shared" / "column_mappings.py"
    
    content = ['"""Auto-generated column mappings."""\n\n']
    content.append("# This file is auto-generated by scripts/auto_map_fields.py\n")
    content.append("# Update manually if needed\n\n")
    content.append("COLUMN_MAPPINGS = {\n")
    
    for key, value in mappings.items():
        content.append(f'    "{key}": "{value}",\n')
    
    content.append("}\n")
    
    mappings_file.write_text("".join(content))
    logger.info(f"Saved mappings to {mappings_file}")


def auto_map_fields():
    """Main function to automatically map fields."""
    config = get_config()
    
    logger.info("Starting automatic field mapping")
    
    try:
        # Load dataset (try local first, then HuggingFace)
        logger.info("Loading dataset (trying local files first, then HuggingFace)...")
        dataset = load_freshretailnet_dataset(use_local=True)
        
        # Get first split for analysis
        first_split = list(dataset.keys())[0]
        df = dataset[first_split].to_pandas()
        
        logger.info(f"Dataset loaded: {df.shape}, split: {first_split}")
        logger.info(f"Columns: {list(df.columns)}")
        
        # Infer mappings
        logger.info("Inferring column mappings...")
        mappings = infer_column_mapping(df)
        
        logger.info("Inferred mappings", mappings=mappings)
        
        # Generate data dictionary
        logger.info("Generating data dictionary...")
        data_dict_content = generate_data_dictionary(df, mappings)
        
        # Save data dictionary
        data_dict_path = Path(__file__).parent.parent / "docs" / "data_dictionary.md"
        data_dict_path.write_text(data_dict_content, encoding='utf-8')
        logger.info(f"Saved data dictionary to {data_dict_path}")
        
        # Update mappings file
        update_scripts_with_mappings(mappings)
        
        # Print summary
        print("\n" + "="*80)
        print("AUTOMATIC FIELD MAPPING COMPLETE")
        print("="*80)
        print(f"\n✅ Dataset loaded: {df.shape}")
        print(f"✅ Columns found: {len(df.columns)}")
        print(f"\n📋 Inferred Mappings:")
        for key, value in mappings.items():
            print(f"   {key:15} → {value}")
        
        missing = ['store_id', 'sku_id', 'date_col', 'sales_col']
        missing_found = [m for m in missing if m not in mappings]
        if missing_found:
            print(f"\n⚠️  Missing mappings: {', '.join(missing_found)}")
            print("   Please review and update manually if needed.")
        
        print(f"\n📄 Data dictionary saved to: docs/data_dictionary.md")
        print(f"📄 Mappings saved to: shared/column_mappings.py")
        print("\n✅ You can now use these mappings in your notebooks and scripts!")
        
    except Exception as e:
        logger.error("Failed to auto-map fields", error=str(e), exc_info=True)
        print(f"\n❌ Error: {e}")
        print("\nThis might be because:")
        print("  1. Dataset hasn't been downloaded yet")
        print("  2. Internet connection issue")
        print("  3. Dataset name is incorrect")
        print("\nTry running: python scripts/inspect_dataset.py first")
        raise


if __name__ == "__main__":
    auto_map_fields()


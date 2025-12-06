"""
Script to run EDA analysis on the FreshRetailNet-50K dataset.

This script performs comprehensive EDA and saves results.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from shared.config import get_config
from shared.logging_setup import setup_logging, get_logger
from shared.column_mappings import COLUMN_MAPPINGS
from services.ingestion.datasets import load_freshretailnet_dataset
from services.ingestion.data_quality import validate_data_quality
from shared.utils import add_calendar_features

# Setup
setup_logging()
logger = get_logger(__name__)
config = get_config()

# Set plotting style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Create figures directory
figures_dir = Path("docs/figures")
figures_dir.mkdir(parents=True, exist_ok=True)


def run_eda():
    """Run comprehensive EDA analysis."""
    logger.info("Starting EDA analysis")
    
    # Load dataset
    dataset = load_freshretailnet_dataset(use_local=True)
    df = dataset['train'].to_pandas()
    
    logger.info(f"Dataset loaded: {df.shape}")
    
    # Get column mappings
    store_col = COLUMN_MAPPINGS.get('store_id', 'store_id')
    sku_col = COLUMN_MAPPINGS.get('sku_id', 'product_id')
    date_col = COLUMN_MAPPINGS.get('date_col', 'dt')
    sales_col = COLUMN_MAPPINGS.get('sales_col', 'sale_amount')
    category_col = COLUMN_MAPPINGS.get('category_col', 'first_category_id')
    stockout_col = COLUMN_MAPPINGS.get('stockout_col', 'stock_hour6_22_cnt')
    
    # Convert date column
    if df[date_col].dtype == 'object':
        df[date_col] = pd.to_datetime(df[date_col])
    
    # Add calendar features
    df = add_calendar_features(df, date_col)
    
    print("\n" + "="*80)
    print("EXPLORATORY DATA ANALYSIS - FreshRetailNet-50K")
    print("="*80)
    
    # 1. Basic Statistics
    print("\n1. BASIC STATISTICS")
    print("-" * 80)
    print(f"Total records: {len(df):,}")
    print(f"Date range: {df[date_col].min()} to {df[date_col].max()}")
    print(f"Number of stores: {df[store_col].nunique():,}")
    print(f"Number of products: {df[sku_col].nunique():,}")
    print(f"Number of categories: {df[category_col].nunique():,}")
    print(f"Total sales: {df[sales_col].sum():,.2f}")
    print(f"Average daily sales: {df[sales_col].mean():.2f}")
    
    # 2. Sales Distribution by Category
    print("\n2. SALES BY CATEGORY")
    print("-" * 80)
    category_sales = df.groupby(category_col)[sales_col].agg(['sum', 'mean', 'count'])
    category_sales = category_sales.sort_values('sum', ascending=False)
    print(category_sales.head(10))
    
    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    category_sales['sum'].head(10).plot(kind='bar', ax=axes[0])
    axes[0].set_title('Total Sales by Category (Top 10)')
    axes[0].set_xlabel('Category ID')
    axes[0].set_ylabel('Total Sales')
    axes[0].tick_params(axis='x', rotation=45)
    
    category_sales['mean'].head(10).plot(kind='bar', ax=axes[1])
    axes[1].set_title('Average Sales by Category (Top 10)')
    axes[1].set_xlabel('Category ID')
    axes[1].set_ylabel('Average Sales')
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(figures_dir / 'sales_by_category.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {figures_dir / 'sales_by_category.png'}")
    
    # 3. Stockout Analysis
    print("\n3. STOCKOUT ANALYSIS")
    print("-" * 80)
    if stockout_col in df.columns:
        # Stockout rate (using stock_hour6_22_cnt > 0 as indicator)
        df['has_stockout'] = (df[stockout_col] > 0).astype(int)
        stockout_rate = df['has_stockout'].mean() * 100
        print(f"Overall stockout rate: {stockout_rate:.2f}%")
        print(f"Records with stockouts: {df['has_stockout'].sum():,} / {len(df):,}")
        
        # Stockout by category
        stockout_by_category = df.groupby(category_col)['has_stockout'].agg(['mean', 'sum', 'count'])
        stockout_by_category['rate'] = stockout_by_category['mean'] * 100
        stockout_by_category = stockout_by_category.sort_values('rate', ascending=False)
        print("\nStockout by Category (Top 10):")
        print(stockout_by_category.head(10))
        
        # Visualization
        plt.figure(figsize=(10, 6))
        stockout_by_category['rate'].head(10).plot(kind='bar')
        plt.title('Stockout Rate by Category (Top 10)')
        plt.xlabel('Category ID')
        plt.ylabel('Stockout Rate (%)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(figures_dir / 'stockout_by_category.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[OK] Saved: {figures_dir / 'stockout_by_category.png'}")
    
    # 4. Calendar Effects
    print("\n4. CALENDAR EFFECTS")
    print("-" * 80)
    # Sales by day of week
    dow_sales = df.groupby('dayofweek')[sales_col].agg(['sum', 'mean'])
    dow_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    print("\nSales by Day of Week:")
    print(dow_sales)
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    dow_sales['sum'].plot(kind='bar', ax=axes[0])
    axes[0].set_title('Total Sales by Day of Week')
    axes[0].set_xlabel('Day of Week')
    axes[0].set_ylabel('Total Sales')
    axes[0].set_xticklabels(dow_labels, rotation=0)
    
    dow_sales['mean'].plot(kind='bar', ax=axes[1])
    axes[1].set_title('Average Sales by Day of Week')
    axes[1].set_xlabel('Day of Week')
    axes[1].set_ylabel('Average Sales')
    axes[1].set_xticklabels(dow_labels, rotation=0)
    
    plt.tight_layout()
    plt.savefig(figures_dir / 'sales_by_dayofweek.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {figures_dir / 'sales_by_dayofweek.png'}")
    
    # Weekend vs weekday
    weekend_sales = df.groupby('is_weekend')[sales_col].agg(['sum', 'mean', 'count'])
    print("\nWeekend vs Weekday Sales:")
    print(weekend_sales)
    
    # 5. Weather Impact
    print("\n5. WEATHER IMPACT")
    print("-" * 80)
    weather_col = COLUMN_MAPPINGS.get('weather_col', 'avg_temperature')
    if weather_col in df.columns:
        # Create temperature buckets
        df['temp_bucket'] = pd.cut(df[weather_col], bins=5, labels=['Very Cold', 'Cold', 'Moderate', 'Warm', 'Hot'])
        weather_sales = df.groupby('temp_bucket')[sales_col].agg(['sum', 'mean', 'count'])
        print(weather_sales)
        
        # Visualization
        plt.figure(figsize=(10, 6))
        weather_sales['mean'].plot(kind='bar')
        plt.title('Average Sales by Temperature Bucket')
        plt.xlabel('Temperature Bucket')
        plt.ylabel('Average Sales')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(figures_dir / 'sales_by_temperature.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[OK] Saved: {figures_dir / 'sales_by_temperature.png'}")
    
    # 6. Time Series Overview
    print("\n6. TIME SERIES OVERVIEW")
    print("-" * 80)
    df_daily = df.groupby(date_col)[sales_col].sum().reset_index()
    df_daily = df_daily.sort_values(date_col)
    
    print(f"Date range: {df_daily[date_col].min()} to {df_daily[date_col].max()}")
    print(f"Total days: {(df_daily[date_col].max() - df_daily[date_col].min()).days}")
    print(f"Average daily sales: {df_daily[sales_col].mean():.2f}")
    print(f"Std daily sales: {df_daily[sales_col].std():.2f}")
    
    # Plot time series
    plt.figure(figsize=(15, 6))
    plt.plot(df_daily[date_col], df_daily[sales_col])
    plt.title('Daily Sales Over Time')
    plt.xlabel('Date')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / 'sales_timeseries.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {figures_dir / 'sales_timeseries.png'}")
    
    # 7. Store and Product Analysis
    print("\n7. STORE AND PRODUCT ANALYSIS")
    print("-" * 80)
    store_sales = df.groupby(store_col)[sales_col].agg(['sum', 'mean', 'count'])
    print(f"\nNumber of stores: {df[store_col].nunique():,}")
    print("\nTop 10 stores by total sales:")
    print(store_sales.sort_values('sum', ascending=False).head(10))
    
    product_sales = df.groupby(sku_col)[sales_col].agg(['sum', 'mean', 'count'])
    print(f"\nNumber of products: {df[sku_col].nunique():,}")
    print("\nTop 10 products by total sales:")
    print(product_sales.sort_values('sum', ascending=False).head(10))
    
    # 8. Data Quality Summary
    print("\n8. DATA QUALITY SUMMARY")
    print("-" * 80)
    quality_report = validate_data_quality(df, name="train")
    report = quality_report.generate_report()
    
    print(f"Total rows: {report['summary']['total_rows']:,}")
    print(f"Total columns: {report['summary']['total_columns']}")
    print(f"Total issues: {report['summary']['total_issues']}")
    print(f"Errors: {report['summary']['error_count']}")
    print(f"Warnings: {report['summary']['warning_count']}")
    
    if report['all_issues']:
        print("\nIssues found:")
        for issue in report['all_issues'][:10]:  # Show first 10
            print(f"  - {issue}")
    
    print("\n" + "="*80)
    print("EDA COMPLETE")
    print("="*80)
    print(f"\n[OK] All visualizations saved to: {figures_dir}")
    print(f"[OK] Analysis complete!")
    
    logger.info("EDA analysis completed successfully")


if __name__ == "__main__":
    run_eda()


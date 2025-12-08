"""Generate realistic inventory from FreshRetailNet-50K sales data.

This module provides functions to create inventory snapshots that are
derived from actual sales patterns in the dataset, ensuring consistency
between forecasting and inventory data.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.ingestion.datasets import load_freshretailnet_dataset
from shared.column_mappings import COLUMN_MAPPINGS
from shared.category_shelf_life import get_shelf_life, get_category_name
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class InventoryGenerator:
    """Generates realistic inventory based on sales patterns."""
    
    def __init__(self, coverage_days: int = 5, safety_factor: float = 1.3):
        """Initialize the inventory generator.
        
        Args:
            coverage_days: Number of days of demand to keep in stock
            safety_factor: Multiplier for safety stock (1.0 = no buffer)
        """
        self.coverage_days = coverage_days
        self.safety_factor = safety_factor
        self.df: Optional[pd.DataFrame] = None
        self.cols: Dict[str, str] = {}
        self._load_data()
    
    def _load_data(self):
        """Load FreshRetailNet-50K dataset."""
        try:
            logger.info("Loading FreshRetailNet-50K for inventory generation")
            dataset = load_freshretailnet_dataset(use_local=True)
            self.df = dataset['train'].to_pandas()
            
            # Column mappings
            self.cols = {
                'store': COLUMN_MAPPINGS.get('store_id', 'store_id'),
                'product': COLUMN_MAPPINGS.get('sku_id', 'product_id'),
                'date': COLUMN_MAPPINGS.get('date_col', 'dt'),
                'sales': COLUMN_MAPPINGS.get('sales_col', 'sale_amount'),
                'category': COLUMN_MAPPINGS.get('category_col', 'first_category_id'),
            }
            
            # Normalize types
            self.df[self.cols['store']] = self.df[self.cols['store']].astype(int)
            self.df[self.cols['product']] = self.df[self.cols['product']].astype(int)
            
            logger.info(f"Dataset loaded: {len(self.df):,} records")
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    def get_available_stores(self, limit: int = 10) -> List[int]:
        """Get list of store IDs with most data."""
        store_col = self.cols['store']
        store_counts = self.df[store_col].value_counts().head(limit)
        return store_counts.index.tolist()
    
    def get_products_for_store(self, store_id: int, limit: int = 50) -> List[Dict]:
        """Get products for a store with their category info.
        
        Args:
            store_id: Store ID to get products for
            limit: Maximum number of products
            
        Returns:
            List of product info dicts
        """
        store_col = self.cols['store']
        product_col = self.cols['product']
        category_col = self.cols['category']
        sales_col = self.cols['sales']
        
        # Filter to store
        store_df = self.df[self.df[store_col] == store_id]
        
        # Get products with highest sales volume
        product_sales = store_df.groupby([product_col, category_col])[sales_col].sum()
        product_sales = product_sales.reset_index()
        product_sales = product_sales.sort_values(sales_col, ascending=False)
        product_sales = product_sales.head(limit)
        
        products = []
        for _, row in product_sales.iterrows():
            product_id = int(row[product_col])
            category_id = int(row[category_col])
            products.append({
                'product_id': product_id,
                'sku_id': str(product_id),  # Use product_id as SKU
                'category_id': category_id,
                'category_name': get_category_name(category_id),
                'shelf_life_days': get_shelf_life(category_id),
                'total_sales': float(row[sales_col])
            })
        
        return products
    
    def calculate_daily_demand(self, store_id: int, product_id: int) -> float:
        """Calculate average daily demand for a product at a store.
        
        Args:
            store_id: Store ID
            product_id: Product ID
            
        Returns:
            Average daily sales quantity
        """
        store_col = self.cols['store']
        product_col = self.cols['product']
        date_col = self.cols['date']
        sales_col = self.cols['sales']
        
        # Filter to store and product
        mask = (
            (self.df[store_col] == store_id) &
            (self.df[product_col] == product_id)
        )
        product_df = self.df[mask]
        
        if len(product_df) == 0:
            return 0.0
        
        # Calculate average daily sales
        daily_sales = product_df.groupby(date_col)[sales_col].sum()
        return float(daily_sales.mean())
    
    def generate_inventory_snapshot(
        self,
        store_id: int,
        product_id: int,
        category_id: int,
        avg_daily_demand: float,
        reference_date: Optional[date] = None
    ) -> Dict:
        """Generate a single inventory snapshot for a product.
        
        Args:
            store_id: Store ID
            product_id: Product ID
            category_id: Category ID for shelf life lookup
            avg_daily_demand: Average daily demand
            reference_date: Date for the snapshot (defaults to today)
            
        Returns:
            Dict with inventory snapshot data
        """
        if reference_date is None:
            reference_date = date.today()
        
        shelf_life_days = get_shelf_life(category_id)
        
        # Calculate base inventory (demand * coverage * safety)
        base_inventory = avg_daily_demand * self.coverage_days * self.safety_factor
        
        # Add some realistic variation (-10% to +10%)
        import random
        variation = random.uniform(0.9, 1.1)
        total_quantity = max(10, round(base_inventory * variation))
        
        # Split between shelf and backroom (60-70% on shelf)
        shelf_ratio = random.uniform(0.60, 0.70)
        shelf_quantity = round(total_quantity * shelf_ratio)
        backroom_quantity = total_quantity - shelf_quantity
        
        # Calculate days until expiry based on shelf life
        # Products have varying ages - use random portion of shelf life remaining
        age_factor = random.uniform(0.3, 0.7)  # Product is 30-70% through its shelf life
        days_until_expiry = max(1, int(shelf_life_days * (1 - age_factor)))
        expiry_date = reference_date + timedelta(days=days_until_expiry)
        
        # Generate CONSISTENT expiry buckets from days_until_expiry
        # This is the key fix - buckets are DERIVED, not random
        expiry_buckets = self._derive_expiry_buckets(
            total_quantity, 
            days_until_expiry, 
            shelf_life_days
        )
        
        # In-transit (occasionally some stock coming)
        in_transit = random.randint(0, 15) if random.random() > 0.7 else 0
        
        # Items to discard (only if very close to expiry)
        to_discard = random.randint(0, 3) if days_until_expiry <= 2 else 0
        
        # Sold today (based on demand with some variation)
        sold_today = max(0, int(avg_daily_demand * random.uniform(0.7, 1.3)))
        
        return {
            'store_id': store_id,
            'product_id': product_id,
            'sku_id': str(product_id),
            'category_id': category_id,
            'category_name': get_category_name(category_id),
            'snapshot_date': reference_date,
            'quantity': float(total_quantity),
            'shelf_quantity': float(shelf_quantity),
            'backroom_quantity': float(backroom_quantity),
            'expiry_date': expiry_date,
            'days_until_expiry': days_until_expiry,
            'expiry_buckets': expiry_buckets,
            'in_transit': float(in_transit),
            'to_discard': float(to_discard),
            'sold_today': float(sold_today),
            'avg_daily_demand': avg_daily_demand,
            'shelf_life_days': shelf_life_days,
        }
    
    def _derive_expiry_buckets(
        self, 
        total_quantity: int, 
        days_until_expiry: int,
        shelf_life_days: int
    ) -> Dict[str, int]:
        """Derive expiry buckets from days until expiry.
        
        This ensures consistency between days_until_expiry and the bucket distribution.
        Items are distributed based on the earliest expiry being days_until_expiry away.
        
        Args:
            total_quantity: Total inventory quantity
            days_until_expiry: Days until first items expire
            shelf_life_days: Product's shelf life
            
        Returns:
            Dict with 1_3, 4_7, 8_plus bucket quantities
        """
        # Distribute inventory based on days_until_expiry
        if days_until_expiry <= 3:
            # Most items expiring soon
            bucket_1_3 = int(total_quantity * 0.6)  # 60% in 1-3 days
            bucket_4_7 = int(total_quantity * 0.3)  # 30% in 4-7 days
            bucket_8_plus = total_quantity - bucket_1_3 - bucket_4_7
        elif days_until_expiry <= 7:
            # Mix of soon and medium expiry
            bucket_1_3 = int(total_quantity * 0.15)  # 15% in 1-3 days
            bucket_4_7 = int(total_quantity * 0.50)  # 50% in 4-7 days
            bucket_8_plus = total_quantity - bucket_1_3 - bucket_4_7
        else:
            # Most items have longer shelf life
            bucket_1_3 = int(total_quantity * 0.05)  # 5% in 1-3 days
            bucket_4_7 = int(total_quantity * 0.15)  # 15% in 4-7 days
            bucket_8_plus = total_quantity - bucket_1_3 - bucket_4_7
        
        return {
            "1_3": max(0, bucket_1_3),
            "4_7": max(0, bucket_4_7),
            "8_plus": max(0, bucket_8_plus)
        }
    
    def generate_store_inventory(
        self,
        store_id: int,
        max_products: int = 50,
        reference_date: Optional[date] = None
    ) -> List[Dict]:
        """Generate complete inventory for a store.
        
        Args:
            store_id: Store to generate inventory for
            max_products: Maximum number of products
            reference_date: Date for snapshots
            
        Returns:
            List of inventory snapshot dicts
        """
        if reference_date is None:
            reference_date = date.today()
        
        products = self.get_products_for_store(store_id, limit=max_products)
        inventory = []
        
        for prod in products:
            avg_demand = self.calculate_daily_demand(store_id, prod['product_id'])
            
            if avg_demand > 0:  # Only include products with actual sales
                snapshot = self.generate_inventory_snapshot(
                    store_id=store_id,
                    product_id=prod['product_id'],
                    category_id=prod['category_id'],
                    avg_daily_demand=avg_demand,
                    reference_date=reference_date
                )
                inventory.append(snapshot)
        
        logger.info(f"Generated {len(inventory)} inventory items for store {store_id}")
        return inventory


def get_inventory_generator(
    coverage_days: int = 5, 
    safety_factor: float = 1.3
) -> InventoryGenerator:
    """Get or create an inventory generator instance."""
    return InventoryGenerator(coverage_days=coverage_days, safety_factor=safety_factor)


if __name__ == "__main__":
    # Test the generator
    print("Testing Inventory Generator")
    print("=" * 50)
    
    generator = InventoryGenerator()
    
    # Get available stores
    stores = generator.get_available_stores(limit=5)
    print(f"Top 5 stores by data volume: {stores}")
    
    # Generate inventory for first store
    if stores:
        test_store = stores[0]
        inventory = generator.generate_store_inventory(test_store, max_products=5)
        
        print(f"\nSample inventory for store {test_store}:")
        for item in inventory[:3]:
            print(f"  - Product {item['sku_id']} ({item['category_name']})")
            print(f"    Quantity: {item['quantity']:.0f} (shelf: {item['shelf_quantity']:.0f}, backroom: {item['backroom_quantity']:.0f})")
            print(f"    Expiry: {item['expiry_date']} ({item['days_until_expiry']} days)")
            print(f"    Buckets: {item['expiry_buckets']}")
            print()

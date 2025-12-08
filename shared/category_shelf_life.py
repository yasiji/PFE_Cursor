"""Category to shelf life mapping for FreshRetailNet-50K dataset.

Maps numeric category IDs to human-readable names and shelf life in days.
Based on common retail fresh product categories.
"""

# FreshRetailNet-50K uses numeric category IDs (first_category_id)
# This mapping provides shelf life based on product perishability

CATEGORY_INFO = {
    # Highly perishable (1-3 days)
    0: {"name": "Fresh Prepared Foods", "shelf_life_days": 2},
    28: {"name": "Fresh Bakery", "shelf_life_days": 3},
    29: {"name": "Deli & Ready Meals", "shelf_life_days": 3},
    
    # Perishable (4-7 days)  
    5: {"name": "Fresh Fruits", "shelf_life_days": 7},
    11: {"name": "Fresh Vegetables", "shelf_life_days": 5},
    30: {"name": "Fresh Meat & Poultry", "shelf_life_days": 4},
    
    # Semi-perishable (7-14 days)
    4: {"name": "Dairy Products", "shelf_life_days": 14},
    8: {"name": "Eggs", "shelf_life_days": 21},
    10: {"name": "Fresh Juice", "shelf_life_days": 10},
    
    # Longer shelf life (14+ days)
    16: {"name": "Cheese", "shelf_life_days": 30},
    18: {"name": "Yogurt & Fermented", "shelf_life_days": 21},
    20: {"name": "Packaged Salads", "shelf_life_days": 7},
    22: {"name": "Fresh Pasta", "shelf_life_days": 14},
    23: {"name": "Fresh Sauces", "shelf_life_days": 14},
    25: {"name": "Organic Produce", "shelf_life_days": 5},
}

# Default for unknown categories
DEFAULT_CATEGORY = {"name": "Other Fresh Products", "shelf_life_days": 7}


def get_category_info(category_id: int) -> dict:
    """Get category name and shelf life for a category ID.
    
    Args:
        category_id: Numeric category ID from FreshRetailNet-50K
        
    Returns:
        Dict with 'name' and 'shelf_life_days' keys
    """
    return CATEGORY_INFO.get(category_id, DEFAULT_CATEGORY)


def get_shelf_life(category_id: int) -> int:
    """Get shelf life in days for a category.
    
    Args:
        category_id: Numeric category ID
        
    Returns:
        Shelf life in days
    """
    return get_category_info(category_id)["shelf_life_days"]


def get_category_name(category_id: int) -> str:
    """Get human-readable category name.
    
    Args:
        category_id: Numeric category ID
        
    Returns:
        Category name string
    """
    return get_category_info(category_id)["name"]

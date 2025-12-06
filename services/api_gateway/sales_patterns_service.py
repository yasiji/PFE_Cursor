"""Sales pattern analysis service - analyzes sales by day-of-week, holidays, weather."""

from datetime import date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import pandas as pd

from services.api_gateway.models import Store
from services.api_gateway.sales_data_service import get_sales_service
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def analyze_day_of_week_patterns(
    db: Session,
    store_id: str,
    period_days: int = 90
) -> Dict:
    """
    Analyze sales patterns by day of week.
    
    Args:
        db: Database session
        store_id: Store identifier
        period_days: Number of days to analyze
        
    Returns:
        Dict with day-of-week patterns
    """
    sales_service = get_sales_service()
    
    if sales_service.df is None:
        return {
            'patterns': {},
            'error': 'Dataset not loaded'
        }
    
    # Get effective date range
    today = date.today()
    if sales_service.latest_date and today > sales_service.latest_date:
        end_date = sales_service.latest_date
    else:
        end_date = today
    
    start_date = end_date - timedelta(days=period_days)
    
    # Get sales data
    sales_data = sales_service.get_store_sales(
        store_id=store_id,
        start_date=start_date,
        end_date=end_date
    )
    
    if not sales_data:
        return {
            'patterns': {},
            'error': 'No sales data found'
        }
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(sales_data)
    df['date'] = pd.to_datetime(df['date'])
    df['day_of_week'] = df['date'].dt.day_name()
    df['day_of_week_num'] = df['date'].dt.dayofweek  # 0=Monday, 6=Sunday
    
    # Aggregate by day of week
    day_patterns = df.groupby('day_of_week').agg({
        'sales': ['mean', 'sum', 'count'],
        'revenue': ['mean', 'sum'],
        'items_sold': 'sum'
    }).round(2)
    
    # Format results
    patterns = {}
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day_num, day_name in enumerate(day_names):
        day_data = df[df['day_of_week_num'] == day_num]
        if len(day_data) > 0:
            patterns[day_name] = {
                'avg_sales': float(day_data['sales'].mean()),
                'total_sales': float(day_data['sales'].sum()),
                'avg_revenue': float(day_data['revenue'].mean()),
                'total_revenue': float(day_data['revenue'].sum()),
                'total_items': int(day_data['items_sold'].sum()),
                'occurrences': len(day_data)
            }
        else:
            patterns[day_name] = {
                'avg_sales': 0.0,
                'total_sales': 0.0,
                'avg_revenue': 0.0,
                'total_revenue': 0.0,
                'total_items': 0,
                'occurrences': 0
            }
    
    # Find best and worst days
    best_day = max(patterns.items(), key=lambda x: x[1]['avg_sales'])
    worst_day = min(patterns.items(), key=lambda x: x[1]['avg_sales'] if x[1]['occurrences'] > 0 else float('inf'))
    
    return {
        'patterns': patterns,
        'best_day': {
            'day': best_day[0],
            'avg_sales': best_day[1]['avg_sales']
        },
        'worst_day': {
            'day': worst_day[0],
            'avg_sales': worst_day[1]['avg_sales'] if worst_day[1]['occurrences'] > 0 else 0.0
        },
        'period_days': period_days,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }


def analyze_weather_patterns(
    db: Session,
    store_id: str,
    period_days: int = 90
) -> Dict:
    """
    Analyze sales patterns by weather conditions.
    
    Args:
        db: Database session
        store_id: Store identifier
        period_days: Number of days to analyze
        
    Returns:
        Dict with weather patterns
    """
    sales_service = get_sales_service()
    
    if sales_service.df is None:
        return {
            'patterns': {},
            'error': 'Dataset not loaded'
        }
    
    # Get the raw dataset
    df = sales_service.df.copy()
    
    # Get column mappings
    store_col = sales_service.cols['store_col']
    date_col = sales_service.cols['date_col']
    sales_col = sales_service.cols['sales_col']
    
    # Get effective date range
    today = date.today()
    if sales_service.latest_date and today > sales_service.latest_date:
        end_date = sales_service.latest_date
    else:
        end_date = today
    
    start_date = end_date - timedelta(days=period_days)
    
    # Filter by store and date
    mask = (
        (df[store_col] == str(store_id)) &
        (df[date_col] >= start_date) &
        (df[date_col] <= end_date)
    )
    filtered_df = df[mask].copy()
    
    if len(filtered_df) == 0:
        return {
            'patterns': {},
            'error': 'No sales data found'
        }
    
    # Check if weather columns exist
    weather_patterns = {}
    
    # Try to find temperature column
    temp_cols = [col for col in filtered_df.columns if 'temp' in col.lower() or 'temperature' in col.lower()]
    if temp_cols:
        temp_col = temp_cols[0]
        # Create temperature buckets
        filtered_df['temp_bucket'] = pd.cut(
            filtered_df[temp_col],
            bins=[-float('inf'), 0, 10, 20, 30, float('inf')],
            labels=['Very Cold', 'Cold', 'Moderate', 'Warm', 'Hot']
        )
        
        temp_patterns = filtered_df.groupby('temp_bucket').agg({
            sales_col: ['mean', 'sum', 'count']
        }).round(2)
        
        weather_patterns['temperature'] = {}
        for bucket in ['Very Cold', 'Cold', 'Moderate', 'Warm', 'Hot']:
            bucket_data = filtered_df[filtered_df['temp_bucket'] == bucket]
            if len(bucket_data) > 0:
                weather_patterns['temperature'][bucket] = {
                    'avg_sales': float(bucket_data[sales_col].mean()),
                    'total_sales': float(bucket_data[sales_col].sum()),
                    'occurrences': len(bucket_data)
                }
            else:
                weather_patterns['temperature'][bucket] = {
                    'avg_sales': 0.0,
                    'total_sales': 0.0,
                    'occurrences': 0
                }
    
    # Try to find precipitation column
    prec_cols = [col for col in filtered_df.columns if 'prec' in col.lower() or 'rain' in col.lower() or 'precipitation' in col.lower()]
    if prec_cols:
        prec_col = prec_cols[0]
        # Create precipitation buckets
        filtered_df['prec_bucket'] = pd.cut(
            filtered_df[prec_col],
            bins=[-float('inf'), 0, 5, 20, float('inf')],
            labels=['No Rain', 'Light Rain', 'Moderate Rain', 'Heavy Rain']
        )
        
        prec_patterns = filtered_df.groupby('prec_bucket').agg({
            sales_col: ['mean', 'sum', 'count']
        }).round(2)
        
        weather_patterns['precipitation'] = {}
        for bucket in ['No Rain', 'Light Rain', 'Moderate Rain', 'Heavy Rain']:
            bucket_data = filtered_df[filtered_df['prec_bucket'] == bucket]
            if len(bucket_data) > 0:
                weather_patterns['precipitation'][bucket] = {
                    'avg_sales': float(bucket_data[sales_col].mean()),
                    'total_sales': float(bucket_data[sales_col].sum()),
                    'occurrences': len(bucket_data)
                }
            else:
                weather_patterns['precipitation'][bucket] = {
                    'avg_sales': 0.0,
                    'total_sales': 0.0,
                    'occurrences': 0
                }
    
    return {
        'patterns': weather_patterns,
        'period_days': period_days,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }


def analyze_holiday_patterns(
    db: Session,
    store_id: str,
    period_days: int = 365
) -> Dict:
    """
    Analyze sales patterns around holidays.
    
    Note: This is a placeholder - would need holiday calendar data.
    
    Args:
        db: Database session
        store_id: Store identifier
        period_days: Number of days to analyze
        
    Returns:
        Dict with holiday patterns
    """
    # TODO: Implement holiday detection if holiday column exists in dataset
    # For now, return placeholder
    
    return {
        'patterns': {},
        'note': 'Holiday analysis requires holiday calendar data',
        'period_days': period_days
    }


def get_sales_patterns(
    db: Session,
    store_id: str,
    period_days: int = 90
) -> Dict:
    """
    Get comprehensive sales pattern analysis.
    
    Args:
        db: Database session
        store_id: Store identifier
        period_days: Number of days to analyze
        
    Returns:
        Dict with all pattern analyses
    """
    day_patterns = analyze_day_of_week_patterns(db, store_id, period_days)
    weather_patterns = analyze_weather_patterns(db, store_id, period_days)
    holiday_patterns = analyze_holiday_patterns(db, store_id, period_days)
    
    return {
        'day_of_week': day_patterns,
        'weather': weather_patterns,
        'holidays': holiday_patterns
    }


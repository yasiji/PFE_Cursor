"""
Settings API routes for user preferences and store settings.

Provides endpoints for:
- User notification preferences
- Store display settings
- Dashboard customization
"""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.api_gateway.database import get_db
from services.api_gateway.models import User, Store
from services.api_gateway.auth import get_current_user
from shared.logging_setup import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

# In-memory settings storage (in production, this would be in database)
# Key: user_id, Value: settings dict
_user_settings: Dict[int, Dict[str, Any]] = {}

# Default settings
DEFAULT_SETTINGS = {
    "notifications": {
        "email_enabled": True,
        "push_enabled": True,
        "low_stock_alerts": True,
        "expiry_alerts": True,
        "order_alerts": True,
        "daily_summary": True,
        "alert_threshold_low_stock": 10,
        "alert_threshold_expiry_days": 3
    },
    "dashboard": {
        "default_time_range": "7d",
        "show_profit": True,
        "show_loss": True,
        "auto_refresh": True,
        "refresh_interval_seconds": 30,
        "chart_type": "line"
    },
    "display": {
        "date_format": "MMM dd, yyyy",
        "currency": "USD",
        "currency_symbol": "$",
        "timezone": "America/New_York",
        "theme": "light",
        "compact_mode": False
    },
    "forecast": {
        "default_horizon_days": 7,
        "show_uncertainty_bounds": True,
        "include_weather": True,
        "include_holidays": True
    }
}


class NotificationSettings(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    low_stock_alerts: Optional[bool] = None
    expiry_alerts: Optional[bool] = None
    order_alerts: Optional[bool] = None
    daily_summary: Optional[bool] = None
    alert_threshold_low_stock: Optional[int] = None
    alert_threshold_expiry_days: Optional[int] = None


class DashboardSettings(BaseModel):
    default_time_range: Optional[str] = None
    show_profit: Optional[bool] = None
    show_loss: Optional[bool] = None
    auto_refresh: Optional[bool] = None
    refresh_interval_seconds: Optional[int] = None
    chart_type: Optional[str] = None


class DisplaySettings(BaseModel):
    date_format: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    compact_mode: Optional[bool] = None


class ForecastSettings(BaseModel):
    default_horizon_days: Optional[int] = None
    show_uncertainty_bounds: Optional[bool] = None
    include_weather: Optional[bool] = None
    include_holidays: Optional[bool] = None


class AllSettings(BaseModel):
    notifications: Optional[NotificationSettings] = None
    dashboard: Optional[DashboardSettings] = None
    display: Optional[DisplaySettings] = None
    forecast: Optional[ForecastSettings] = None


def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Get settings for a user, with defaults."""
    if user_id not in _user_settings:
        _user_settings[user_id] = DEFAULT_SETTINGS.copy()
    return _user_settings[user_id]


def update_nested_dict(base: Dict, updates: Dict) -> Dict:
    """Update nested dictionary with non-None values."""
    result = base.copy()
    for key, value in updates.items():
        if value is not None:
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = update_nested_dict(result[key], value)
            else:
                result[key] = value
    return result


@router.get("")
async def get_all_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all settings for the current user.
    """
    settings = get_user_settings(current_user.id)
    
    return {
        "user_id": current_user.id,
        "settings": settings,
        "defaults": DEFAULT_SETTINGS,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.put("")
async def update_all_settings(
    settings: AllSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update multiple settings at once.
    """
    current_settings = get_user_settings(current_user.id)
    
    # Update each section if provided
    if settings.notifications:
        current_settings["notifications"] = update_nested_dict(
            current_settings.get("notifications", {}),
            settings.notifications.dict(exclude_none=True)
        )
    
    if settings.dashboard:
        current_settings["dashboard"] = update_nested_dict(
            current_settings.get("dashboard", {}),
            settings.dashboard.dict(exclude_none=True)
        )
    
    if settings.display:
        current_settings["display"] = update_nested_dict(
            current_settings.get("display", {}),
            settings.display.dict(exclude_none=True)
        )
    
    if settings.forecast:
        current_settings["forecast"] = update_nested_dict(
            current_settings.get("forecast", {}),
            settings.forecast.dict(exclude_none=True)
        )
    
    _user_settings[current_user.id] = current_settings
    
    logger.info(f"Updated settings for user {current_user.id}")
    
    return {
        "message": "Settings updated successfully",
        "settings": current_settings,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.get("/notifications")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification settings for the current user."""
    settings = get_user_settings(current_user.id)
    return settings.get("notifications", DEFAULT_SETTINGS["notifications"])


@router.put("/notifications")
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update notification settings."""
    current_settings = get_user_settings(current_user.id)
    current_settings["notifications"] = update_nested_dict(
        current_settings.get("notifications", {}),
        settings.dict(exclude_none=True)
    )
    _user_settings[current_user.id] = current_settings
    
    return {
        "message": "Notification settings updated",
        "settings": current_settings["notifications"]
    }


@router.get("/dashboard")
async def get_dashboard_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard settings for the current user."""
    settings = get_user_settings(current_user.id)
    return settings.get("dashboard", DEFAULT_SETTINGS["dashboard"])


@router.put("/dashboard")
async def update_dashboard_settings(
    settings: DashboardSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update dashboard settings."""
    current_settings = get_user_settings(current_user.id)
    current_settings["dashboard"] = update_nested_dict(
        current_settings.get("dashboard", {}),
        settings.dict(exclude_none=True)
    )
    _user_settings[current_user.id] = current_settings
    
    return {
        "message": "Dashboard settings updated",
        "settings": current_settings["dashboard"]
    }


@router.get("/display")
async def get_display_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get display settings for the current user."""
    settings = get_user_settings(current_user.id)
    return settings.get("display", DEFAULT_SETTINGS["display"])


@router.put("/display")
async def update_display_settings(
    settings: DisplaySettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update display settings."""
    current_settings = get_user_settings(current_user.id)
    current_settings["display"] = update_nested_dict(
        current_settings.get("display", {}),
        settings.dict(exclude_none=True)
    )
    _user_settings[current_user.id] = current_settings
    
    return {
        "message": "Display settings updated",
        "settings": current_settings["display"]
    }


@router.get("/forecast")
async def get_forecast_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get forecast settings for the current user."""
    settings = get_user_settings(current_user.id)
    return settings.get("forecast", DEFAULT_SETTINGS["forecast"])


@router.put("/forecast")
async def update_forecast_settings(
    settings: ForecastSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update forecast settings."""
    current_settings = get_user_settings(current_user.id)
    current_settings["forecast"] = update_nested_dict(
        current_settings.get("forecast", {}),
        settings.dict(exclude_none=True)
    )
    _user_settings[current_user.id] = current_settings
    
    return {
        "message": "Forecast settings updated",
        "settings": current_settings["forecast"]
    }


@router.post("/reset")
async def reset_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset all settings to defaults."""
    _user_settings[current_user.id] = DEFAULT_SETTINGS.copy()
    
    return {
        "message": "Settings reset to defaults",
        "settings": DEFAULT_SETTINGS
    }


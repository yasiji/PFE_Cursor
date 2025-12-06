"""
Unified Demand Factors Service.

Combines weather, holidays, and day-of-week factors into a single service
that all forecast and replenishment services can use consistently.

This ensures all services use the same real-time data from:
- Open-Meteo API (weather)
- Nager.Date API (holidays)
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List

from services.api_gateway.weather_service import get_weather_service, WeatherService
from services.api_gateway.holiday_service import get_holiday_service, HolidayService
from shared.logging_setup import get_logger

logger = get_logger(__name__)

# Day of week demand factors
DAY_OF_WEEK_FACTORS = {
    0: {"name": "Monday", "factor": 0.85, "description": "Monday - typically lower traffic"},
    1: {"name": "Tuesday", "factor": 0.88, "description": "Tuesday - still slow start"},
    2: {"name": "Wednesday", "factor": 0.95, "description": "Wednesday - mid-week pickup"},
    3: {"name": "Thursday", "factor": 1.00, "description": "Thursday - steady traffic"},
    4: {"name": "Friday", "factor": 1.15, "description": "Friday - weekend prep shopping"},
    5: {"name": "Saturday", "factor": 1.30, "description": "Saturday - peak shopping day"},
    6: {"name": "Sunday", "factor": 1.10, "description": "Sunday - moderate traffic"},
}


class DemandFactorsService:
    """
    Unified service for all demand-affecting factors.
    
    Combines:
    - Real-time weather data (Open-Meteo API)
    - Real holiday calendar (Nager.Date API)
    - Day-of-week patterns
    
    Returns consistent factor data for forecasting and replenishment.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.weather_service = get_weather_service()
        self.holiday_service = get_holiday_service()
    
    def get_all_factors(
        self,
        store_id: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Get all demand factors for a specific store and date.
        
        Args:
            store_id: Store identifier
            target_date: Target date
            
        Returns:
            Dict containing all factors and combined multiplier
        """
        # Get day of week factor
        day_of_week = target_date.weekday()
        day_info = DAY_OF_WEEK_FACTORS[day_of_week]
        day_factor = day_info["factor"]
        is_weekend = day_of_week >= 5
        
        # Get weather factor (real-time from Open-Meteo)
        weather_data = self.weather_service.get_weather_factor_for_date(store_id, target_date)
        weather_factor = weather_data.get("weather_factor", 1.0)
        
        # Get holiday factor (real-time from Nager.Date)
        holiday_data = self.holiday_service.get_holiday_factor_for_date(store_id, target_date)
        holiday_factor = holiday_data.get("factor", 1.0)
        is_holiday = holiday_data.get("is_holiday", False)
        is_pre_holiday = holiday_data.get("is_pre_holiday", False)
        
        # Calculate combined seasonality factor
        # Using weighted combination: day (30%) + weather (35%) + holiday (35%)
        # Note: Holiday gets high weight because of significant impact on retail
        combined_factor = (
            day_factor * 0.30 +
            weather_factor * 0.35 +
            holiday_factor * 0.35
        )
        
        # If it's a major holiday, give more weight to holiday factor
        if is_holiday and holiday_factor > 1.2:
            combined_factor = (
                day_factor * 0.20 +
                weather_factor * 0.25 +
                holiday_factor * 0.55
            )
        
        return {
            "date": target_date.isoformat(),
            "store_id": store_id,
            
            # Day of week
            "day_of_week": day_info["name"],
            "day_of_week_index": day_of_week,
            "is_weekend": is_weekend,
            "day_factor": round(day_factor, 3),
            "day_description": day_info["description"],
            
            # Weather (real-time)
            "weather": weather_data.get("weather", "unknown"),
            "temperature": weather_data.get("temperature"),
            "temperature_category": weather_data.get("temperature_category", "mild"),
            "weather_factor": round(weather_factor, 3),
            "weather_description": weather_data.get("description", ""),
            "weather_source": weather_data.get("source", "Unknown"),
            
            # Holiday (real-time)
            "is_holiday": is_holiday,
            "is_pre_holiday": is_pre_holiday,
            "holiday_name": holiday_data.get("name"),
            "holiday_factor": round(holiday_factor, 3),
            "holiday_description": holiday_data.get("description", ""),
            "holiday_source": holiday_data.get("source", "Unknown"),
            
            # Combined
            "seasonality_factor": round(combined_factor, 3),
            "factors_applied": {
                "day_weight": 0.30 if not (is_holiday and holiday_factor > 1.2) else 0.20,
                "weather_weight": 0.35 if not (is_holiday and holiday_factor > 1.2) else 0.25,
                "holiday_weight": 0.35 if not (is_holiday and holiday_factor > 1.2) else 0.55
            },
            
            # Metadata
            "generated_at": datetime.now().isoformat(),
            "data_sources": {
                "weather": "Open-Meteo API (real-time)",
                "holidays": "Nager.Date API (real-time)",
                "day_of_week": "Static patterns"
            }
        }
    
    def get_factors_range(
        self,
        store_id: str,
        start_date: date,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get demand factors for a range of dates.
        
        Args:
            store_id: Store identifier
            start_date: Start date
            days: Number of days
            
        Returns:
            List of factor dictionaries for each day
        """
        factors_list = []
        
        for i in range(days):
            target_date = start_date + timedelta(days=i)
            factors = self.get_all_factors(store_id, target_date)
            factors_list.append(factors)
        
        return factors_list
    
    def get_weather_forecast(
        self,
        store_id: str,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """Get weather forecast for a store."""
        return self.weather_service.get_weather_forecast(
            store_id, 
            date.today(), 
            days_ahead
        )
    
    def get_upcoming_holidays(
        self,
        store_id: str,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get upcoming holidays for a store."""
        return self.holiday_service.get_upcoming_holidays(store_id, days_ahead)
    
    def get_demand_summary(
        self,
        store_id: str,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Get a summary of demand factors for the upcoming period.
        
        Args:
            store_id: Store identifier
            days_ahead: Number of days to summarize
            
        Returns:
            Summary with averages, highs, lows, and notable days
        """
        factors_list = self.get_factors_range(store_id, date.today(), days_ahead)
        
        if not factors_list:
            return {"error": "No data available"}
        
        # Calculate statistics
        seasonality_factors = [f["seasonality_factor"] for f in factors_list]
        
        # Find notable days
        high_demand_days = [f for f in factors_list if f["seasonality_factor"] > 1.15]
        low_demand_days = [f for f in factors_list if f["seasonality_factor"] < 0.90]
        holiday_days = [f for f in factors_list if f["is_holiday"] or f["is_pre_holiday"]]
        
        return {
            "store_id": store_id,
            "period": {
                "start": factors_list[0]["date"],
                "end": factors_list[-1]["date"],
                "days": days_ahead
            },
            "statistics": {
                "average_factor": round(sum(seasonality_factors) / len(seasonality_factors), 3),
                "max_factor": round(max(seasonality_factors), 3),
                "min_factor": round(min(seasonality_factors), 3),
            },
            "notable_days": {
                "high_demand_count": len(high_demand_days),
                "high_demand_days": [
                    {"date": d["date"], "factor": d["seasonality_factor"], "reason": d.get("holiday_name") or d["day_of_week"]}
                    for d in high_demand_days
                ],
                "low_demand_count": len(low_demand_days),
                "low_demand_days": [
                    {"date": d["date"], "factor": d["seasonality_factor"], "reason": d["weather"]}
                    for d in low_demand_days
                ],
                "holidays": [
                    {"date": d["date"], "name": d["holiday_name"], "factor": d["holiday_factor"]}
                    for d in holiday_days
                ]
            },
            "daily_factors": factors_list,
            "generated_at": datetime.now().isoformat()
        }


# Global singleton instance
_demand_factors_service_instance: Optional[DemandFactorsService] = None


def get_demand_factors_service() -> DemandFactorsService:
    """Get or create the global DemandFactorsService singleton."""
    global _demand_factors_service_instance
    if _demand_factors_service_instance is None:
        _demand_factors_service_instance = DemandFactorsService()
    return _demand_factors_service_instance


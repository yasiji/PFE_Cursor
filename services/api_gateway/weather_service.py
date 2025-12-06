"""
Real Weather Service using Open-Meteo API.

Open-Meteo is a free, open-source weather API that requires no API key.
Documentation: https://open-meteo.com/en/docs

This service provides:
- Current weather conditions
- Weather forecasts up to 16 days
- Historical weather data
"""

import httpx
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import lru_cache
import asyncio

from shared.logging_setup import get_logger

logger = get_logger(__name__)

# Open-Meteo API base URL (free, no API key required)
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Default coordinates (can be overridden per store)
# Default: New York City area for demo
DEFAULT_LATITUDE = 40.7128
DEFAULT_LONGITUDE = -74.0060

# Store coordinates mapping (store_id -> (lat, lon))
# In production, this would come from the database
STORE_COORDINATES = {
    "235": (40.7128, -74.0060),   # NYC
    "100": (34.0522, -118.2437),  # Los Angeles
    "150": (41.8781, -87.6298),   # Chicago
    "200": (29.7604, -95.3698),   # Houston
    "250": (33.4484, -112.0740),  # Phoenix
}

# Weather impact factors on demand
WEATHER_IMPACT_FACTORS = {
    # Temperature ranges (Celsius) and their impact
    "very_cold": {"range": (-50, 0), "factor": 0.85, "description": "Very cold - reduced foot traffic"},
    "cold": {"range": (0, 10), "factor": 0.92, "description": "Cold - slightly reduced demand"},
    "mild": {"range": (10, 20), "factor": 1.0, "description": "Mild - normal demand"},
    "warm": {"range": (20, 28), "factor": 1.08, "description": "Warm - increased demand for fresh/cold items"},
    "hot": {"range": (28, 50), "factor": 1.15, "description": "Hot - high demand for cold beverages/produce"},
    
    # Weather condition impacts
    "rain": {"factor": 0.88, "description": "Rainy - reduced store visits"},
    "snow": {"factor": 0.75, "description": "Snowy - significantly reduced traffic"},
    "storm": {"factor": 0.65, "description": "Stormy - major reduction in visits"},
    "clear": {"factor": 1.05, "description": "Clear/sunny - good shopping weather"},
    "cloudy": {"factor": 0.98, "description": "Cloudy - slight reduction"},
}

# Weather code mapping from Open-Meteo
# https://open-meteo.com/en/docs#weathervariables
WEATHER_CODE_MAP = {
    0: "clear",        # Clear sky
    1: "clear",        # Mainly clear
    2: "cloudy",       # Partly cloudy
    3: "cloudy",       # Overcast
    45: "cloudy",      # Fog
    48: "cloudy",      # Depositing rime fog
    51: "rain",        # Light drizzle
    53: "rain",        # Moderate drizzle
    55: "rain",        # Dense drizzle
    56: "rain",        # Light freezing drizzle
    57: "rain",        # Dense freezing drizzle
    61: "rain",        # Slight rain
    63: "rain",        # Moderate rain
    65: "rain",        # Heavy rain
    66: "rain",        # Light freezing rain
    67: "rain",        # Heavy freezing rain
    71: "snow",        # Slight snow
    73: "snow",        # Moderate snow
    75: "snow",        # Heavy snow
    77: "snow",        # Snow grains
    80: "rain",        # Slight rain showers
    81: "rain",        # Moderate rain showers
    82: "storm",       # Violent rain showers
    85: "snow",        # Slight snow showers
    86: "snow",        # Heavy snow showers
    95: "storm",       # Thunderstorm
    96: "storm",       # Thunderstorm with slight hail
    99: "storm",       # Thunderstorm with heavy hail
}


class WeatherService:
    """Service for fetching real weather data and calculating demand impact."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._cache: Dict[str, Dict] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(hours=1)  # Cache weather for 1 hour
    
    def _get_store_coordinates(self, store_id: str) -> tuple:
        """Get coordinates for a store."""
        return STORE_COORDINATES.get(store_id, (DEFAULT_LATITUDE, DEFAULT_LONGITUDE))
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]
    
    def _get_temperature_category(self, temp_celsius: float) -> str:
        """Categorize temperature into impact categories."""
        for category, info in WEATHER_IMPACT_FACTORS.items():
            if "range" in info:
                min_temp, max_temp = info["range"]
                if min_temp <= temp_celsius < max_temp:
                    return category
        return "mild"  # Default
    
    def _get_weather_condition(self, weather_code: int) -> str:
        """Map Open-Meteo weather code to condition category."""
        return WEATHER_CODE_MAP.get(weather_code, "cloudy")
    
    def get_weather_forecast(
        self,
        store_id: str,
        target_date: date,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a store location.
        
        Args:
            store_id: Store identifier
            target_date: Target date for forecast
            days_ahead: Number of days to forecast
            
        Returns:
            Dict with weather data and demand impact factors
        """
        cache_key = f"{store_id}_{target_date.isoformat()}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Using cached weather for {cache_key}")
            return self._cache[cache_key]
        
        lat, lon = self._get_store_coordinates(store_id)
        
        try:
            # Build API URL
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "temperature_2m_mean",
                    "precipitation_sum",
                    "rain_sum",
                    "snowfall_sum",
                    "weather_code",
                    "wind_speed_10m_max"
                ],
                "timezone": "auto",
                "forecast_days": min(days_ahead + 1, 16)  # Open-Meteo supports up to 16 days
            }
            
            # Make synchronous request
            with httpx.Client(timeout=10.0) as client:
                response = client.get(OPEN_METEO_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Parse response
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            
            forecasts = []
            for i, forecast_date_str in enumerate(dates):
                forecast_date = date.fromisoformat(forecast_date_str)
                
                temp_mean = daily.get("temperature_2m_mean", [None])[i]
                temp_max = daily.get("temperature_2m_max", [None])[i]
                temp_min = daily.get("temperature_2m_min", [None])[i]
                weather_code = daily.get("weather_code", [0])[i] or 0
                precipitation = daily.get("precipitation_sum", [0])[i] or 0
                snowfall = daily.get("snowfall_sum", [0])[i] or 0
                wind_speed = daily.get("wind_speed_10m_max", [0])[i] or 0
                
                # Determine weather condition
                condition = self._get_weather_condition(weather_code)
                temp_category = self._get_temperature_category(temp_mean or 15)
                
                # Calculate demand impact factor
                temp_factor = WEATHER_IMPACT_FACTORS.get(temp_category, {}).get("factor", 1.0)
                condition_factor = WEATHER_IMPACT_FACTORS.get(condition, {}).get("factor", 1.0)
                
                # Combined weather factor (weighted average)
                weather_factor = (temp_factor * 0.4) + (condition_factor * 0.6)
                
                forecasts.append({
                    "date": forecast_date.isoformat(),
                    "temperature": {
                        "mean": temp_mean,
                        "max": temp_max,
                        "min": temp_min,
                        "category": temp_category
                    },
                    "condition": condition,
                    "weather_code": weather_code,
                    "precipitation_mm": precipitation,
                    "snowfall_cm": snowfall,
                    "wind_speed_kmh": wind_speed,
                    "demand_impact": {
                        "temperature_factor": round(temp_factor, 3),
                        "condition_factor": round(condition_factor, 3),
                        "combined_factor": round(weather_factor, 3),
                        "description": WEATHER_IMPACT_FACTORS.get(condition, {}).get("description", "Normal conditions")
                    }
                })
            
            result = {
                "store_id": store_id,
                "location": {"latitude": lat, "longitude": lon},
                "timezone": data.get("timezone", "UTC"),
                "generated_at": datetime.now().isoformat(),
                "forecasts": forecasts,
                "source": "Open-Meteo API (real-time)"
            }
            
            # Cache result
            self._cache[cache_key] = result
            self._cache_expiry[cache_key] = datetime.now() + self._cache_duration
            
            self.logger.info(f"Fetched weather forecast for store {store_id}: {len(forecasts)} days")
            return result
            
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error fetching weather: {e}")
            return self._get_fallback_weather(store_id, target_date, days_ahead)
        except Exception as e:
            self.logger.error(f"Error fetching weather: {e}", exc_info=True)
            return self._get_fallback_weather(store_id, target_date, days_ahead)
    
    def get_weather_factor_for_date(
        self,
        store_id: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Get the weather demand impact factor for a specific date.
        
        Args:
            store_id: Store identifier
            target_date: Date to get weather factor for
            
        Returns:
            Dict with weather factor and details
        """
        forecast = self.get_weather_forecast(store_id, target_date, days_ahead=1)
        
        # Find the specific date in forecasts
        for day_forecast in forecast.get("forecasts", []):
            if day_forecast["date"] == target_date.isoformat():
                return {
                    "date": target_date.isoformat(),
                    "weather": day_forecast["condition"],
                    "temperature": day_forecast["temperature"]["mean"],
                    "temperature_category": day_forecast["temperature"]["category"],
                    "weather_factor": day_forecast["demand_impact"]["combined_factor"],
                    "description": day_forecast["demand_impact"]["description"],
                    "source": "Open-Meteo API"
                }
        
        # Date not found in forecast, use today's data or fallback
        return self._get_fallback_weather_factor(target_date)
    
    def _get_fallback_weather(
        self,
        store_id: str,
        target_date: date,
        days_ahead: int
    ) -> Dict[str, Any]:
        """Generate fallback weather data when API is unavailable."""
        self.logger.warning(f"Using fallback weather for store {store_id}")
        
        lat, lon = self._get_store_coordinates(store_id)
        forecasts = []
        
        for i in range(days_ahead):
            forecast_date = target_date + timedelta(days=i)
            month = forecast_date.month
            
            # Seasonal temperature estimation (Northern hemisphere)
            if month in [12, 1, 2]:
                temp_mean = 5.0
                condition = "cold"
            elif month in [3, 4, 5]:
                temp_mean = 15.0
                condition = "mild"
            elif month in [6, 7, 8]:
                temp_mean = 25.0
                condition = "warm"
            else:
                temp_mean = 15.0
                condition = "mild"
            
            weather_factor = 1.0  # Neutral when using fallback
            
            forecasts.append({
                "date": forecast_date.isoformat(),
                "temperature": {
                    "mean": temp_mean,
                    "max": temp_mean + 5,
                    "min": temp_mean - 5,
                    "category": self._get_temperature_category(temp_mean)
                },
                "condition": condition,
                "weather_code": 2,
                "precipitation_mm": 0,
                "snowfall_cm": 0,
                "wind_speed_kmh": 10,
                "demand_impact": {
                    "temperature_factor": 1.0,
                    "condition_factor": 1.0,
                    "combined_factor": weather_factor,
                    "description": "Fallback estimate - API unavailable"
                }
            })
        
        return {
            "store_id": store_id,
            "location": {"latitude": lat, "longitude": lon},
            "timezone": "UTC",
            "generated_at": datetime.now().isoformat(),
            "forecasts": forecasts,
            "source": "Fallback estimate (API unavailable)"
        }
    
    def _get_fallback_weather_factor(self, target_date: date) -> Dict[str, Any]:
        """Get fallback weather factor when specific date data is unavailable."""
        month = target_date.month
        
        # Simple seasonal estimation
        if month in [12, 1, 2]:
            return {
                "date": target_date.isoformat(),
                "weather": "cold",
                "temperature": 5.0,
                "temperature_category": "cold",
                "weather_factor": 0.92,
                "description": "Seasonal estimate - winter",
                "source": "Fallback"
            }
        elif month in [6, 7, 8]:
            return {
                "date": target_date.isoformat(),
                "weather": "warm",
                "temperature": 25.0,
                "temperature_category": "warm",
                "weather_factor": 1.08,
                "description": "Seasonal estimate - summer",
                "source": "Fallback"
            }
        else:
            return {
                "date": target_date.isoformat(),
                "weather": "mild",
                "temperature": 15.0,
                "temperature_category": "mild",
                "weather_factor": 1.0,
                "description": "Seasonal estimate - spring/autumn",
                "source": "Fallback"
            }
    
    def clear_cache(self):
        """Clear the weather cache."""
        self._cache.clear()
        self._cache_expiry.clear()
        self.logger.info("Weather cache cleared")


# Global singleton instance
_weather_service_instance: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """Get or create the global WeatherService singleton."""
    global _weather_service_instance
    if _weather_service_instance is None:
        _weather_service_instance = WeatherService()
    return _weather_service_instance


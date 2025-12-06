"""
Real Holiday Service using Nager.Date API.

Nager.Date is a free, open-source holiday API that requires no API key.
Documentation: https://date.nager.at/Api

This service provides:
- Public holidays for any country
- Long weekends detection
- Holiday demand impact factors
"""

import httpx
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from functools import lru_cache

from shared.logging_setup import get_logger

logger = get_logger(__name__)

# Nager.Date API base URL (free, no API key required)
NAGER_DATE_BASE_URL = "https://date.nager.at/api/v3"

# Store to country mapping
# In production, this would come from the database
STORE_COUNTRY_MAP = {
    "235": "US",    # United States
    "100": "US",    # Los Angeles
    "150": "US",    # Chicago
    "200": "US",    # Houston
    "250": "US",    # Phoenix
    "default": "US"
}

# Holiday impact factors on demand
HOLIDAY_IMPACT_FACTORS = {
    # Major holidays with significant impact
    "major": {
        "factor": 1.35,
        "pre_days": 3,      # Days before with elevated demand
        "post_days": 1,     # Days after with elevated demand
        "description": "Major holiday - significantly higher demand"
    },
    # Medium holidays
    "medium": {
        "factor": 1.20,
        "pre_days": 2,
        "post_days": 0,
        "description": "Medium holiday - moderately higher demand"
    },
    # Minor holidays
    "minor": {
        "factor": 1.10,
        "pre_days": 1,
        "post_days": 0,
        "description": "Minor holiday - slightly higher demand"
    },
    # No holiday
    "none": {
        "factor": 1.0,
        "pre_days": 0,
        "post_days": 0,
        "description": "No holiday impact"
    }
}

# Holiday classification by name (for demand impact)
MAJOR_HOLIDAYS = {
    "Christmas Day", "Christmas", "New Year's Day", "Thanksgiving Day",
    "Independence Day", "Easter Sunday", "Easter Monday", "Memorial Day",
    "Labor Day", "New Year's Eve"
}

MEDIUM_HOLIDAYS = {
    "Good Friday", "Presidents' Day", "Martin Luther King Jr. Day",
    "Columbus Day", "Veterans Day", "Super Bowl Sunday"
}

# Special retail events (not official holidays but significant for retail)
RETAIL_EVENTS = {
    # (month, day): {"name": str, "factor": float, "description": str}
    (11, 25): {"name": "Black Friday", "factor": 1.50, "description": "Black Friday - highest retail day"},
    (11, 28): {"name": "Cyber Monday", "factor": 1.25, "description": "Cyber Monday - online surge"},
    (2, 14): {"name": "Valentine's Day", "factor": 1.20, "description": "Valentine's Day - flowers/chocolate surge"},
    (5, 12): {"name": "Mother's Day", "factor": 1.25, "description": "Mother's Day - flowers/gifts surge"},
    (6, 16): {"name": "Father's Day", "factor": 1.15, "description": "Father's Day - gifts surge"},
    (10, 31): {"name": "Halloween", "factor": 1.20, "description": "Halloween - candy/costumes surge"},
    (7, 4): {"name": "July 4th", "factor": 1.30, "description": "Independence Day - BBQ/party supplies"},
}


class HolidayService:
    """Service for fetching real holiday data and calculating demand impact."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._cache: Dict[str, Dict] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(days=30)  # Cache holidays for 30 days
        self._holidays_by_date: Dict[str, Set[date]] = {}  # country -> set of holiday dates
    
    def _get_store_country(self, store_id: str) -> str:
        """Get country code for a store."""
        return STORE_COUNTRY_MAP.get(store_id, STORE_COUNTRY_MAP["default"])
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]
    
    def _classify_holiday(self, holiday_name: str) -> str:
        """Classify holiday by impact level."""
        if any(major.lower() in holiday_name.lower() for major in MAJOR_HOLIDAYS):
            return "major"
        elif any(medium.lower() in holiday_name.lower() for medium in MEDIUM_HOLIDAYS):
            return "medium"
        else:
            return "minor"
    
    def get_holidays_for_year(
        self,
        country_code: str,
        year: int
    ) -> List[Dict[str, Any]]:
        """
        Get all public holidays for a country in a given year.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "GB", "DE")
            year: Year to get holidays for
            
        Returns:
            List of holiday dictionaries
        """
        cache_key = f"{country_code}_{year}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Using cached holidays for {cache_key}")
            return self._cache[cache_key]
        
        try:
            url = f"{NAGER_DATE_BASE_URL}/PublicHolidays/{year}/{country_code}"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                holidays_raw = response.json()
            
            holidays = []
            for h in holidays_raw:
                holiday_date = date.fromisoformat(h["date"])
                classification = self._classify_holiday(h["localName"])
                impact = HOLIDAY_IMPACT_FACTORS[classification]
                
                holidays.append({
                    "date": h["date"],
                    "name": h["localName"],
                    "name_english": h.get("name", h["localName"]),
                    "country_code": h["countryCode"],
                    "fixed": h.get("fixed", False),
                    "global": h.get("global", True),
                    "types": h.get("types", []),
                    "classification": classification,
                    "demand_impact": {
                        "factor": impact["factor"],
                        "pre_days": impact["pre_days"],
                        "post_days": impact["post_days"],
                        "description": impact["description"]
                    }
                })
            
            # Store in date lookup cache
            if country_code not in self._holidays_by_date:
                self._holidays_by_date[country_code] = set()
            for h in holidays:
                self._holidays_by_date[country_code].add(date.fromisoformat(h["date"]))
            
            # Cache result
            self._cache[cache_key] = holidays
            self._cache_expiry[cache_key] = datetime.now() + self._cache_duration
            
            self.logger.info(f"Fetched {len(holidays)} holidays for {country_code} {year}")
            return holidays
            
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error fetching holidays: {e}")
            return self._get_fallback_holidays(country_code, year)
        except Exception as e:
            self.logger.error(f"Error fetching holidays: {e}", exc_info=True)
            return self._get_fallback_holidays(country_code, year)
    
    def is_holiday(
        self,
        target_date: date,
        country_code: str = "US"
    ) -> Dict[str, Any]:
        """
        Check if a date is a holiday and get its details.
        
        Args:
            target_date: Date to check
            country_code: Country code
            
        Returns:
            Dict with holiday info or None indicator
        """
        # Ensure we have holidays for this year loaded
        self.get_holidays_for_year(country_code, target_date.year)
        
        cache_key = f"{country_code}_{target_date.year}"
        holidays = self._cache.get(cache_key, [])
        
        # Check for official holidays
        for h in holidays:
            if h["date"] == target_date.isoformat():
                return {
                    "is_holiday": True,
                    "date": target_date.isoformat(),
                    "name": h["name"],
                    "classification": h["classification"],
                    "factor": h["demand_impact"]["factor"],
                    "description": h["demand_impact"]["description"],
                    "source": "Nager.Date API"
                }
        
        # Check for retail events
        retail_event = RETAIL_EVENTS.get((target_date.month, target_date.day))
        if retail_event:
            return {
                "is_holiday": True,
                "date": target_date.isoformat(),
                "name": retail_event["name"],
                "classification": "retail_event",
                "factor": retail_event["factor"],
                "description": retail_event["description"],
                "source": "Retail Calendar"
            }
        
        # Check for pre-holiday periods (days before major holidays)
        for h in holidays:
            if h["classification"] == "major":
                holiday_date = date.fromisoformat(h["date"])
                days_until = (holiday_date - target_date).days
                pre_days = h["demand_impact"]["pre_days"]
                
                if 0 < days_until <= pre_days:
                    # Calculate diminishing factor as we get further from holiday
                    factor_reduction = (pre_days - days_until + 1) / (pre_days + 1)
                    adjusted_factor = 1.0 + (h["demand_impact"]["factor"] - 1.0) * factor_reduction * 0.7
                    
                    return {
                        "is_holiday": False,
                        "is_pre_holiday": True,
                        "date": target_date.isoformat(),
                        "name": f"Pre-{h['name']} shopping",
                        "related_holiday": h["name"],
                        "days_until_holiday": days_until,
                        "classification": "pre_holiday",
                        "factor": round(adjusted_factor, 3),
                        "description": f"{days_until} day(s) before {h['name']} - elevated shopping",
                        "source": "Calculated"
                    }
        
        return {
            "is_holiday": False,
            "date": target_date.isoformat(),
            "name": None,
            "classification": "none",
            "factor": 1.0,
            "description": "No holiday impact",
            "source": "None"
        }
    
    def get_holiday_factor_for_date(
        self,
        store_id: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Get the holiday demand impact factor for a specific date and store.
        
        Args:
            store_id: Store identifier
            target_date: Date to get factor for
            
        Returns:
            Dict with holiday factor and details
        """
        country_code = self._get_store_country(store_id)
        return self.is_holiday(target_date, country_code)
    
    def get_upcoming_holidays(
        self,
        store_id: str,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming holidays for a store.
        
        Args:
            store_id: Store identifier
            days_ahead: Number of days to look ahead
            
        Returns:
            List of upcoming holidays
        """
        country_code = self._get_store_country(store_id)
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        # Get holidays for current and possibly next year
        holidays = self.get_holidays_for_year(country_code, today.year)
        if end_date.year != today.year:
            holidays.extend(self.get_holidays_for_year(country_code, end_date.year))
        
        # Filter to upcoming holidays
        upcoming = []
        for h in holidays:
            holiday_date = date.fromisoformat(h["date"])
            if today <= holiday_date <= end_date:
                days_until = (holiday_date - today).days
                upcoming.append({
                    **h,
                    "days_until": days_until
                })
        
        # Add retail events
        for (month, day), event in RETAIL_EVENTS.items():
            try:
                event_date = date(today.year, month, day)
                if event_date < today:
                    event_date = date(today.year + 1, month, day)
                
                if today <= event_date <= end_date:
                    days_until = (event_date - today).days
                    upcoming.append({
                        "date": event_date.isoformat(),
                        "name": event["name"],
                        "classification": "retail_event",
                        "demand_impact": {
                            "factor": event["factor"],
                            "description": event["description"]
                        },
                        "days_until": days_until
                    })
            except ValueError:
                continue  # Invalid date (e.g., Feb 30)
        
        # Sort by date
        upcoming.sort(key=lambda x: x["date"])
        
        return upcoming
    
    def _get_fallback_holidays(
        self,
        country_code: str,
        year: int
    ) -> List[Dict[str, Any]]:
        """Generate fallback holiday data when API is unavailable."""
        self.logger.warning(f"Using fallback holidays for {country_code} {year}")
        
        # Basic US holidays as fallback
        if country_code == "US":
            fallback = [
                {"date": f"{year}-01-01", "name": "New Year's Day", "classification": "major"},
                {"date": f"{year}-07-04", "name": "Independence Day", "classification": "major"},
                {"date": f"{year}-11-28", "name": "Thanksgiving Day", "classification": "major"},
                {"date": f"{year}-12-25", "name": "Christmas Day", "classification": "major"},
            ]
        else:
            fallback = [
                {"date": f"{year}-01-01", "name": "New Year's Day", "classification": "major"},
                {"date": f"{year}-12-25", "name": "Christmas Day", "classification": "major"},
            ]
        
        holidays = []
        for h in fallback:
            impact = HOLIDAY_IMPACT_FACTORS[h["classification"]]
            holidays.append({
                "date": h["date"],
                "name": h["name"],
                "name_english": h["name"],
                "country_code": country_code,
                "fixed": True,
                "global": True,
                "types": ["Public"],
                "classification": h["classification"],
                "demand_impact": {
                    "factor": impact["factor"],
                    "pre_days": impact["pre_days"],
                    "post_days": impact["post_days"],
                    "description": f"{impact['description']} (fallback)"
                }
            })
        
        return holidays
    
    def clear_cache(self):
        """Clear the holiday cache."""
        self._cache.clear()
        self._cache_expiry.clear()
        self._holidays_by_date.clear()
        self.logger.info("Holiday cache cleared")


# Global singleton instance
_holiday_service_instance: Optional[HolidayService] = None


def get_holiday_service() -> HolidayService:
    """Get or create the global HolidayService singleton."""
    global _holiday_service_instance
    if _holiday_service_instance is None:
        _holiday_service_instance = HolidayService()
    return _holiday_service_instance


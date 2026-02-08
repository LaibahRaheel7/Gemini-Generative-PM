"""
Holiday Manager - Provides country-specific holiday data for scheduling.
"""
from typing import List, Dict
from datetime import date, datetime
from core.models import HolidayPreset


class HolidayManager:
    """
    Manages holiday data for different countries using the python-holidays library.
    Provides caching for performance.
    """
    
    def __init__(self):
        """Initialize the holiday manager with an empty cache."""
        self._cache: Dict[str, List[date]] = {}
    
    def get_holidays(self, country_code: str, year: int) -> List[date]:
        """
        Get all holidays for a specific country and year.
        
        Args:
            country_code: ISO country code (e.g., 'US', 'GB', 'AE')
            year: Year to get holidays for
            
        Returns:
            List of holiday dates sorted chronologically
        """
        cache_key = f"{country_code}_{year}"
        
        if cache_key not in self._cache:
            try:
                import holidays
                country_holidays = holidays.country_holidays(country_code, years=year)
                self._cache[cache_key] = sorted(country_holidays.keys())
            except (AttributeError, KeyError):
                # Country not supported, return empty list
                print(f"Warning: Country code '{country_code}' not supported by holidays library")
                self._cache[cache_key] = []
        
        return self._cache[cache_key]
    
    def get_holidays_from_preset(self, preset: HolidayPreset) -> List[date]:
        """
        Get holidays from a HolidayPreset object.
        
        If preset has pre-defined holiday_dates, use those.
        Otherwise, fetch from the holidays library.
        
        Args:
            preset: HolidayPreset with country and year
            
        Returns:
            List of holiday dates
        """
        if preset.holiday_dates:
            # Use pre-defined dates from preset
            return [datetime.fromisoformat(d).date() for d in preset.holiday_dates]
        
        # Fetch from holidays library
        return self.get_holidays(preset.country_code, preset.year)
    
    def is_holiday(self, check_date: date, preset: HolidayPreset) -> bool:
        """
        Check if a specific date is a holiday.
        
        Args:
            check_date: Date to check
            preset: HolidayPreset with country and year
            
        Returns:
            True if the date is a holiday, False otherwise
        """
        holidays_list = self.get_holidays_from_preset(preset)
        return check_date in holidays_list
    
    def get_available_countries(self) -> List[str]:
        """
        Get list of all supported country codes.
        
        Returns:
            List of ISO country codes
        """
        try:
            import holidays
            # Get all available country codes
            return sorted(holidays.list_supported_countries())
        except Exception as e:
            print(f"Error getting available countries: {e}")
            return ["US", "GB", "CA", "AU", "DE", "FR", "AE", "SA"]
    
    def get_country_name(self, country_code: str) -> str:
        """
        Get the full country name from country code.
        
        Args:
            country_code: ISO country code
            
        Returns:
            Full country name or the code if not found
        """
        country_names = {
            "US": "United States",
            "GB": "United Kingdom",
            "CA": "Canada",
            "AU": "Australia",
            "DE": "Germany",
            "FR": "France",
            "AE": "United Arab Emirates",
            "SA": "Saudi Arabia",
            "IN": "India",
            "CN": "China",
            "JP": "Japan",
            "BR": "Brazil",
            "MX": "Mexico",
            "IT": "Italy",
            "ES": "Spain",
            "NL": "Netherlands",
            "SE": "Sweden",
            "NO": "Norway",
            "DK": "Denmark",
            "FI": "Finland",
            "PL": "Poland",
            "CH": "Switzerland",
            "AT": "Austria",
            "BE": "Belgium",
            "IE": "Ireland",
            "PT": "Portugal",
            "GR": "Greece",
            "CZ": "Czech Republic",
            "HU": "Hungary",
            "RO": "Romania",
            "NZ": "New Zealand",
            "SG": "Singapore",
            "KR": "South Korea",
            "ZA": "South Africa",
            "IL": "Israel",
            "TR": "Turkey",
            "AR": "Argentina",
            "CL": "Chile",
            "CO": "Colombia",
        }
        return country_names.get(country_code, country_code)
    
    def clear_cache(self):
        """Clear the holiday cache. Useful when switching contexts."""
        self._cache.clear()


# Singleton instance
_holiday_manager_instance = None


def get_holiday_manager() -> HolidayManager:
    """
    Get the singleton HolidayManager instance.
    
    Returns:
        HolidayManager instance
    """
    global _holiday_manager_instance
    if _holiday_manager_instance is None:
        _holiday_manager_instance = HolidayManager()
    return _holiday_manager_instance

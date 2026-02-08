from datetime import datetime, timedelta
from typing import List

def is_business_day(date: datetime) -> bool:
    """Check if a date is a business day (Monday-Friday)."""
    return date.weekday() < 5

def get_next_business_day(date: datetime) -> datetime:
    """Get the next business day after the given date."""
    next_day = date + timedelta(days=1)
    while not is_business_day(next_day):
        next_day += timedelta(days=1)
    return next_day

def format_duration(hours: int) -> str:
    """Convert hours to human-readable format."""
    if hours < 8:
        return f"{hours}h"
    days = hours // 8
    remaining_hours = hours % 8
    if remaining_hours == 0:
        return f"{days}d"
    return f"{days}d {remaining_hours}h"

def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats."""
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    raise ValueError(f"Could not parse date: {date_str}")

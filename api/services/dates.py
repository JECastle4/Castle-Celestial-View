"""
Date and time calculation services
"""
from astropy.time import Time

# Import from root module - works when package is installed
from DayOfTheWeek import jd_to_weekday
from api.i18n import t


def calculate_day_of_week(date_str: str, time_str: str = "00:00:00") -> dict:
    """
    Calculate the day of the week from a given date and time.
    
    Args:
        date_str: Date in ISO format (YYYY-MM-DD)
        time_str: Time in HH:MM:SS format (defaults to 00:00:00)
    
    Returns:
        Dictionary containing:
            - julian_date: The JD as a float
            - day_of_week: Integer 0-6 (0=Sunday)
            - day_name: Name of the day
            - input_datetime: The processed input string
    
    Raises:
        ValueError: If date/time format is invalid
    """
    # Combine date and time (ISO 8601 format)
    datetime_str = f"{date_str}T{time_str}"
    
    # Convert to Julian Date using astropy
    t_obj = Time(datetime_str, format='isot', scale='utc')
    jd = t_obj.jd
    
    # Calculate day of week
    day_index = jd_to_weekday(jd)
    day_name = t(f'dayNames.{day_index}')
    
    return {
        "julian_date": jd,
        "day_of_week": day_index,
        "day_name": day_name,
        "input_datetime": datetime_str
    }

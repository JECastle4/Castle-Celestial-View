"""
Shared utility functions for astronomy calculations
"""
import math


def jd_to_weekday(jd):
    """Convert Julian Date to weekday index.

    Args:
        jd: Julian Date as a float

    Returns:
        int: Weekday index (0=Sunday, 1=Monday, ..., 6=Saturday)
    """
    jdn = int(math.floor(jd + 0.5))
    return (jdn + 1) % 7  # 0=Sunday ... 6=Saturday

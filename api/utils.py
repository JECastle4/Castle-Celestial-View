"""
Shared utility functions for astronomy calculations
"""
import math


def jd_to_weekday(jd):
    jdn = int(math.floor(jd + 0.5))
    return (jdn + 1) % 7  # 0=Sunday ... 6=Saturday

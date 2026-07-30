from astropy.time import Time

def prompt_date(prompt="Enter date (YYYY/MM/DD): "):
    date_s = input("Date (YYYY-MM-DD): ").strip()
    time_s = input("Time (HH:MM[:SS], default 00:00:00): ").strip() or "00:00:00"

    iso = f"{date_s} {time_s}"            # e.g. "2025-12-31 12:34:56"
    t = Time(iso, format='iso', scale='utc')  # use 'utc' or the correct scale for your data

    return t;
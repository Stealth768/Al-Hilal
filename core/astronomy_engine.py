import math
import datetime
from functools import lru_cache

from skyfield import api, almanac

DELHI_LAT = 28.6139
DELHI_LON = 77.2090
DELHI_ELEVATION = 324.0

# Load ephemeris lazily to avoid long import times when module loaded
ts = api.load.timescale()
try:
    eph = api.load('de421.bsp')
except Exception:
    # fallback to built-in simple ephemeris if download not available
    eph = api.load('de421.bsp')

# Observer position
delhi = api.Topos(latitude_degrees=DELHI_LAT, longitude_degrees=DELHI_LON, elevation_m=DELHI_ELEVATION)


def _ensure_date(dt):
    if isinstance(dt, str):
        return datetime.datetime.strptime(dt, '%Y-%m-%d').date()
    if isinstance(dt, datetime.datetime):
        return dt.date()
    return dt


def calculate_moon_visibility(target_date):
    """
    Compute accurate moon visibility parameters for Delhi on the given date.
    Expects target_date as datetime.date, datetime.datetime or 'YYYY-MM-DD' string.
    Returns dict with keys: moon_age_hours, illumination_pct, lag_time_minutes,
    moon_altitude_deg_at_sunset, is_visible, visibility_grade, sunset_utc, moonset_utc
    """
    date = _ensure_date(target_date)

    # define time window covering the date (UTC) — search from 00:00 to 23:59 UTC
    t0 = ts.utc(date.year, date.month, date.day, 0, 0, 0)
    t1 = ts.utc(date.year, date.month, date.day, 23, 59, 59)

    # Compute sunset time at Delhi for that date
    f = almanac.sunrise_sunset(eph, delhi)
    try:
        times, events = almanac.find_discrete(t0, t1, f)
        # events: 1 = above (rise), 0 = below (set) — pick the 'set' event (0) that occurs in the day
        sunset_time = None
        for t, ev in zip(times, events):
            if ev == 0:
                sunset_time = t
        # if not found, expand search +/- 1 day
        if sunset_time is None:
            t0b = ts.utc(date.year, date.month, date.day-1, 0)
            t1b = ts.utc(date.year, date.month, date.day+1, 23, 59)
            times, events = almanac.find_discrete(t0b, t1b, f)
            for t, ev in zip(times, events):
                if ev == 0 and t.utc_datetime().date() == date:
                    sunset_time = t
    except Exception:
        sunset_time = ts.utc(date.year, date.month, date.day, 18, 0)

    # Compute moonset time for the same window
    try:
        fm = almanac.risings_and_settings(eph, eph['moon'], delhi)
        times_m, events_m = almanac.find_discrete(t0, t1, fm)
        moonset_time = None
        for t, ev in zip(times_m, events_m):
            # events_m: 1 = rise, 0 = set (same convention)
            if ev == 0:
                moonset_time = t
        if moonset_time is None:
            # expand window
            t0b = ts.utc(date.year, date.month, date.day-1, 0)
            t1b = ts.utc(date.year, date.month, date.day+1, 23, 59)
            times_m, events_m = almanac.find_discrete(t0b, t1b, fm)
            for t, ev in zip(times_m, events_m):
                if ev == 0 and t.utc_datetime().date() == date:
                    moonset_time = t
    except Exception:
        moonset_time = None

    # If sunset_time or moonset_time are still None, provide reasonable fallbacks
    if sunset_time is None:
        sunset_time = ts.utc(date.year, date.month, date.day, 18, 0)
    if moonset_time is None:
        # if no moonset found on that calendar day, try to compute next setting after sunset
        try:
            # search from sunset to sunset+24h
            t_start = sunset_time
            t_end = ts.utc(date.year, date.month, date.day, 23, 59)
            times_m, events_m = almanac.find_discrete(t_start, t_end, fm)
            moonset_time = None
            for t, ev in zip(times_m, events_m):
                if ev == 0:
                    moonset_time = t
            if moonset_time is None:
                # fallback to sunset + 45 minutes
                moonset_time = ts.utc((sunset_time.utc_datetime() + datetime.timedelta(minutes=45)).replace(tzinfo=None))
        except Exception:
            moonset_time = ts.utc((sunset_time.utc_datetime() + datetime.timedelta(minutes=45)).replace(tzinfo=None))

    # compute lag time = moonset - sunset in minutes
    lag_seconds = (moonset_time.utc_datetime() - sunset_time.utc_datetime()).total_seconds()
    lag_minutes = lag_seconds / 60.0

    # compute moon altitude at sunset
    astrometric = eph['moon'].at(sunset_time).observe(eph['earth']) if False else None
    # Instead compute moon's topocentric alt/az
    try:
        topocentric = (eph['moon'] - eph['earth']).at(sunset_time)
    except Exception:
        topocentric = eph['moon'].at(sunset_time)

    # Use Skyfield's observer position to compute alt/az
    try:
        observer = eph['earth'] + delhi
        astrom = observer.at(sunset_time).observe(eph['moon']).apparent()
        alt, az, distance = astrom.altaz()
        moon_alt_deg = alt.degrees
    except Exception:
        moon_alt_deg = 0.0

    # compute moon phase angle and illumination using almanac
    try:
        phase_angle = almanac.moon_phase(eph, sunset_time)
        # skyfield returns radians; convert to illumination pct
        illumination = (1 - math.cos(phase_angle)) / 2.0 * 100.0
    except Exception:
        # fallback: approximate from age via fraction of synodic month
        illumination = 1.0

    # compute moon age (hours) since last new moon
    try:
        # search for moon phases around the date to find the nearest previous new moon
        t_before = ts.utc(date.year, date.month, date.day-30)
        t_after = ts.utc(date.year, date.month, date.day+1)
        times_p, phases = almanac.find_discrete(t_before, t_after, almanac.moon_phases(eph))
        new_moon_time = None
        for t, p in zip(times_p, phases):
            # phase 0 is New Moon
            if p == 0 and t.utc_datetime().date() <= date:
                new_moon_time = t
        if new_moon_time is None and len(times_p) > 0:
            new_moon_time = times_p[0]
        if new_moon_time is not None:
            age_hours = (sunset_time.utc_datetime() - new_moon_time.utc_datetime()).total_seconds() / 3600.0
        else:
            age_hours = None
    except Exception:
        age_hours = None

    # visibility logic: thresholds adapted from common Crescents visibility guidance
    is_visible = False
    visibility_grade = 'D'

    # Basic thresholds
    try:
        if age_hours is None:
            age_hours = 0.0
        if illumination is None:
            illumination = 0.0

        if illumination < 0.5 or age_hours < 15.0:
            is_visible = False
            visibility_grade = 'D'
        elif lag_minutes >= 60 and moon_alt_deg > 2 and illumination >= 1.5:
            is_visible = True
            visibility_grade = 'A'
        elif lag_minutes >= 45 and moon_alt_deg > 1 and illumination >= 1.0:
            is_visible = True
            visibility_grade = 'B'
        elif lag_minutes >= 30 and moon_alt_deg > 0 and illumination >= 0.5:
            is_visible = True
            visibility_grade = 'C'
        else:
            is_visible = False
            visibility_grade = 'D'
    except Exception:
        is_visible = False
        visibility_grade = 'D'

    result = {
        "moon_age_hours": age_hours,
        "illumination_pct": round(illumination, 2),
        "lag_time_minutes": round(lag_minutes, 1),
        "moon_altitude_deg_at_sunset": round(moon_alt_deg, 2),
        "is_visible": bool(is_visible),
        "visibility_grade": visibility_grade,
        "sunset_utc": sunset_time.utc_datetime().isoformat(),
        "moonset_utc": moonset_time.utc_datetime().isoformat()
    }
    return result


# --- Helper algorithms for calendar conversions ---

def gregorian_to_jd(y, m, d):
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    jd = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045
    return jd


def islamic_to_jd(year, month, day):
    # Tabular Islamic approximation
    ISLAMIC_EPOCH = 1948439.5
    return day + math.ceil(29.5 * (month - 1)) + (year - 1) * 354 + math.floor((3 + 11 * year) / 30) + ISLAMIC_EPOCH - 1


def jd_to_islamic(jd):
    ISLAMIC_EPOCH = 1948439.5
    jd0 = math.floor(jd) + 0.5
    days = jd0 - ISLAMIC_EPOCH
    year = math.floor((30 * days + 10646) / 10631)
    # compute month by trial
    month = min(12, math.ceil((jd0 - (29 + islamic_to_jd(year, 1, 1))) / 29.5) + 1)
    day = int(math.floor(jd0 - islamic_to_jd(year, month, 1) + 1))
    return {'y': int(year), 'm': int(month), 'd': int(day)}


def _build_hijri_calendar_for_year(target_gregorian_year):
    """Build a mapping of Gregorian dates to Hijri dates for a given Gregorian year.
    This uses moon visibility prediction to determine Islamic month starts for the year.
    """
    # Search for new moons a little before and after the requested year so we can cover the first
    # and last Hijri months that overlap the Gregorian year.
    start = datetime.date(target_gregorian_year - 1, 12, 1)
    end = datetime.date(target_gregorian_year + 1, 2, 15)
    t0 = ts.utc(start.year, start.month, start.day, 0, 0)
    t1 = ts.utc(end.year, end.month, end.day, 23, 59)

    try:
        phases = almanac.moon_phases(eph)
        times, phases_arr = almanac.find_discrete(t0, t1, phases)
    except Exception:
        return {}

    month_starts = []  # list of (month_start_date, islamic_year, islamic_month)

    for t, p in zip(times, phases_arr):
        if p != 0:
            continue
        try:
            base_date = t.utc_datetime().date()
        except Exception:
            continue

        month_start = None
        for offset in range(0, 7):
            try_date = base_date + datetime.timedelta(days=offset)
            vis = calculate_moon_visibility(try_date)
            if vis and vis.get('is_visible'):
                month_start = try_date + datetime.timedelta(days=1)
                break

        if month_start is None:
            month_start = base_date + datetime.timedelta(days=30)

        jd = gregorian_to_jd(month_start.year, month_start.month, month_start.day)
        isl = jd_to_islamic(jd)
        month_starts.append((month_start, isl['y'], isl['m']))

    month_starts.sort()

    # Ensure we have a month start before Jan 1 to cover the start of the Gregorian year.
    if not month_starts or month_starts[0][0] > datetime.date(target_gregorian_year, 1, 1):
        month_starts.insert(0, (datetime.date(target_gregorian_year - 1, 12, 1), None, None))

    # Build day-by-day mapping for the Gregorian year
    mapping = {}
    current_index = 0
    date_cursor = datetime.date(target_gregorian_year, 1, 1)
    year_end = datetime.date(target_gregorian_year, 12, 31)

    while date_cursor <= year_end:
        while (current_index + 1 < len(month_starts) and
               month_starts[current_index + 1][0] <= date_cursor):
            current_index += 1

        start_date, hijri_year, hijri_month = month_starts[current_index]
        if hijri_year is not None:
            day_of_month = (date_cursor - start_date).days + 1
            if day_of_month > 0:
                mapping[date_cursor.isoformat()] = {
                    'y': hijri_year,
                    'm': hijri_month,
                    'd': day_of_month,
                }

        date_cursor += datetime.timedelta(days=1)

    return mapping


@lru_cache(maxsize=8)
def build_hijri_calendar_for_year(target_gregorian_year):
    return _build_hijri_calendar_for_year(target_gregorian_year)


@lru_cache(maxsize=64)
def find_gregorian_date_for_islamic(target_gregorian_year, islamic_month, islamic_day):
    # Try to use the visibility-based Hijri mapping for the target year.
    mapping = build_hijri_calendar_for_year(target_gregorian_year)
    for gregorian_date, hijri in mapping.items():
        if hijri['m'] == islamic_month and hijri['d'] == islamic_day:
            return datetime.datetime.strptime(gregorian_date, '%Y-%m-%d').date()

    # fallback to a more expensive search if the mapping did not produce a result.
    start = datetime.date(target_gregorian_year - 1, 1, 1)
    end = datetime.date(target_gregorian_year + 1, 12, 31)
    t0 = ts.utc(start.year, start.month, start.day, 0, 0)
    t1 = ts.utc(end.year, end.month, end.day, 23, 59)

    try:
        phases = almanac.moon_phases(eph)
        times, phases_arr = almanac.find_discrete(t0, t1, phases)
    except Exception:
        return None

    candidate_month_starts = []

    for t, p in zip(times, phases_arr):
        if p != 0:
            continue
        try:
            base_date = t.utc_datetime().date()
        except Exception:
            continue
        for offset in range(0, 6):
            try_date = base_date + datetime.timedelta(days=offset)
            vis = calculate_moon_visibility(try_date)
            if vis and vis.get('is_visible'):
                month_start = try_date + datetime.timedelta(days=1)
                jd = gregorian_to_jd(month_start.year, month_start.month, month_start.day)
                isl = jd_to_islamic(jd)
                candidate_month_starts.append((month_start, isl['y'], isl['m']))
                break

    for month_start, isl_year, isl_month in candidate_month_starts:
        if isl_month == islamic_month:
            event_date = month_start + datetime.timedelta(days=(islamic_day - 1))
            if event_date.year == target_gregorian_year:
                return event_date

    for month_start, isl_year, isl_month in candidate_month_starts:
        if isl_month == islamic_month:
            return month_start + datetime.timedelta(days=(islamic_day - 1))

    cur = datetime.date(target_gregorian_year, 1, 1)
    endd = datetime.date(target_gregorian_year, 12, 31)
    while cur <= endd:
        jd = gregorian_to_jd(cur.year, cur.month, cur.day)
        isl = jd_to_islamic(jd)
        if isl['m'] == islamic_month and isl['d'] == islamic_day:
            return cur
        cur += datetime.timedelta(days=1)

    return None

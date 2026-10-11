"""US retail calendar: store closure days, US Eastern time and demand seasonality."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from functools import lru_cache

from .formats import UTC
from .rng import Weighted


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7, weeks=n - 1)


def thanksgiving(year: int) -> date:
    """Fourth Thursday of November."""
    first_november = date(year, 11, 1)
    first_thursday = first_november + timedelta(days=(3 - first_november.weekday()) % 7)
    return first_thursday + timedelta(weeks=3)


@lru_cache(maxsize=None)
def store_closures(year: int) -> frozenset[date]:
    """The chain closes its stores on Easter Sunday, Thanksgiving Day and Christmas Day."""
    return frozenset({easter_sunday(year), thanksgiving(year), date(year, 12, 25)})


def is_trading_day(day: date) -> bool:
    """Are brick-and-mortar stores open? Online sales ignore this."""
    return day not in store_closures(day.year)


def next_trading_day(day: date) -> date:
    candidate = day + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def eastern_utc_offset(moment_utc: datetime) -> timedelta:
    """US rule: daylight time from the 2nd Sunday of March 02:00 EST to the 1st Sunday of November 02:00 EDT."""
    year = moment_utc.year
    summer_start = datetime.combine(nth_sunday(year, 3, 2), time(7), tzinfo=UTC)
    summer_end = datetime.combine(nth_sunday(year, 11, 1), time(6), tzinfo=UTC)
    return timedelta(hours=-4) if summer_start <= moment_utc < summer_end else timedelta(hours=-5)


def local_to_utc(local: datetime) -> datetime:
    """Naive America/New_York wall-clock time -> aware UTC (approximate inside the DST switch hour)."""
    guess = local.replace(tzinfo=UTC) + timedelta(hours=5)
    return local.replace(tzinfo=UTC) - eastern_utc_offset(guess)


def black_friday(year: int) -> date:
    return thanksgiving(year) + timedelta(days=1)


def is_black_week(day: date) -> bool:
    friday = black_friday(day.year)
    return friday - timedelta(days=4) <= day <= friday + timedelta(days=3)


ONLINE_WEEKDAY_FACTOR = (1.05, 1.0, 1.0, 0.98, 0.95, 0.85, 1.12)
STORE_WEEKDAY_FACTOR = (0.85, 0.85, 0.9, 0.95, 1.15, 1.45, 1.1)
TREND_BASE = date(2025, 1, 1)
YEARLY_GROWTH = 1.12


def _seasonal_factor(day: date, online: bool) -> float:
    friday = black_friday(day.year)
    if day == friday:
        return 6.0 if online else 3.0
    if day == friday + timedelta(days=3):  # Cyber Monday
        return 4.0 if online else 1.5
    if friday - timedelta(days=4) <= day <= friday + timedelta(days=2):  # Black Week
        return 2.5 if online else 1.7
    if day.month == 12 and day.day <= 22:
        return 1.6 if online else 1.8
    if day.month == 12 and day.day in (23, 24):
        return 1.2 if online else 2.2
    if day.month == 12 and day.day >= 26:
        return 1.15
    if day.month == 1 and day.day <= 20:
        return 0.85
    if (day.month == 7 and day.day >= 20) or (day.month == 8) or (day.month == 9 and day.day <= 5):
        return 1.25  # back to school
    if day.month == 6:
        return 0.9
    return 1.0


def demand_multiplier(day: date, channel: str) -> float:
    online = channel == "online"
    weekday = (ONLINE_WEEKDAY_FACTOR if online else STORE_WEEKDAY_FACTOR)[day.weekday()]
    payday = 1.06 if day.day <= 3 or 15 <= day.day <= 17 else 1.0
    trend = YEARLY_GROWTH ** ((day - TREND_BASE).days / 365.25)
    return weekday * _seasonal_factor(day, online) * payday * trend


_ONLINE_HOUR_WEIGHTS = (0.15, 0.08, 0.05, 0.03, 0.03, 0.06, 0.2, 0.45, 0.7, 0.85, 0.95, 1.0,
                        1.05, 1.0, 0.95, 0.95, 1.0, 1.1, 1.25, 1.45, 1.6, 1.5, 1.1, 0.5)
_STORE_HOUR_WEIGHTS = (0.5, 0.7, 0.85, 0.9, 0.9, 1.0, 1.2, 1.35, 1.3, 1.0, 0.6)  # 10:00-20:59

ONLINE_HOURS = Weighted(list(enumerate(_ONLINE_HOUR_WEIGHTS)))
STORE_HOURS_WEEKDAY = Weighted(list(zip(range(10, 21), _STORE_HOUR_WEIGHTS)))
STORE_HOURS_SUNDAY = Weighted(list(zip(range(11, 19), _STORE_HOUR_WEIGHTS[:8])))  # Sundays 11-19


def sample_local_time(rng: random.Random, day: date, hours: Weighted[int]) -> datetime:
    hour = hours(rng)
    return datetime.combine(day, time(hour, rng.randrange(60), rng.randrange(60), rng.randrange(1000) * 1000))

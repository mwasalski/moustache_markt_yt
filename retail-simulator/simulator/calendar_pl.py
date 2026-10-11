"""Polish retail calendar: public holidays, trading Sundays, Warsaw time and demand seasonality."""

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


def last_sunday(year: int, month: int) -> date:
    first_of_next = date(year + month // 12, month % 12 + 1, 1)
    last_day = first_of_next - timedelta(days=1)
    return last_day - timedelta(days=(last_day.weekday() + 1) % 7)


@lru_cache(maxsize=None)
def public_holidays(year: int) -> frozenset[date]:
    easter = easter_sunday(year)
    holidays = {
        date(year, 1, 1), date(year, 1, 6), easter, easter + timedelta(days=1),
        date(year, 5, 1), date(year, 5, 3), easter + timedelta(days=49), easter + timedelta(days=60),
        date(year, 8, 15), date(year, 11, 1), date(year, 11, 11), date(year, 12, 25), date(year, 12, 26),
    }
    if year >= 2025:  # Christmas Eve is a public holiday since 2025
        holidays.add(date(year, 12, 24))
    return frozenset(holidays)


@lru_cache(maxsize=None)
def trading_sundays(year: int) -> frozenset[date]:
    """Last Sunday of Jan/Apr/Jun/Aug, Palm Sunday and the Sundays before Christmas (3 since 2025)."""
    sundays = {last_sunday(year, month) for month in (1, 4, 6, 8)}
    sundays.add(easter_sunday(year) - timedelta(days=7))
    christmas = date(year, 12, 25)
    sunday_before_christmas = christmas - timedelta(days=(christmas.weekday() + 1) % 7 or 7)
    december_count = 3 if year >= 2025 else 2
    sundays.update(sunday_before_christmas - timedelta(weeks=week) for week in range(december_count))
    return frozenset(sundays - public_holidays(year))


def is_trading_day(day: date) -> bool:
    """Are brick-and-mortar stores allowed to open? Online sales ignore this."""
    if day in public_holidays(day.year):
        return False
    return day.weekday() != 6 or day in trading_sundays(day.year)


def next_trading_day(day: date) -> date:
    candidate = day + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def warsaw_utc_offset(moment_utc: datetime) -> timedelta:
    """EU rule: summer time from the last Sunday of March to the last Sunday of October, 01:00 UTC."""
    year = moment_utc.year
    summer_start = datetime.combine(last_sunday(year, 3), time(1), tzinfo=UTC)
    summer_end = datetime.combine(last_sunday(year, 10), time(1), tzinfo=UTC)
    return timedelta(hours=2) if summer_start <= moment_utc < summer_end else timedelta(hours=1)


def local_to_utc(local: datetime) -> datetime:
    """Naive Europe/Warsaw wall-clock time -> aware UTC (approximate inside the DST switch hour)."""
    guess = local.replace(tzinfo=UTC) - timedelta(hours=1)
    return local.replace(tzinfo=UTC) - warsaw_utc_offset(guess)


def black_friday(year: int) -> date:
    first_november = date(year, 11, 1)
    first_thursday = first_november + timedelta(days=(3 - first_november.weekday()) % 7)
    return first_thursday + timedelta(weeks=3, days=1)


def is_black_week(day: date) -> bool:
    friday = black_friday(day.year)
    return friday - timedelta(days=4) <= day <= friday + timedelta(days=3)


ONLINE_WEEKDAY_FACTOR = (1.05, 1.0, 1.0, 0.98, 0.95, 0.85, 1.12)
STORE_WEEKDAY_FACTOR = (0.85, 0.85, 0.9, 0.95, 1.15, 1.45, 1.25)
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
    if day.month == 12 and day.day == 23:
        return 1.2 if online else 2.2
    if day.month == 12 and day.day >= 27:
        return 1.15
    if day.month == 1 and day.day <= 20:
        return 0.85
    if (day.month == 8 and day.day >= 18) or (day.month == 9 and day.day <= 12):
        return 1.25  # back to school
    if day.month in (6, 7):
        return 0.9
    return 1.0


def demand_multiplier(day: date, channel: str) -> float:
    online = channel == "online"
    weekday = (ONLINE_WEEKDAY_FACTOR if online else STORE_WEEKDAY_FACTOR)[day.weekday()]
    payday = 1.06 if day.day <= 3 or 10 <= day.day <= 12 else 1.0
    trend = YEARLY_GROWTH ** ((day - TREND_BASE).days / 365.25)
    return weekday * _seasonal_factor(day, online) * payday * trend


_ONLINE_HOUR_WEIGHTS = (0.15, 0.08, 0.05, 0.03, 0.03, 0.06, 0.2, 0.45, 0.7, 0.85, 0.95, 1.0,
                        1.05, 1.0, 0.95, 0.95, 1.0, 1.1, 1.25, 1.45, 1.6, 1.5, 1.1, 0.5)
_STORE_HOUR_WEIGHTS = (0.5, 0.7, 0.85, 0.9, 0.9, 1.0, 1.2, 1.35, 1.3, 1.0, 0.6)  # 10:00-20:59

ONLINE_HOURS = Weighted(list(enumerate(_ONLINE_HOUR_WEIGHTS)))
STORE_HOURS_WEEKDAY = Weighted(list(zip(range(10, 21), _STORE_HOUR_WEIGHTS)))
STORE_HOURS_SUNDAY = Weighted(list(zip(range(10, 18), _STORE_HOUR_WEIGHTS[:8])))  # trading Sundays 10-18


def sample_local_time(rng: random.Random, day: date, hours: Weighted[int]) -> datetime:
    hour = hours(rng)
    return datetime.combine(day, time(hour, rng.randrange(60), rng.randrange(60), rng.randrange(1000) * 1000))

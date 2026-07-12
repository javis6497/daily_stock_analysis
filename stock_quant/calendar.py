from __future__ import annotations

from datetime import date
from functools import lru_cache


def is_cn_trading_day(day: date) -> bool:
    try:
        return bool(_xshg_calendar().is_session(day.isoformat()))
    except Exception:
        return day.weekday() < 5


@lru_cache(maxsize=1)
def _xshg_calendar():
    import exchange_calendars

    return exchange_calendars.get_calendar("XSHG")

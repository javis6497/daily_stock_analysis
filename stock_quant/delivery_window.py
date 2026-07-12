from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, time as clock_time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo


class DeliveryWindowError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeliveryWindow:
    target: datetime
    opens_at: datetime
    closes_at: datetime


def wait_for_delivery_window(
    target_time: str,
    tolerance_minutes: int = 5,
    timezone_name: str = "Asia/Shanghai",
    now_fn: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> DeliveryWindow:
    if tolerance_minutes < 0:
        raise ValueError("tolerance_minutes must be non-negative")

    timezone = ZoneInfo(timezone_name)
    now_fn = now_fn or (lambda: datetime.now(timezone))
    now = _aware_now(now_fn(), timezone)
    target_clock = _parse_target_time(target_time)
    target = datetime.combine(now.date(), target_clock, tzinfo=timezone)
    tolerance = timedelta(minutes=tolerance_minutes)
    window = DeliveryWindow(
        target=target,
        opens_at=target - tolerance,
        closes_at=target + tolerance,
    )

    if now < window.opens_at:
        sleep_fn((window.opens_at - now).total_seconds())

    ensure_delivery_window_open(window, now_fn=now_fn)
    return window


def ensure_delivery_window_open(
    window: DeliveryWindow,
    now_fn: Callable[[], datetime] | None = None,
) -> datetime:
    timezone = window.target.tzinfo
    if timezone is None:
        raise ValueError("delivery window must be timezone-aware")
    now_fn = now_fn or (lambda: datetime.now(timezone))
    now = _aware_now(now_fn(), timezone)
    if now < window.opens_at:
        raise DeliveryWindowError(
            f"delivery window is not open: now={now.isoformat()} opens={window.opens_at.isoformat()}"
        )
    if now > window.closes_at:
        raise DeliveryWindowError(
            f"missed delivery window: now={now.isoformat()} deadline={window.closes_at.isoformat()}"
        )
    return now


def _parse_target_time(value: str) -> clock_time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError("target_time must use HH:MM format") from exc


def _aware_now(value: datetime, timezone) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)

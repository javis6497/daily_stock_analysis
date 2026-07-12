from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from stock_quant.delivery_window import (
    DeliveryWindowError,
    ensure_delivery_window_open,
    wait_for_delivery_window,
)


BEIJING = ZoneInfo("Asia/Shanghai")


def test_waits_until_five_minutes_before_target():
    moments = iter(
        [
            datetime(2026, 7, 13, 8, 30, tzinfo=BEIJING),
            datetime(2026, 7, 13, 8, 32, tzinfo=BEIJING),
        ]
    )
    sleeps: list[float] = []

    window = wait_for_delivery_window(
        "08:37",
        tolerance_minutes=5,
        timezone_name="Asia/Shanghai",
        now_fn=lambda: next(moments),
        sleep_fn=sleeps.append,
    )

    assert sleeps == [120.0]
    assert window.opens_at.hour == 8
    assert window.opens_at.minute == 32
    assert window.closes_at.minute == 42


def test_rejects_delivery_after_window_closes():
    now = datetime(2026, 7, 13, 8, 42, 1, tzinfo=BEIJING)

    with pytest.raises(DeliveryWindowError, match="missed delivery window"):
        wait_for_delivery_window(
            "08:37",
            tolerance_minutes=5,
            timezone_name="Asia/Shanghai",
            now_fn=lambda: now,
        )


def test_each_message_attempt_is_rejected_after_deadline():
    now = datetime(2026, 7, 13, 14, 12, 1, tzinfo=BEIJING)
    window = wait_for_delivery_window(
        "14:07",
        tolerance_minutes=5,
        timezone_name="Asia/Shanghai",
        now_fn=lambda: datetime(2026, 7, 13, 14, 8, tzinfo=BEIJING),
    )

    with pytest.raises(DeliveryWindowError, match="missed delivery window"):
        ensure_delivery_window_open(window, now_fn=lambda: now)

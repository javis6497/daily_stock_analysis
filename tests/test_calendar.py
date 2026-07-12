from __future__ import annotations

from datetime import date

from tests.helpers import require_module


def test_cn_calendar_rejects_weekday_exchange_holiday(monkeypatch):
    calendar = require_module("stock_quant.calendar")

    class FakeCalendar:
        def is_session(self, value):
            return value == "2026-10-09"

    monkeypatch.setattr(calendar, "_xshg_calendar", lambda: FakeCalendar())

    assert not calendar.is_cn_trading_day(date(2026, 10, 1))
    assert calendar.is_cn_trading_day(date(2026, 10, 9))


def test_cn_calendar_falls_back_to_weekdays_when_library_fails(monkeypatch):
    calendar = require_module("stock_quant.calendar")
    monkeypatch.setattr(calendar, "_xshg_calendar", lambda: (_ for _ in ()).throw(RuntimeError("unavailable")))

    assert calendar.is_cn_trading_day(date(2026, 7, 13))
    assert not calendar.is_cn_trading_day(date(2026, 7, 12))

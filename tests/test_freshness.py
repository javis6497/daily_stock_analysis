from __future__ import annotations

from datetime import date

from tests.helpers import make_bars, make_instrument, require_module


def test_build_data_freshness_detects_stale_and_missing_symbols():
    freshness = require_module("stock_quant.freshness")
    fresh = make_instrument("018044", "基金018044", "fund")
    stale = make_instrument("012922", "基金012922", "fund")
    missing = make_instrument("017731", "基金017731", "fund")
    fresh_bars = make_bars("up", count=5)
    stale_bars = make_bars("up", count=5)

    # Force stable known dates for the assertion.
    fresh_bars = [bar.__class__(date(2026, 7, 3), bar.open, bar.high, bar.low, bar.close, bar.volume) for bar in fresh_bars[-1:]]
    stale_bars = [bar.__class__(date(2026, 6, 25), bar.open, bar.high, bar.low, bar.close, bar.volume) for bar in stale_bars[-1:]]

    report = freshness.build_data_freshness(
        report_date=date(2026, 7, 4),
        expected_instruments=[fresh, stale, missing],
        bars_by_instrument={fresh: fresh_bars, stale: stale_bars},
        stale_after_days=3,
    )

    assert report.latest_date == date(2026, 7, 3)
    assert "012922" in report.stale_symbols
    assert "017731" in report.failed_symbols
    assert report.items[0].age_days == 1

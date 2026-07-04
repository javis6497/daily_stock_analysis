from __future__ import annotations

from tests.helpers import make_bars, make_instrument, require_module


def test_build_backtest_summary_contains_quality_metrics():
    review = require_module("stock_quant.review")
    instrument = make_instrument("018044", "基金018044", "fund")

    summary = review.build_backtest_summary(
        {instrument: make_bars("up", count=120)},
        risk_profile="balanced",
    )

    assert summary.instrument_count == 1
    assert summary.average_period_return > 0
    assert summary.max_drawdown >= 0
    assert 0 <= summary.signal_success_rate <= 1
    assert "偏强" in summary.summary


def test_build_monthly_reviews_calculates_rolling_30_day_change():
    review = require_module("stock_quant.review")
    instrument = make_instrument("018044", "基金018044", "fund")

    monthly = review.build_monthly_reviews({instrument: make_bars("up", count=120)}, "balanced")

    assert len(monthly) == 1
    assert monthly[0].instrument == instrument
    assert monthly[0].monthly_change > 0
    assert monthly[0].monthly_drawdown >= 0

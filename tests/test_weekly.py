from __future__ import annotations

from tests.helpers import make_bars, make_instrument, require_module


def test_build_weekly_reviews_calculates_change_drawdown_and_signal():
    weekly = require_module("stock_quant.weekly")
    instrument = make_instrument("018044", "基金018044", "fund")

    reviews = weekly.build_weekly_reviews(
        {instrument: make_bars("up", count=90)},
        risk_profile="balanced",
    )

    assert len(reviews) == 1
    review = reviews[0]
    assert review.instrument == instrument
    assert review.signal.instrument == instrument
    assert review.weekly_change > 0
    assert review.weekly_drawdown >= 0

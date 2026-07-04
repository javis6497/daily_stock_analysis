from __future__ import annotations

from collections.abc import Mapping, Sequence

from .indicators import max_drawdown
from .models import Bar, Instrument, WeeklyHoldingReview
from .strategy import analyze_instrument


def build_weekly_reviews(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    risk_profile: str = "balanced",
) -> list[WeeklyHoldingReview]:
    reviews: list[WeeklyHoldingReview] = []
    for instrument, bars in bars_by_instrument.items():
        if not bars:
            continue
        closes = [float(bar.close) for bar in bars]
        signal = analyze_instrument(instrument, bars, risk_profile)
        reviews.append(
            WeeklyHoldingReview(
                instrument=instrument,
                signal=signal,
                weekly_change=_weekly_change(closes),
                weekly_drawdown=max_drawdown(closes[-5:]) if len(closes) >= 2 else None,
            )
        )
    return reviews


def _weekly_change(closes: Sequence[float]) -> float | None:
    if len(closes) < 2:
        return None
    start = closes[-6] if len(closes) >= 6 else closes[0]
    if start == 0:
        return None
    return closes[-1] / start - 1

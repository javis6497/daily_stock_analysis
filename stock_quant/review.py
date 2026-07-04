from __future__ import annotations

from collections.abc import Mapping, Sequence

from .indicators import max_drawdown
from .models import Bar, BacktestSummary, Instrument, MonthlyHoldingReview
from .strategy import analyze_instrument


def build_backtest_summary(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    risk_profile: str = "balanced",
) -> BacktestSummary:
    returns: list[float] = []
    drawdowns: list[float] = []
    successes = 0
    evaluated = 0
    strong_count = 0
    weak_count = 0

    for instrument, bars in bars_by_instrument.items():
        if len(bars) < 2:
            continue
        closes = [float(bar.close) for bar in bars]
        period_return = closes[-1] / closes[0] - 1 if closes[0] else 0.0
        signal = analyze_instrument(instrument, bars, risk_profile)
        returns.append(period_return)
        drawdowns.append(max_drawdown(closes))
        if signal.status == "偏强":
            strong_count += 1
            successes += int(period_return > 0)
            evaluated += 1
        elif signal.status == "偏弱":
            weak_count += 1
            successes += int(period_return < 0)
            evaluated += 1

    count = len(returns)
    average_return = sum(returns) / count if count else 0.0
    worst_drawdown = max(drawdowns) if drawdowns else 0.0
    success_rate = successes / evaluated if evaluated else 0.0
    summary = f"{count} 个标的回测；当前偏强 {strong_count} 个、偏弱 {weak_count} 个。"
    return BacktestSummary(
        instrument_count=count,
        average_period_return=average_return,
        max_drawdown=worst_drawdown,
        signal_success_rate=success_rate,
        summary=summary,
    )


def build_monthly_reviews(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    risk_profile: str = "balanced",
) -> list[MonthlyHoldingReview]:
    reviews: list[MonthlyHoldingReview] = []
    for instrument, bars in bars_by_instrument.items():
        if not bars:
            continue
        closes = [float(bar.close) for bar in bars]
        signal = analyze_instrument(instrument, bars, risk_profile)
        reviews.append(
            MonthlyHoldingReview(
                instrument=instrument,
                signal=signal,
                monthly_change=_rolling_change(closes, 30),
                monthly_drawdown=max_drawdown(closes[-30:]) if len(closes) >= 2 else None,
            )
        )
    return reviews


def _rolling_change(closes: Sequence[float], days: int) -> float | None:
    if len(closes) < 2:
        return None
    start_index = -days - 1
    start = closes[start_index] if len(closes) > days else closes[0]
    if start == 0:
        return None
    return closes[-1] / start - 1

from __future__ import annotations

from collections.abc import Sequence

from .models import Bar, Instrument
from .strategy import analyze_instrument


def run_backtest(
    instrument: Instrument,
    bars: Sequence[Bar],
    risk_profile: str = "balanced",
    benchmark_bars: Sequence[Bar] | None = None,
    buy_fee_rate: float = 0.001,
    sell_fee_rate: float = 0.005,
    slippage_rate: float = 0.001,
    turnover_cost_rate: float = 0.001,
) -> dict[str, float | int | str | None]:
    signal = analyze_instrument(instrument, bars, risk_profile)
    first = float(bars[0].close)
    last = float(bars[-1].close)
    gross_return = last / first - 1 if first else 0.0
    estimated_cost = buy_fee_rate + sell_fee_rate + slippage_rate * 2 + turnover_cost_rate
    net_return = gross_return - estimated_cost
    benchmark_return = _period_return(benchmark_bars)
    excess_return = None if benchmark_return is None else net_return - benchmark_return
    return {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "signal": signal.status,
        "period_return": round(gross_return * 100, 2),
        "gross_return_pct": round(gross_return * 100, 2),
        "estimated_cost_pct": round(estimated_cost * 100, 2),
        "net_return_pct": round(net_return * 100, 2),
        "benchmark_return_pct": None if benchmark_return is None else round(benchmark_return * 100, 2),
        "excess_return_pct": None if excess_return is None else round(excess_return * 100, 2),
        "holding_days": (bars[-1].date - bars[0].date).days,
        "last_close": signal.last_close,
    }


def _period_return(bars: Sequence[Bar] | None) -> float | None:
    if not bars or len(bars) < 2:
        return None
    first = float(bars[0].close)
    if first == 0:
        return None
    return float(bars[-1].close) / first - 1

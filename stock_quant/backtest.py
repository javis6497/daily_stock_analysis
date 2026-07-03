from __future__ import annotations

from collections.abc import Sequence

from .models import Bar, Instrument
from .strategy import analyze_instrument


def run_backtest(instrument: Instrument, bars: Sequence[Bar], risk_profile: str = "balanced") -> dict[str, float | str]:
    signal = analyze_instrument(instrument, bars, risk_profile)
    first = float(bars[0].close)
    last = float(bars[-1].close)
    return {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "signal": signal.status,
        "period_return": round((last / first - 1) * 100, 2),
        "last_close": signal.last_close,
    }

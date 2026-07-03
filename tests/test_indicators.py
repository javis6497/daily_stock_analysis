from __future__ import annotations

from tests.helpers import make_bars, require_module


def test_sma_returns_none_until_window_is_available():
    indicators = require_module("stock_quant.indicators")

    assert indicators.sma([1, 2, 3, 4], 3) == [None, None, 2.0, 3.0]


def test_rsi_macd_and_atr_return_usable_latest_values():
    indicators = require_module("stock_quant.indicators")
    bars = make_bars("up", count=90)
    closes = [bar.close for bar in bars]

    rsi_values = indicators.rsi(closes, period=14)
    macd_line, signal_line, histogram = indicators.macd(closes)
    atr_values = indicators.atr(bars, period=14)

    assert rsi_values[-1] is not None
    assert rsi_values[-1] > 60
    assert macd_line[-1] is not None
    assert signal_line[-1] is not None
    assert histogram[-1] is not None
    assert atr_values[-1] > 0

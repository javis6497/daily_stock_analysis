from __future__ import annotations

from tests.helpers import make_bars, make_instrument, require_module


def test_balanced_strategy_marks_confirmed_uptrend_as_strong():
    strategy = require_module("stock_quant.strategy")
    instrument = make_instrument("000001", "平安银行")
    bars = make_bars("up", count=90)

    signal = strategy.analyze_instrument(instrument, bars, risk_profile="balanced")

    assert signal.status == "偏强"
    assert signal.action == "回踩观察"
    assert signal.buy_zone.lower < signal.last_close
    assert signal.buy_zone.upper <= signal.last_close
    assert signal.stop_loss < signal.last_close
    assert signal.take_profit > signal.last_close
    assert signal.reasons


def test_balanced_strategy_marks_broken_downtrend_as_weak():
    strategy = require_module("stock_quant.strategy")
    instrument = make_instrument("000002", "弱势样例")
    bars = make_bars("down", count=90)

    signal = strategy.analyze_instrument(instrument, bars, risk_profile="balanced")

    assert signal.status == "偏弱"
    assert signal.action == "降低仓位"
    assert signal.stop_loss <= signal.last_close
    assert any("趋势" in reason for reason in signal.reasons)

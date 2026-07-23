from __future__ import annotations

from tests.helpers import make_bars, make_instrument, require_module


def test_run_backtest_includes_costs_holding_days_and_benchmark():
    module = require_module("stock_quant.backtest")
    instrument = make_instrument("018044", "基金018044", "fund")
    bars = make_bars("up", count=90)
    benchmark_bars = make_bars("up", count=90)

    result = module.run_backtest(
        instrument,
        bars,
        risk_profile="balanced",
        benchmark_bars=benchmark_bars,
        buy_fee_rate=0.001,
        sell_fee_rate=0.005,
        slippage_rate=0.001,
        turnover_cost_rate=0.001,
    )

    assert result["holding_days"] == (bars[-1].date - bars[0].date).days
    assert result["gross_return_pct"] == result["period_return"]
    assert result["estimated_cost_pct"] > 0
    assert result["strategy_gross_return_pct"] >= result["net_return_pct"]
    assert result["benchmark_return_pct"] is not None
    assert result["excess_return_pct"] is not None
    assert result["decision_lag_bars"] == 1
    assert result["lookahead_safe"] == "yes"
    assert result["sample_count"] == 30
    assert result["trade_count"] >= 1


def test_walk_forward_result_is_unchanged_when_future_bars_are_removed():
    module = require_module("stock_quant.backtest")
    instrument = make_instrument("018044", "基金018044", "fund")
    bars = make_bars("up", count=100)

    prefix = module.run_backtest(instrument, bars[:90], risk_profile="balanced")
    full = module.run_backtest(instrument, bars, risk_profile="balanced")

    assert prefix["sample_count"] == 30
    assert full["sample_count"] == 40
    assert prefix["decision_lag_bars"] == full["decision_lag_bars"] == 1

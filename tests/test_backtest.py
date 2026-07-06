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
    assert result["estimated_cost_pct"] == 0.9
    assert result["net_return_pct"] < result["gross_return_pct"]
    assert result["benchmark_return_pct"] is not None
    assert result["excess_return_pct"] is not None

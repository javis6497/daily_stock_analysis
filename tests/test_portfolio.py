from __future__ import annotations

from tests.helpers import require_module


def test_build_portfolio_summary_calculates_weights_pnl_and_limit_warnings():
    models = require_module("stock_quant.models")
    portfolio = require_module("stock_quant.portfolio")
    fund = models.Instrument(
        symbol="018044",
        name="基金018044",
        market="cn",
        asset_type="fund",
        cost_price=2.0,
        holding_amount=10000,
        max_weight=0.50,
    )
    etf = models.Instrument(
        symbol="510300",
        name="沪深300ETF",
        market="cn",
        asset_type="etf",
        cost_price=1.0,
        holding_amount=5000,
        max_weight=0.40,
    )
    signals = [
        models.Signal(
            instrument=fund,
            status="偏强",
            action="回踩观察",
            last_close=2.2,
            buy_zone=models.PriceRange(2.1, 2.2),
            stop_loss=1.9,
            take_profit=2.4,
            confidence=0.78,
            reasons=("趋势向上",),
            risks=("外部事件风险",),
        ),
        models.Signal(
            instrument=etf,
            status="观察",
            action="等待确认",
            last_close=1.0,
            buy_zone=models.PriceRange(0.95, 1.0),
            stop_loss=0.9,
            take_profit=1.1,
            confidence=0.52,
            reasons=("等待确认",),
            risks=("风格切换",),
        ),
    ]

    summary = portfolio.build_portfolio_summary(signals)

    assert summary.total_principal == 15000
    assert round(summary.total_market_value, 2) == 16000
    assert round(summary.total_pnl_amount, 2) == 1000
    assert round(summary.total_pnl_pct, 4) == round(1000 / 15000, 4)
    assert summary.positions[0].weight > 0.5
    assert summary.positions[0].max_weight_breached is True
    assert "超过最大仓位" in summary.warnings[0]

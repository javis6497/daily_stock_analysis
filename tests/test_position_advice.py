from __future__ import annotations

from tests.helpers import require_module


def _signal(symbol: str, status: str, target_weight: float = 0.2, max_weight: float = 0.3):
    models = require_module("stock_quant.models")
    instrument = models.Instrument(
        symbol=symbol,
        name=f"基金{symbol}",
        market="cn",
        asset_type="fund",
        target_weight=target_weight,
        max_weight=max_weight,
        cost_price=1.0,
        holding_amount=10000,
    )
    return models.Signal(
        instrument=instrument,
        status=status,
        action="回踩观察" if status == "偏强" else "降低仓位",
        last_close=1.1,
        buy_zone=models.PriceRange(1.0, 1.1),
        stop_loss=0.95,
        take_profit=1.25,
        confidence=0.78,
        reasons=("趋势测试",),
        risks=("风险测试",),
    )


def test_build_position_advices_uses_signal_market_and_current_weight():
    models = require_module("stock_quant.models")
    module = require_module("stock_quant.position_advice")

    strong = _signal("018044", "偏强")
    weak = _signal("012922", "偏弱")
    portfolio = models.PortfolioSummary(
        total_principal=30000,
        total_market_value=30000,
        total_pnl_amount=0,
        total_pnl_pct=0,
        positions=(
            models.PortfolioPosition(
                instrument=strong.instrument,
                market_value=21000,
                principal=20000,
                pnl_amount=1000,
                pnl_pct=0.05,
                weight=0.7,
            ),
            models.PortfolioPosition(
                instrument=weak.instrument,
                market_value=9000,
                principal=10000,
                pnl_amount=-1000,
                pnl_pct=-0.1,
                weight=0.3,
            ),
        ),
    )
    market = models.MarketEnvironment(
        status="防守",
        risk_level="偏高",
        position_bias="降低进攻仓位",
        summary="宽基指数偏弱。",
    )

    advices = module.build_position_advices([strong, weak], portfolio, market)

    assert advices["018044"].suggested_min == 0.12
    assert advices["018044"].suggested_max == 0.24
    assert advices["018044"].current_weight == 0.7
    assert advices["018044"].action == "高于建议区间，优先控制仓位"
    assert advices["012922"].suggested_max == 0.08
    assert advices["012922"].action == "高于建议区间，优先控制仓位"

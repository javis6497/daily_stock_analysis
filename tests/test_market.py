from __future__ import annotations

from tests.helpers import make_bars, require_module


def test_analyze_market_environment_detects_offensive_regime():
    market = require_module("stock_quant.market")

    environment = market.analyze_market_environment(
        {
            market.MARKET_INDEXES[0]: make_bars("up", count=90),
            market.MARKET_INDEXES[1]: make_bars("up", count=90),
            market.MARKET_INDEXES[2]: make_bars("up", count=90),
        }
    )

    assert environment.status == "进攻"
    assert environment.risk_level == "偏低"
    assert "均衡偏进攻" in environment.position_bias
    assert len(environment.index_signals) == 3


def test_analyze_market_environment_detects_defensive_regime():
    market = require_module("stock_quant.market")

    environment = market.analyze_market_environment(
        {
            market.MARKET_INDEXES[0]: make_bars("down", count=90),
            market.MARKET_INDEXES[1]: make_bars("down", count=90),
            market.MARKET_INDEXES[2]: make_bars("up", count=90),
        }
    )

    assert environment.status == "防守"
    assert environment.risk_level == "偏高"
    assert "控制仓位" in environment.position_bias

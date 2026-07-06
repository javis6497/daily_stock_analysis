from __future__ import annotations

from tests.helpers import make_bars, require_module


def test_build_fund_intraday_estimates_uses_proxy_bar_change():
    models = require_module("stock_quant.models")
    module = require_module("stock_quant.fund_intraday")

    fund = models.Instrument(
        symbol="018044",
        name="基金018044",
        market="cn",
        asset_type="fund",
        proxy_symbol="159915",
        proxy_name="创业板ETF",
        proxy_asset_type="etf",
    )
    signal = models.Signal(
        instrument=fund,
        status="观察",
        action="等待确认",
        last_close=2.0,
        buy_zone=models.PriceRange(1.9, 2.0),
        stop_loss=1.8,
        take_profit=2.2,
        confidence=0.52,
        reasons=("等待确认",),
        risks=("净值滞后",),
    )
    proxy_bars = make_bars("up", count=90)
    last = proxy_bars[-1]
    proxy_bars[-1] = models.Bar(
        date=last.date,
        open=10.0,
        high=10.4,
        low=9.8,
        close=10.3,
        volume=1000000,
    )

    estimates = module.build_fund_intraday_estimates(
        [signal],
        {fund.proxy_instrument(): proxy_bars},
        market_environment=None,
    )

    estimate = estimates["018044"]
    assert estimate.proxy_symbol == "159915"
    assert estimate.proxy_name == "创业板ETF"
    assert estimate.estimated_pct == 0.03
    assert "代理标的" in estimate.note


def test_build_fund_intraday_estimates_falls_back_to_market_environment():
    models = require_module("stock_quant.models")
    module = require_module("stock_quant.fund_intraday")

    fund = models.Instrument(symbol="018044", name="基金018044", market="cn", asset_type="fund")
    signal = models.Signal(
        instrument=fund,
        status="观察",
        action="等待确认",
        last_close=2.0,
        buy_zone=models.PriceRange(1.9, 2.0),
        stop_loss=1.8,
        take_profit=2.2,
        confidence=0.52,
        reasons=("等待确认",),
        risks=("净值滞后",),
    )
    market = models.MarketEnvironment(
        status="进攻",
        risk_level="偏低",
        position_bias="可维持均衡偏进攻",
        summary="宽基指数趋势向上。",
    )

    estimates = module.build_fund_intraday_estimates([signal], {}, market)

    assert estimates["018044"].estimated_pct == 0.005
    assert "市场环境" in estimates["018044"].note

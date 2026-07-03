from __future__ import annotations

import sys

from tests.helpers import make_instrument, require_module


def test_build_recommendation_pool_excludes_watchlist_and_adds_default_universe():
    config_mod = require_module("stock_quant.config")
    universe = require_module("stock_quant.universe")
    watched = make_instrument("510300", "沪深300ETF", "etf")
    manual_candidate = make_instrument("510300", "沪深300ETF", "etf")
    app_config = config_mod.AppConfig(
        watchlist=[watched],
        candidate_pool=[manual_candidate],
        recommendation=config_mod.RecommendationConfig(
            enabled=True,
            include_default_universe=True,
        ),
    )

    candidates = universe.build_recommendation_pool(app_config)
    symbols = [instrument.symbol for instrument in candidates]

    assert "510300" not in symbols
    assert "600519" in symbols
    assert "159915" in symbols
    assert len(symbols) == len(set(symbols))


class _FakeSpotFrame:
    def iterrows(self):
        rows = [
            {
                "代码": "600111",
                "名称": "高流动龙头",
                "成交额": 2_000_000_000,
                "总市值": 120_000_000_000,
                "涨跌幅": 2.5,
                "市盈率-动态": 24.0,
                "市净率": 3.2,
            },
            {
                "代码": "600222",
                "名称": "低成交股票",
                "成交额": 10_000_000,
                "总市值": 90_000_000_000,
                "涨跌幅": 1.0,
                "市盈率-动态": 20.0,
                "市净率": 2.0,
            },
            {
                "代码": "600333",
                "名称": "高估值股票",
                "成交额": 1_500_000_000,
                "总市值": 80_000_000_000,
                "涨跌幅": 1.0,
                "市盈率-动态": 120.0,
                "市净率": 2.0,
            },
            {
                "代码": "600444",
                "名称": "ST风险股",
                "成交额": 2_500_000_000,
                "总市值": 100_000_000_000,
                "涨跌幅": 1.0,
                "市盈率-动态": 20.0,
                "市净率": 2.0,
            },
        ]
        for idx, row in enumerate(rows):
            yield idx, row


class _FakeAkShare:
    def stock_zh_a_spot_em(self):
        return _FakeSpotFrame()


def test_build_recommendation_pool_filters_dynamic_a_share_universe(monkeypatch):
    config_mod = require_module("stock_quant.config")
    universe = require_module("stock_quant.universe")
    monkeypatch.setitem(sys.modules, "akshare", _FakeAkShare())
    app_config = config_mod.AppConfig(
        data=config_mod.DataConfig(provider="akshare"),
        watchlist=[make_instrument("600111", "高流动龙头", "stock")],
        recommendation=config_mod.RecommendationConfig(
            enabled=True,
            include_default_universe=False,
            include_dynamic_a_shares=True,
            dynamic_a_share_limit=5,
            min_turnover=500_000_000,
            min_market_cap=50_000_000_000,
            min_pe=0,
            max_pe=80,
            min_pb=0,
            max_pb=10,
            min_pct_change=-5,
            max_pct_change=7,
        ),
    )

    candidates = universe.build_recommendation_pool(app_config)
    symbols = [instrument.symbol for instrument in candidates]

    assert "600111" not in symbols
    assert "600222" not in symbols
    assert "600333" not in symbols
    assert "600444" not in symbols


def test_dynamic_a_share_universe_adds_filtered_non_watchlist_stocks(monkeypatch):
    config_mod = require_module("stock_quant.config")
    universe = require_module("stock_quant.universe")
    monkeypatch.setitem(sys.modules, "akshare", _FakeAkShare())
    app_config = config_mod.AppConfig(
        data=config_mod.DataConfig(provider="akshare"),
        watchlist=[],
        recommendation=config_mod.RecommendationConfig(
            enabled=True,
            include_default_universe=False,
            include_dynamic_a_shares=True,
            dynamic_a_share_limit=5,
            min_turnover=500_000_000,
            min_market_cap=50_000_000_000,
            min_pe=0,
            max_pe=80,
            min_pb=0,
            max_pb=10,
            min_pct_change=-5,
            max_pct_change=7,
        ),
    )

    candidates = universe.build_recommendation_pool(app_config)

    assert [(candidate.symbol, candidate.name, candidate.asset_type) for candidate in candidates] == [
        ("600111", "高流动龙头", "stock")
    ]

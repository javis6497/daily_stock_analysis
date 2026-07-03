from __future__ import annotations

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

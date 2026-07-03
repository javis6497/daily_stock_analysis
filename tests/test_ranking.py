from __future__ import annotations

from tests.helpers import make_bars, make_instrument, require_module


def test_rank_candidates_prefers_stronger_trend_and_limits_top_n():
    ranking = require_module("stock_quant.ranking")
    strong = make_instrument("510300", "沪深300ETF", "etf")
    weak = make_instrument("000002", "弱势股票", "stock")

    ranked = ranking.rank_candidates(
        {
            strong: make_bars("up", count=90),
            weak: make_bars("down", count=90),
        },
        top_n=1,
        risk_profile="balanced",
    )

    assert len(ranked) == 1
    assert ranked[0].instrument.symbol == "510300"
    assert ranked[0].score > 0

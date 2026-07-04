from __future__ import annotations

from datetime import timedelta

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


def test_rank_candidates_limits_same_group_exposure():
    ranking = require_module("stock_quant.ranking")
    models = require_module("stock_quant.models")
    tech_a = models.Instrument("588000", "科创50ETF", "cn", "etf", tags=("科技", "候选"))
    tech_b = models.Instrument("512760", "芯片ETF", "cn", "etf", tags=("科技", "候选"))
    finance = models.Instrument("512880", "证券ETF", "cn", "etf", tags=("金融", "候选"))

    ranked = ranking.rank_candidates(
        {
            tech_a: make_bars("up", count=90),
            tech_b: make_bars("up", count=90),
            finance: make_bars("up", count=90),
        },
        top_n=3,
        risk_profile="balanced",
        max_per_group=1,
    )

    groups = [candidate.group for candidate in ranked]
    assert groups.count("科技") == 1
    assert groups.count("金融") == 1
    assert len(ranked) == 2


def test_rank_candidates_excludes_abnormal_single_day_surge():
    ranking = require_module("stock_quant.ranking")
    models = require_module("stock_quant.models")
    normal = make_instrument("510300", "沪深300ETF", "etf")
    surged = make_instrument("159995", "芯片ETF", "etf")
    bars = make_bars("up", count=89)
    last = bars[-1]
    surged_bars = bars + [
        models.Bar(
            date=last.date + timedelta(days=1),
            open=last.close,
            high=last.close * 1.13,
            low=last.close * 1.10,
            close=last.close * 1.12,
            volume=last.volume,
        )
    ]

    ranked = ranking.rank_candidates(
        {
            normal: make_bars("up", count=90),
            surged: surged_bars,
        },
        top_n=5,
        risk_profile="balanced",
        max_single_day_pct=0.07,
    )

    assert [candidate.instrument.symbol for candidate in ranked] == ["510300"]

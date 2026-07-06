from __future__ import annotations

from tests.helpers import make_bars, make_instrument, require_module


def test_build_fund_quality_profiles_scores_return_drawdown_and_fee_data():
    module = require_module("stock_quant.fund_quality")
    fund = make_instrument("018044", "基金018044", "fund")
    bars = make_bars("up", count=130)

    profiles = module.build_fund_quality_profiles(
        {fund: bars},
        metadata={
            "018044": {
                "fund_size": 8_000_000_000,
                "manager_tenure_days": 1200,
                "category_rank": "35/500",
                "fee_rate": 0.015,
                "holding_concentration": 0.42,
            }
        },
    )

    profile = profiles["018044"]
    assert profile.fund_size == 8_000_000_000
    assert profile.manager_tenure_days == 1200
    assert profile.category_rank == "35/500"
    assert profile.return_1m is not None
    assert profile.return_3m is not None
    assert profile.max_drawdown is not None
    assert profile.quality_score > 70


def test_rank_candidates_can_attach_fund_quality_profile():
    models = require_module("stock_quant.models")
    ranking = require_module("stock_quant.ranking")
    fund = make_instrument("159915", "创业板ETF", "etf")
    profile = models.FundQualityProfile(
        instrument=fund,
        quality_score=88,
        return_1m=0.03,
        return_3m=0.08,
        return_6m=0.12,
        return_12m=0.18,
        max_drawdown=0.08,
    )

    candidates = ranking.rank_candidates(
        {fund: make_bars("up", count=130)},
        top_n=1,
        risk_profile="balanced",
        quality_profiles={"159915": profile},
    )

    assert candidates[0].quality_profile == profile
    assert any("基金质量" in reason for reason in candidates[0].reasons)

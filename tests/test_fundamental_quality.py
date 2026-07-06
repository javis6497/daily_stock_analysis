from __future__ import annotations

from tests.helpers import make_instrument, require_module


def test_build_fundamental_quality_profiles_scores_reasonable_stock_metrics():
    module = require_module("stock_quant.fundamental_quality")
    stock = make_instrument("600519", "贵州茅台", "stock")

    profiles = module.build_fundamental_quality_profiles(
        [stock],
        metadata={
            "600519": {
                "roe": 0.28,
                "gross_margin": 0.72,
                "debt_ratio": 0.18,
                "operating_cashflow_ratio": 1.18,
                "pe": 28,
                "pb": 8,
                "dividend_yield": 0.018,
            }
        },
    )

    profile = profiles["600519"]
    assert profile.quality_score >= 80
    assert profile.roe == 0.28
    assert profile.gross_margin == 0.72
    assert "ROE" in "；".join(profile.reasons)


def test_rank_candidates_uses_stock_fundamental_quality_profile():
    models = require_module("stock_quant.models")
    ranking = require_module("stock_quant.ranking")
    stock = make_instrument("600519", "贵州茅台", "stock")
    profile = models.FundamentalQualityProfile(
        instrument=stock,
        quality_score=86,
        roe=0.28,
        gross_margin=0.72,
        debt_ratio=0.18,
        operating_cashflow_ratio=1.18,
        pe=28,
        pb=8,
        dividend_yield=0.018,
        reasons=("ROE 优秀",),
    )

    candidates = ranking.rank_candidates(
        {stock: __import__("tests.helpers", fromlist=["make_bars"]).make_bars("up", count=130)},
        top_n=1,
        risk_profile="balanced",
        quality_profiles={"600519": profile},
    )

    assert candidates[0].quality_profile == profile
    assert any("基本面质量" in reason for reason in candidates[0].reasons)

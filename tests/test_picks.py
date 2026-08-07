from __future__ import annotations

from datetime import date

from tests.helpers import require_module
from stock_quant.models import CandidateScore, Instrument, PriceRange, Signal


def _candidate(symbol: str, name: str, score: float) -> CandidateScore:
    instrument = Instrument(symbol=symbol, name=name, market="cn", asset_type="etf")
    return CandidateScore(
        instrument=instrument,
        score=score,
        group="测试",
        reasons=("资金流入",),
        signal=Signal(
            instrument=instrument,
            status="偏强",
            action="关注",
            last_close=3.6,
            buy_zone=PriceRange(3.5, 3.6),
            stop_loss=3.4,
            take_profit=4.0,
            confidence=0.7,
            reasons=("资金流入",),
            risks=(),
        ),
    )


def test_candidate_picks_keeps_top_three_with_prices():
    picks_mod = require_module("stock_quant.picks")
    picks = picks_mod.candidate_picks([_candidate("510300", "沪深300ETF", 0.85)], "premarket", max_picks=3)
    assert len(picks) == 1
    pick = picks[0]
    assert pick["session"] == "premarket"
    assert pick["symbol"] == "510300"
    assert pick["ref_price"] == 3.6
    assert pick["buy_low"] == 3.5
    assert pick["risk"] == 3.4


def test_save_load_merge_picks_roundtrip(tmp_path):
    picks_mod = require_module("stock_quant.picks")

    premarket = picks_mod.candidate_picks([_candidate("510300", "沪深300ETF", 0.85)], "premarket")
    picks_mod.save_daily_picks(tmp_path, date(2026, 8, 6), premarket)

    intraday = picks_mod.candidate_picks([_candidate("510500", "中证500ETF", 0.8)], "fund_action")
    existing = picks_mod.load_daily_picks(tmp_path, date(2026, 8, 6))
    picks_mod.save_daily_picks(tmp_path, date(2026, 8, 6), picks_mod.merge_picks(existing, intraday))

    loaded = picks_mod.load_daily_picks(tmp_path, date(2026, 8, 6))
    assert len(loaded) == 2
    assert [p["session"] for p in loaded] == ["premarket", "fund_action"]
    assert loaded[1]["symbol"] == "510500"

    # another day starts empty
    assert picks_mod.load_daily_picks(tmp_path, date(2026, 8, 7)) == []


def test_merge_picks_deduplicates_same_session_and_symbol():
    picks_mod = require_module("stock_quant.picks")
    a = picks_mod.candidate_picks([_candidate("510300", "沪深300ETF", 0.85)], "premarket")
    a2 = picks_mod.candidate_picks([_candidate("510300", "沪深300ETF", 0.9)], "premarket")
    merged = picks_mod.merge_picks(a, a2)
    assert len(merged) == 1

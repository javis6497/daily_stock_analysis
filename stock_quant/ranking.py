from __future__ import annotations

from collections.abc import Mapping, Sequence

from .indicators import max_drawdown, sma
from .models import Bar, CandidateScore, Instrument
from .strategy import analyze_instrument


def rank_candidates(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    top_n: int,
    risk_profile: str = "balanced",
) -> list[CandidateScore]:
    scores: list[CandidateScore] = []
    for instrument, bars in bars_by_instrument.items():
        if not bars:
            continue
        signal = analyze_instrument(instrument, bars, risk_profile)
        closes = [float(bar.close) for bar in bars]
        ma60 = sma(closes, 60)[-1]
        trend_bonus = 0.0 if ma60 in (None, 0) else (closes[-1] / ma60 - 1) * 100
        drawdown_penalty = max_drawdown(closes[-60:]) * 35
        status_base = {"偏强": 70.0, "观察": 45.0, "偏弱": 18.0}.get(signal.status, 35.0)
        fund_bonus = 4.0 if instrument.asset_type in {"etf", "fund"} else 0.0
        score = max(0.0, status_base + trend_bonus + fund_bonus - drawdown_penalty)
        reasons = (
            f"状态 {signal.status}",
            f"趋势得分 {trend_bonus:.1f}",
            f"回撤惩罚 {drawdown_penalty:.1f}",
        )
        scores.append(
            CandidateScore(
                instrument=instrument,
                score=round(score, 2),
                signal=signal,
                reasons=reasons,
            )
        )

    return sorted(scores, key=lambda item: item.score, reverse=True)[: max(0, top_n)]

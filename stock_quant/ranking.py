from __future__ import annotations

from collections.abc import Mapping, Sequence

from .indicators import max_drawdown, sma
from .models import Bar, CandidateScore, FundQualityProfile, Instrument, MarketEnvironment
from .strategy import analyze_instrument


def rank_candidates(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    top_n: int,
    risk_profile: str = "balanced",
    max_per_group: int = 2,
    max_single_day_pct: float = 0.07,
    market_environment: MarketEnvironment | None = None,
    quality_profiles: Mapping[str, FundQualityProfile] | None = None,
) -> list[CandidateScore]:
    quality_profiles = quality_profiles or {}
    scores: list[CandidateScore] = []
    for instrument, bars in bars_by_instrument.items():
        if not bars:
            continue
        closes = [float(bar.close) for bar in bars]
        single_day_pct = _single_day_pct(closes)
        if single_day_pct is not None and abs(single_day_pct) > max_single_day_pct:
            continue
        signal = analyze_instrument(instrument, bars, risk_profile)
        ma60 = sma(closes, 60)[-1]
        trend_bonus = 0.0 if ma60 in (None, 0) else (closes[-1] / ma60 - 1) * 100
        drawdown_penalty = max_drawdown(closes[-60:]) * 35
        status_base = {"偏强": 70.0, "观察": 45.0, "偏弱": 18.0}.get(signal.status, 35.0)
        fund_bonus = 4.0 if instrument.asset_type in {"etf", "fund"} else 0.0
        market_adjustment = _market_adjustment(instrument, market_environment)
        quality_profile = quality_profiles.get(instrument.symbol)
        quality_bonus = 0.0
        if quality_profile is not None:
            quality_bonus = (quality_profile.quality_score - 50.0) * 0.12
        score = max(0.0, status_base + trend_bonus + fund_bonus + market_adjustment + quality_bonus - drawdown_penalty)
        group = candidate_group(instrument)
        reasons = [
            f"状态 {signal.status}",
            f"趋势得分 {trend_bonus:.1f}",
            f"回撤惩罚 {drawdown_penalty:.1f}",
            f"分组 {group}",
        ]
        if single_day_pct is not None:
            reasons.append(f"单日涨跌 {single_day_pct:.2%}")
        if market_environment is not None:
            reasons.append(f"市场环境 {market_environment.status}")
        if quality_profile is not None:
            reasons.append(f"基金质量 {quality_profile.quality_score:.1f}")
        scores.append(
            CandidateScore(
                instrument=instrument,
                score=round(score, 2),
                signal=signal,
                reasons=tuple(reasons),
                group=group,
                quality_profile=quality_profile,
            )
        )

    ranked = sorted(scores, key=lambda item: item.score, reverse=True)
    return _apply_group_diversity(ranked, max(0, top_n), max(1, max_per_group))


def candidate_group(instrument: Instrument) -> str:
    generic = {"候选", "自选", "动态A股", "动态ETF", "测试", "持仓"}
    for tag in instrument.tags:
        if tag and tag not in generic:
            return tag
    return instrument.asset_type.upper()


def _apply_group_diversity(
    ranked: Sequence[CandidateScore],
    top_n: int,
    max_per_group: int,
) -> list[CandidateScore]:
    selected: list[CandidateScore] = []
    group_counts: dict[str, int] = {}
    for candidate in ranked:
        count = group_counts.get(candidate.group, 0)
        if count >= max_per_group:
            continue
        selected.append(candidate)
        group_counts[candidate.group] = count + 1
        if len(selected) >= top_n:
            break
    return selected


def _single_day_pct(closes: Sequence[float]) -> float | None:
    if len(closes) < 2 or closes[-2] == 0:
        return None
    return closes[-1] / closes[-2] - 1


def _market_adjustment(
    instrument: Instrument,
    market_environment: MarketEnvironment | None,
) -> float:
    if market_environment is None:
        return 0.0
    asset_type = instrument.asset_type.lower()
    if market_environment.status == "防守":
        return 2.0 if asset_type in {"etf", "fund"} else -6.0
    if market_environment.status == "进攻":
        return 3.0 if asset_type == "stock" else 1.5
    return 0.0

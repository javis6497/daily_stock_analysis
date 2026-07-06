from __future__ import annotations

from collections.abc import Mapping, Sequence

from .models import MarketEnvironment, PortfolioSummary, PositionAdvice, Signal


def build_position_advices(
    signals: Sequence[Signal],
    portfolio_summary: PortfolioSummary | None = None,
    market_environment: MarketEnvironment | None = None,
) -> dict[str, PositionAdvice]:
    current_weights = _current_weights(portfolio_summary)
    advices: dict[str, PositionAdvice] = {}
    for signal in signals:
        instrument = signal.instrument
        suggested_min, suggested_max = _suggested_band(signal, market_environment)
        current_weight = current_weights.get(instrument.symbol)
        action = _position_action(current_weight, suggested_min, suggested_max)
        reason = _reason(signal, market_environment)
        advices[instrument.symbol] = PositionAdvice(
            instrument=instrument,
            current_weight=current_weight,
            suggested_min=suggested_min,
            suggested_max=suggested_max,
            action=action,
            reason=reason,
        )
    return advices


def _current_weights(portfolio_summary: PortfolioSummary | None) -> Mapping[str, float]:
    if portfolio_summary is None:
        return {}
    return {position.instrument.symbol: position.weight for position in portfolio_summary.positions}


def _suggested_band(
    signal: Signal,
    market_environment: MarketEnvironment | None,
) -> tuple[float, float]:
    target = signal.instrument.target_weight
    if target is None:
        target = 0.18 if signal.instrument.asset_type.lower() in {"fund", "etf"} else 0.10
    max_weight = signal.instrument.max_weight if signal.instrument.max_weight is not None else min(1.0, target * 1.5)

    if signal.status == "偏强":
        lower = target * 0.60
        upper = target * 1.20
    elif signal.status == "偏弱":
        lower = 0.0
        upper = target * 0.50
    else:
        lower = target * 0.30
        upper = target * 0.80

    if market_environment and market_environment.status == "进攻" and signal.status == "偏强":
        upper = max(upper, target * 1.30)
    if market_environment and market_environment.status == "防守" and signal.status != "偏强":
        upper *= 0.80

    lower = max(0.0, min(lower, max_weight))
    upper = max(lower, min(upper, max_weight))
    return round(lower, 4), round(upper, 4)


def _position_action(
    current_weight: float | None,
    suggested_min: float,
    suggested_max: float,
) -> str:
    if current_weight is None:
        return "未配置持仓金额，先按建议区间人工核对"
    if current_weight > suggested_max:
        return "高于建议区间，优先控制仓位"
    if current_weight < suggested_min:
        return "低于建议区间，只在信号确认后分批补足"
    return "位于建议区间，维持观察"


def _reason(signal: Signal, market_environment: MarketEnvironment | None) -> str:
    parts = [f"信号{signal.status}"]
    if market_environment is not None:
        parts.append(f"市场{market_environment.status}")
    if signal.instrument.target_weight is not None:
        parts.append(f"目标仓位{signal.instrument.target_weight:.0%}")
    return "；".join(parts)

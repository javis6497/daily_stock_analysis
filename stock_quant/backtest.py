from __future__ import annotations

import math
from statistics import fmean, pstdev
from collections.abc import Sequence

from .indicators import max_drawdown
from .models import Bar, Instrument
from .strategy import analyze_instrument


def run_backtest(
    instrument: Instrument,
    bars: Sequence[Bar],
    risk_profile: str = "balanced",
    benchmark_bars: Sequence[Bar] | None = None,
    buy_fee_rate: float = 0.001,
    sell_fee_rate: float = 0.005,
    slippage_rate: float = 0.001,
    turnover_cost_rate: float = 0.001,
) -> dict[str, float | int | str | None]:
    if len(bars) < 2:
        raise ValueError("backtest requires at least two bars")

    signal = analyze_instrument(instrument, bars, risk_profile)
    first = float(bars[0].close)
    last = float(bars[-1].close)
    period_return = last / first - 1 if first else 0.0
    net = _simulate_walk_forward(
        instrument,
        bars,
        risk_profile,
        buy_fee_rate,
        sell_fee_rate,
        slippage_rate,
        turnover_cost_rate,
    )
    gross = _simulate_walk_forward(
        instrument,
        bars,
        risk_profile,
        0.0,
        0.0,
        0.0,
        0.0,
    )
    benchmark_return = _benchmark_return(benchmark_bars)
    excess_return = None if benchmark_return is None else net["return"] - benchmark_return
    return {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "signal": signal.status,
        "period_return": round(period_return * 100, 2),
        "gross_return_pct": round(period_return * 100, 2),
        "strategy_gross_return_pct": round(gross["return"] * 100, 2),
        "estimated_cost_pct": round(net["cost"] * 100, 2),
        "net_return_pct": round(net["return"] * 100, 2),
        "benchmark_return_pct": None if benchmark_return is None else round(benchmark_return * 100, 2),
        "excess_return_pct": None if excess_return is None else round(excess_return * 100, 2),
        "max_drawdown_pct": round(net["max_drawdown"] * 100, 2),
        "annualized_return_pct": round(net["annualized_return"] * 100, 2),
        "sharpe_ratio": round(net["sharpe_ratio"], 3),
        "trade_count": int(net["trade_count"]),
        "signal_success_rate_pct": round(net["signal_success_rate"] * 100, 2),
        "average_exposure_pct": round(net["average_exposure"] * 100, 2),
        "sample_count": int(net["sample_count"]),
        "decision_lag_bars": 1,
        "lookahead_safe": "yes",
        "holding_days": (bars[-1].date - bars[0].date).days,
        "last_close": signal.last_close,
    }


def _simulate_walk_forward(
    instrument: Instrument,
    bars: Sequence[Bar],
    risk_profile: str,
    buy_fee_rate: float,
    sell_fee_rate: float,
    slippage_rate: float,
    turnover_cost_rate: float,
    warmup_bars: int = 60,
    rebalance_threshold: float = 0.02,
) -> dict[str, float | int]:
    if len(bars) <= warmup_bars:
        return {
            "return": 0.0,
            "cost": 0.0,
            "max_drawdown": 0.0,
            "annualized_return": 0.0,
            "sharpe_ratio": 0.0,
            "trade_count": 0,
            "signal_success_rate": 0.0,
            "average_exposure": 0.0,
            "sample_count": 0,
        }

    cash = 1.0
    units = 0.0
    previous_equity = 1.0
    equity_curve = [previous_equity]
    daily_returns: list[float] = []
    exposures: list[float] = []
    total_cost = 0.0
    trade_count = 0
    directional_hits = 0
    directional_samples = 0

    for execution_index in range(warmup_bars, len(bars)):
        decision_bars = bars[:execution_index]
        signal = analyze_instrument(instrument, decision_bars, risk_profile)
        execution_bar = bars[execution_index]
        open_price = float(execution_bar.open)
        close_price = float(execution_bar.close)
        if open_price <= 0 or close_price <= 0:
            continue

        opening_equity = cash + units * open_price
        target_weight = _target_weight(signal.status, risk_profile)
        current_value = units * open_price
        current_weight = current_value / opening_equity if opening_equity > 0 else 0.0
        target_value = opening_equity * target_weight
        delta = target_value - current_value
        should_rebalance = (
            (target_weight == 0.0 and current_weight > 0.0)
            or (current_weight == 0.0 and target_weight > 0.0)
            or abs(target_weight - current_weight) >= rebalance_threshold
        )
        if should_rebalance and abs(delta) > 1e-10:
            side_fee = buy_fee_rate if delta > 0 else sell_fee_rate
            cost = abs(delta) * (side_fee + slippage_rate + turnover_cost_rate)
            total_cost += cost
            cash -= delta + cost
            units += delta / open_price
            trade_count += 1

        closing_equity = cash + units * close_price
        daily_return = closing_equity / previous_equity - 1 if previous_equity else 0.0
        daily_returns.append(daily_return)
        equity_curve.append(closing_equity)
        exposures.append(target_weight)
        previous_equity = closing_equity

        intraday_return = close_price / open_price - 1
        if signal.status in {"偏强", "偏弱"}:
            directional_samples += 1
            expected_positive = signal.status == "偏强"
            directional_hits += int((intraday_return > 0) == expected_positive)

    if units and equity_curve:
        liquidation_value = units * float(bars[-1].close)
        liquidation_cost = liquidation_value * (
            sell_fee_rate + slippage_rate + turnover_cost_rate
        )
        total_cost += liquidation_cost
        cash += liquidation_value - liquidation_cost
        units = 0.0
        equity_curve[-1] = cash
        if daily_returns:
            prior_equity = equity_curve[-2]
            daily_returns[-1] = cash / prior_equity - 1 if prior_equity else 0.0
        trade_count += 1

    total_return = equity_curve[-1] - 1
    years = max(len(daily_returns) / 252, 1 / 252)
    annualized_return = (max(equity_curve[-1], 0.0) ** (1 / years) - 1) if equity_curve[-1] > 0 else -1.0
    volatility = pstdev(daily_returns) if len(daily_returns) > 1 else 0.0
    sharpe_ratio = 0.0 if volatility == 0 else fmean(daily_returns) / volatility * math.sqrt(252)
    return {
        "return": total_return,
        "cost": total_cost,
        "max_drawdown": max_drawdown(equity_curve),
        "annualized_return": annualized_return,
        "sharpe_ratio": sharpe_ratio,
        "trade_count": trade_count,
        "signal_success_rate": (
            directional_hits / directional_samples if directional_samples else 0.0
        ),
        "average_exposure": fmean(exposures) if exposures else 0.0,
        "sample_count": len(daily_returns),
    }


def _target_weight(status: str, risk_profile: str) -> float:
    weights = {
        "conservative": {"偏强": 0.60, "观察": 0.15, "偏弱": 0.0},
        "balanced": {"偏强": 0.80, "观察": 0.25, "偏弱": 0.0},
        "aggressive": {"偏强": 1.00, "观察": 0.40, "偏弱": 0.0},
    }
    profile = weights.get(risk_profile, weights["balanced"])
    return profile.get(status, 0.0)


def _period_return(bars: Sequence[Bar] | None) -> float | None:
    if not bars or len(bars) < 2:
        return None
    first = float(bars[0].close)
    if first == 0:
        return None
    return float(bars[-1].close) / first - 1


def _benchmark_return(
    bars: Sequence[Bar] | None,
    warmup_bars: int = 60,
) -> float | None:
    if not bars or len(bars) <= warmup_bars:
        return _period_return(bars)
    start = float(bars[warmup_bars].open)
    if start == 0:
        return None
    return float(bars[-1].close) / start - 1

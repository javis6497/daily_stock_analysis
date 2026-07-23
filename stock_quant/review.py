from __future__ import annotations

from collections.abc import Mapping, Sequence

from .backtest import run_backtest
from .indicators import max_drawdown
from .models import Bar, BacktestSummary, Instrument, MonthlyHoldingReview
from .strategy import analyze_instrument


def build_backtest_summary(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    risk_profile: str = "balanced",
    buy_fee_rate: float = 0.001,
    sell_fee_rate: float = 0.005,
    slippage_rate: float = 0.001,
    turnover_cost_rate: float = 0.001,
    benchmark_bars: Sequence[Bar] | None = None,
) -> BacktestSummary:
    returns: list[float] = []
    drawdowns: list[float] = []
    signal_success_rates: list[float] = []
    strong_count = 0
    weak_count = 0
    net_returns: list[float] = []
    sharpe_ratios: list[float] = []
    costs: list[float] = []
    total_trade_count = 0

    for instrument, bars in bars_by_instrument.items():
        if len(bars) < 2:
            continue
        closes = [float(bar.close) for bar in bars]
        period_return = closes[-1] / closes[0] - 1 if closes[0] else 0.0
        signal = analyze_instrument(instrument, bars, risk_profile)
        result = run_backtest(
            instrument,
            bars,
            risk_profile,
            benchmark_bars=benchmark_bars,
            buy_fee_rate=buy_fee_rate,
            sell_fee_rate=sell_fee_rate,
            slippage_rate=slippage_rate,
            turnover_cost_rate=turnover_cost_rate,
        )
        returns.append(period_return)
        net_returns.append(float(result["net_return_pct"]) / 100)
        drawdowns.append(float(result["max_drawdown_pct"]) / 100)
        sharpe_ratios.append(float(result["sharpe_ratio"]))
        costs.append(float(result["estimated_cost_pct"]) / 100)
        total_trade_count += int(result["trade_count"])
        if signal.status == "偏强":
            strong_count += 1
        elif signal.status == "偏弱":
            weak_count += 1
        if int(result["sample_count"]) > 0:
            signal_success_rates.append(float(result["signal_success_rate_pct"]) / 100)

    count = len(returns)
    average_return = sum(returns) / count if count else 0.0
    average_net_return = sum(net_returns) / count if count else 0.0
    worst_drawdown = max(drawdowns) if drawdowns else 0.0
    success_rate = (
        sum(signal_success_rates) / len(signal_success_rates)
        if signal_success_rates
        else 0.0
    )
    benchmark_return = _period_return(benchmark_bars)
    average_excess_return = None if benchmark_return is None else average_net_return - benchmark_return
    estimated_cost_rate = sum(costs) / len(costs) if costs else 0.0
    average_sharpe_ratio = sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0.0
    summary = (
        f"{count} 个标的逐日样本外回放；当前偏强 {strong_count} 个、偏弱 {weak_count} 个；"
        f"信号滞后 1 根 K 线执行，已计入实际换手产生的估算成本。"
    )
    return BacktestSummary(
        instrument_count=count,
        average_period_return=average_return,
        max_drawdown=worst_drawdown,
        signal_success_rate=success_rate,
        summary=summary,
        average_net_return=average_net_return,
        benchmark_return=benchmark_return,
        average_excess_return=average_excess_return,
        estimated_cost_rate=estimated_cost_rate,
        average_sharpe_ratio=average_sharpe_ratio,
        total_trade_count=total_trade_count,
        decision_lag_bars=1,
        lookahead_safe=True,
    )


def build_monthly_reviews(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    risk_profile: str = "balanced",
) -> list[MonthlyHoldingReview]:
    reviews: list[MonthlyHoldingReview] = []
    for instrument, bars in bars_by_instrument.items():
        if not bars:
            continue
        closes = [float(bar.close) for bar in bars]
        signal = analyze_instrument(instrument, bars, risk_profile)
        reviews.append(
            MonthlyHoldingReview(
                instrument=instrument,
                signal=signal,
                monthly_change=_rolling_change(closes, 30),
                monthly_drawdown=max_drawdown(closes[-30:]) if len(closes) >= 2 else None,
            )
        )
    return reviews


def _rolling_change(closes: Sequence[float], days: int) -> float | None:
    if len(closes) < 2:
        return None
    start_index = -days - 1
    start = closes[start_index] if len(closes) > days else closes[0]
    if start == 0:
        return None
    return closes[-1] / start - 1


def _period_return(bars: Sequence[Bar] | None) -> float | None:
    if not bars or len(bars) < 2:
        return None
    start = float(bars[0].close)
    if start == 0:
        return None
    return float(bars[-1].close) / start - 1

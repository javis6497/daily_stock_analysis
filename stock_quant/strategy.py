from __future__ import annotations

from collections.abc import Sequence

from .indicators import atr, macd, max_drawdown, rsi, sma
from .models import Bar, Instrument, PriceRange, Signal


def analyze_instrument(
    instrument: Instrument,
    bars: Sequence[Bar],
    risk_profile: str = "balanced",
) -> Signal:
    if not bars:
        raise ValueError(f"{instrument.symbol} has no bars")

    closes = [float(bar.close) for bar in bars]
    latest_close = closes[-1]
    ma20 = sma(closes, 20)[-1]
    ma60 = sma(closes, 60)[-1]
    rsi_value = rsi(closes, 14)[-1]
    _, _, histogram = macd(closes)
    macd_hist = histogram[-1]
    atr_value = atr(bars, 14)[-1] or max(latest_close * 0.02, 0.01)
    recent = bars[-20:] if len(bars) >= 20 else bars
    recent_low = min(float(bar.low) for bar in recent)
    recent_high = max(float(bar.high) for bar in recent)
    drawdown = max_drawdown(closes[-60:])

    if ma20 is None or ma60 is None or rsi_value is None:
        return Signal(
            instrument=instrument,
            status="观察",
            action="数据不足",
            last_close=round(latest_close, 4),
            buy_zone=_range(latest_close - atr_value, latest_close),
            stop_loss=round(max(0.0, latest_close - 2 * atr_value), 4),
            take_profit=round(latest_close + 2 * atr_value, 4),
            confidence=0.2,
            reasons=("历史数据不足，暂不形成方向判断",),
            risks=("样本不足，信号稳定性较低",),
            ma20=ma20,
            ma60=ma60,
            rsi=rsi_value,
            macd_histogram=macd_hist,
            atr=round(atr_value, 4),
        )

    trend_up = latest_close > ma20 > ma60
    trend_down = latest_close < ma20 < ma60
    momentum_ok = (macd_hist or 0.0) >= -0.02 and rsi_value >= 50
    overheated = rsi_value >= 78

    reasons: list[str] = []
    risks: list[str] = []

    if trend_up and momentum_ok:
        status = "偏强"
        action = "回踩观察"
        confidence = 0.78
        buy_zone = _range(latest_close - 0.8 * atr_value, latest_close - 0.2 * atr_value)
        stop_loss = min(recent_low, latest_close - 2.0 * atr_value)
        take_profit = max(recent_high, latest_close + 2.2 * atr_value)
        reasons.append("趋势向上：收盘价高于 MA20，且 MA20 高于 MA60")
        reasons.append("动量确认：RSI 与 MACD 未显示明显转弱")
        if drawdown > 0.08:
            risks.append("近 60 日回撤偏大，仓位不宜激进")
        if overheated:
            risks.append("RSI 偏高，短线追高风险上升")
    elif trend_down or drawdown > 0.14:
        status = "偏弱"
        action = "降低仓位"
        confidence = 0.72
        buy_zone = _range(min(recent_low, latest_close - atr_value), latest_close)
        stop_loss = min(latest_close, recent_low)
        take_profit = min(ma20, latest_close + 1.2 * atr_value)
        reasons.append("趋势破坏：价格位于中期均线下方或均线空头排列")
        risks.append("下行趋势中反弹失败概率较高")
    else:
        status = "观察"
        action = "等待确认"
        confidence = 0.52
        buy_zone = _range(latest_close - atr_value, latest_close + 0.2 * atr_value)
        stop_loss = min(recent_low, latest_close - 1.8 * atr_value)
        take_profit = max(recent_high, latest_close + 1.8 * atr_value)
        reasons.append("趋势尚未形成一致方向，等待量价或均线确认")
        if overheated:
            risks.append("RSI 偏高，短线追高风险上升")

    if not risks:
        risks.append("外部事件、流动性和市场风格切换可能导致信号失效")

    return Signal(
        instrument=instrument,
        status=status,
        action=action,
        last_close=round(latest_close, 4),
        buy_zone=buy_zone,
        stop_loss=round(max(0.0, stop_loss), 4),
        take_profit=round(max(take_profit, latest_close), 4),
        confidence=confidence,
        reasons=tuple(reasons),
        risks=tuple(risks),
        ma20=round(ma20, 4),
        ma60=round(ma60, 4),
        rsi=round(rsi_value, 4),
        macd_histogram=round(macd_hist or 0.0, 6),
        atr=round(atr_value, 4),
    )


def _range(lower: float, upper: float) -> PriceRange:
    lower, upper = sorted((float(lower), float(upper)))
    return PriceRange(lower=round(lower, 4), upper=round(upper, 4))

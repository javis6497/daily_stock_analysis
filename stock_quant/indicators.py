from __future__ import annotations

from collections.abc import Sequence

from .models import Bar


def sma(values: Sequence[float], window: int) -> list[float | None]:
    _require_window(window)
    result: list[float | None] = []
    total = 0.0
    for idx, value in enumerate(values):
        total += float(value)
        if idx >= window:
            total -= float(values[idx - window])
        if idx < window - 1:
            result.append(None)
        else:
            result.append(round(total / window, 6))
    return result


def ema(values: Sequence[float], span: int) -> list[float | None]:
    _require_window(span)
    if not values:
        return []
    alpha = 2 / (span + 1)
    result: list[float | None] = [float(values[0])]
    current = float(values[0])
    for value in values[1:]:
        current = alpha * float(value) + (1 - alpha) * current
        result.append(round(current, 6))
    return result


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    _require_window(period)
    if len(values) < 2:
        return [None for _ in values]

    gains: list[float] = []
    losses: list[float] = []
    for prev, current in zip(values, values[1:]):
        change = float(current) - float(prev)
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    result: list[float | None] = [None for _ in values]
    if len(gains) < period:
        return result

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = _rsi_value(avg_gain, avg_loss)

    for idx in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[idx]) / period
        avg_loss = (avg_loss * (period - 1) + losses[idx]) / period
        result[idx + 1] = _rsi_value(avg_gain, avg_loss)

    return result


def macd(
    values: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    if fast >= slow:
        raise ValueError("fast span must be less than slow span")
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd_line = [
        round(fast_value - slow_value, 6)
        for fast_value, slow_value in zip(fast_ema, slow_ema)
        if fast_value is not None and slow_value is not None
    ]
    signal_line = ema(macd_line, signal)
    histogram = [
        round(line - sig, 6) if sig is not None else None
        for line, sig in zip(macd_line, signal_line)
    ]
    return macd_line, signal_line, histogram


def atr(bars: Sequence[Bar], period: int = 14) -> list[float | None]:
    _require_window(period)
    if not bars:
        return []

    true_ranges: list[float] = []
    previous_close: float | None = None
    for bar in bars:
        high_low = float(bar.high) - float(bar.low)
        if previous_close is None:
            true_range = high_low
        else:
            true_range = max(
                high_low,
                abs(float(bar.high) - previous_close),
                abs(float(bar.low) - previous_close),
            )
        true_ranges.append(true_range)
        previous_close = float(bar.close)

    result: list[float | None] = [None for _ in bars]
    if len(true_ranges) < period:
        return result

    current_atr = sum(true_ranges[:period]) / period
    result[period - 1] = round(current_atr, 6)
    for idx in range(period, len(true_ranges)):
        current_atr = (current_atr * (period - 1) + true_ranges[idx]) / period
        result[idx] = round(current_atr, 6)
    return result


def max_drawdown(values: Sequence[float]) -> float:
    peak = None
    worst = 0.0
    for value in values:
        value = float(value)
        peak = value if peak is None else max(peak, value)
        if peak:
            worst = min(worst, (value - peak) / peak)
    return abs(worst)


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 6)


def _require_window(window: int) -> None:
    if window <= 0:
        raise ValueError("window must be positive")

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .data import MarketDataProvider, fetch_many
from .indicators import max_drawdown, sma
from .models import Bar, Instrument, MarketEnvironment, MarketIndexSignal


MARKET_INDEXES = (
    Instrument("sh000001", "上证指数", "cn", "index", tags=("宽基", "市场环境")),
    Instrument("sh000300", "沪深300", "cn", "index", tags=("宽基", "市场环境")),
    Instrument("sz399006", "创业板指", "cn", "index", tags=("成长", "市场环境")),
    Instrument("sh000905", "中证500", "cn", "index", tags=("中盘", "市场环境")),
)


def build_market_environment(
    provider: MarketDataProvider,
    lookback_days: int = 180,
) -> MarketEnvironment | None:
    bars_by_index = fetch_many(provider, MARKET_INDEXES, lookback_days, strict=False)
    if not bars_by_index:
        return None
    return analyze_market_environment(bars_by_index)


def analyze_market_environment(
    bars_by_index: Mapping[Instrument, Sequence[Bar]],
) -> MarketEnvironment:
    index_signals = tuple(
        signal
        for instrument, bars in bars_by_index.items()
        if (signal := _analyze_index(instrument, bars)) is not None
    )
    if not index_signals:
        return MarketEnvironment(
            status="未知",
            risk_level="未知",
            position_bias="缺少宽基指数行情，先按既有持仓风险位执行。",
            summary="暂无可用市场环境数据。",
        )

    strong = sum(1 for signal in index_signals if signal.status == "偏强")
    weak = sum(1 for signal in index_signals if signal.status == "偏弱")
    total = len(index_signals)
    if strong >= max(2, total - 1):
        status = "进攻"
        risk_level = "偏低"
        position_bias = "可维持均衡偏进攻，但新增仓位仍以回踩确认和分批为主。"
    elif weak >= 2:
        status = "防守"
        risk_level = "偏高"
        position_bias = "控制仓位，优先保护本金，候选标的只做观察不追高。"
    else:
        status = "中性"
        risk_level = "中等"
        position_bias = "维持均衡仓位，等待指数方向和成交额进一步确认。"

    summary = f"{total} 个宽基指数中 {strong} 个偏强、{weak} 个偏弱。"
    return MarketEnvironment(
        status=status,
        risk_level=risk_level,
        position_bias=position_bias,
        summary=summary,
        index_signals=index_signals,
    )


def _analyze_index(instrument: Instrument, bars: Sequence[Bar]) -> MarketIndexSignal | None:
    if not bars:
        return None
    closes = [float(bar.close) for bar in bars]
    latest_close = closes[-1]
    ma20 = sma(closes, 20)[-1]
    ma60 = sma(closes, 60)[-1]
    pct20 = None
    if len(closes) >= 21 and closes[-21] != 0:
        pct20 = closes[-1] / closes[-21] - 1
    drawdown60 = max_drawdown(closes[-60:])

    if ma20 is not None and ma60 is not None and latest_close > ma20 > ma60:
        status = "偏强"
    elif ma20 is not None and ma60 is not None and latest_close < ma20 < ma60:
        status = "偏弱"
    elif drawdown60 > 0.10:
        status = "偏弱"
    else:
        status = "震荡"

    return MarketIndexSignal(
        instrument=instrument,
        status=status,
        last_close=round(latest_close, 4),
        ma20=round(ma20, 4) if ma20 is not None else None,
        ma60=round(ma60, 4) if ma60 is not None else None,
        pct20=pct20,
        drawdown60=drawdown60,
    )

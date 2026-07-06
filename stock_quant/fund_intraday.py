from __future__ import annotations

from collections.abc import Mapping, Sequence

from .models import Bar, FundIntradayEstimate, Instrument, MarketEnvironment, Signal


def build_proxy_instruments(signals: Sequence[Signal]) -> list[Instrument]:
    proxies: list[Instrument] = []
    seen: set[str] = set()
    for signal in signals:
        if signal.instrument.asset_type.lower() not in {"fund", "etf"}:
            continue
        proxy = signal.instrument.proxy_instrument()
        if proxy is None or proxy.symbol in seen:
            continue
        proxies.append(proxy)
        seen.add(proxy.symbol)
    return proxies


def build_fund_intraday_estimates(
    signals: Sequence[Signal],
    proxy_bars: Mapping[Instrument, Sequence[Bar]],
    market_environment: MarketEnvironment | None,
) -> dict[str, FundIntradayEstimate]:
    bars_by_symbol = {instrument.symbol: list(bars) for instrument, bars in proxy_bars.items()}
    estimates: dict[str, FundIntradayEstimate] = {}
    for signal in signals:
        instrument = signal.instrument
        if instrument.asset_type.lower() not in {"fund", "etf"}:
            continue
        proxy = instrument.proxy_instrument()
        if proxy is not None and proxy.symbol in bars_by_symbol:
            pct = _latest_bar_pct(bars_by_symbol[proxy.symbol])
            estimates[instrument.symbol] = FundIntradayEstimate(
                instrument=instrument,
                proxy_symbol=proxy.symbol,
                proxy_name=proxy.name,
                estimated_pct=pct,
                note="基于代理标的当日可见涨跌估算，场外基金最终净值以晚间披露为准。",
            )
            continue

        estimates[instrument.symbol] = _fallback_estimate(instrument, market_environment)
    return estimates


def _latest_bar_pct(bars: Sequence[Bar]) -> float | None:
    if not bars:
        return None
    latest = bars[-1]
    if latest.open == 0:
        return None
    return round(float(latest.close) / float(latest.open) - 1, 4)


def _fallback_estimate(
    instrument: Instrument,
    market_environment: MarketEnvironment | None,
) -> FundIntradayEstimate:
    if market_environment is None or market_environment.status == "未知":
        return FundIntradayEstimate(
            instrument=instrument,
            proxy_symbol=None,
            proxy_name=None,
            estimated_pct=None,
            note="未配置代理标的，且暂无市场环境估算。",
        )
    pct = {"进攻": 0.005, "中性": 0.0, "防守": -0.005}.get(market_environment.status, 0.0)
    return FundIntradayEstimate(
        instrument=instrument,
        proxy_symbol=None,
        proxy_name=None,
        estimated_pct=pct,
        note="未配置代理标的，按市场环境给出粗略估算。",
    )

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, timedelta
from typing import Protocol

from .models import Bar, Instrument


class MarketDataProvider(Protocol):
    def fetch_bars(self, instrument: Instrument, lookback_days: int = 180) -> list[Bar]:
        ...


class SampleDataProvider:
    def fetch_bars(self, instrument: Instrument, lookback_days: int = 180) -> list[Bar]:
        direction = "down" if instrument.symbol.endswith("2") else "up"
        return _make_sample_bars(direction, max(90, lookback_days))


class AkShareDataProvider:
    def fetch_bars(self, instrument: Instrument, lookback_days: int = 180) -> list[Bar]:
        try:
            import akshare as ak
        except ModuleNotFoundError as exc:
            raise RuntimeError("akshare is not installed; install requirements or use provider=sample") from exc

        start_date = (date.today() - timedelta(days=lookback_days * 2)).strftime("%Y%m%d")
        asset_type = instrument.asset_type.lower()
        if asset_type == "fund":
            frame = ak.fund_open_fund_info_em(symbol=instrument.symbol, indicator="单位净值走势")
        elif asset_type == "etf":
            frame = ak.fund_etf_hist_em(symbol=instrument.symbol, period="daily", start_date=start_date, adjust="qfq")
        else:
            frame = ak.stock_zh_a_hist(symbol=instrument.symbol, period="daily", start_date=start_date, adjust="qfq")

        bars = _frame_to_bars(frame)
        if not bars:
            raise RuntimeError(f"no bars returned for {instrument.symbol}")
        return bars[-lookback_days:]


def create_provider(name: str) -> MarketDataProvider:
    provider = name.lower()
    if provider == "sample":
        return SampleDataProvider()
    if provider == "akshare":
        return AkShareDataProvider()
    raise ValueError(f"unsupported data provider: {name}")


def fetch_many(
    provider: MarketDataProvider,
    instruments: Sequence[Instrument],
    lookback_days: int,
    strict: bool = True,
) -> dict[Instrument, list[Bar]]:
    result: dict[Instrument, list[Bar]] = {}
    for instrument in instruments:
        try:
            result[instrument] = provider.fetch_bars(instrument, lookback_days)
        except Exception:
            if strict:
                raise
    return result


def resolve_instrument_names(provider_name: str, instruments: Sequence[Instrument]) -> list[Instrument]:
    if provider_name.lower() != "akshare":
        return list(instruments)
    try:
        import akshare as ak
    except ModuleNotFoundError:
        return list(instruments)

    fund_names = _load_fund_names(ak)
    resolved: list[Instrument] = []
    for instrument in instruments:
        name = fund_names.get(instrument.symbol)
        if name and _is_placeholder_name(instrument):
            resolved.append(replace(instrument, name=name))
        else:
            resolved.append(instrument)
    return resolved


def _make_sample_bars(direction: str, count: int) -> list[Bar]:
    bars: list[Bar] = []
    start = date(2026, 1, 1)
    price = 10.0 if direction == "up" else 30.0
    step = 0.18 if direction == "up" else -0.16
    for idx in range(count):
        price = max(2.0, price + step)
        bars.append(
            Bar(
                date=start + timedelta(days=idx),
                open=round(price - 0.05, 4),
                high=round(price + 0.35, 4),
                low=round(price - 0.35, 4),
                close=round(price, 4),
                volume=1_000_000 + idx * 10_000,
            )
        )
    return bars


def _frame_to_bars(frame) -> list[Bar]:
    bars: list[Bar] = []
    for _, row in frame.iterrows():
        day = row.get("日期") or row.get("净值日期") or row.get("date")
        close = row.get("收盘") or row.get("单位净值") or row.get("close")
        if day is None or close is None:
            continue
        open_price = row.get("开盘", close)
        high = row.get("最高", max(float(open_price), float(close)))
        low = row.get("最低", min(float(open_price), float(close)))
        volume = row.get("成交量", 0.0)
        bars.append(
            Bar(
                date=date.fromisoformat(str(day).replace("/", "-")),
                open=float(open_price),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(volume),
            )
        )
    return bars


def _load_fund_names(ak) -> dict[str, str]:
    try:
        frame = ak.fund_name_em()
    except Exception:
        return {}

    names: dict[str, str] = {}
    for _, row in frame.iterrows():
        symbol = row.get("基金代码") or row.get("代码") or row.get("symbol")
        name = row.get("基金简称") or row.get("基金名称") or row.get("name")
        if symbol and name:
            names[str(symbol).zfill(6)] = str(name).strip()
    return names


def _is_placeholder_name(instrument: Instrument) -> bool:
    name = instrument.name.strip()
    symbol = instrument.symbol
    return name in {symbol, f"基金{symbol}", f"股票{symbol}", f"ETF{symbol}"}

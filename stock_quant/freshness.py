from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from .models import Bar, DataFreshnessItem, DataFreshnessReport, Instrument


def build_data_freshness(
    report_date: date,
    expected_instruments: Sequence[Instrument],
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    stale_after_days: int = 3,
) -> DataFreshnessReport:
    items: list[DataFreshnessItem] = []
    stale_symbols: list[str] = []
    failed_symbols: list[str] = []
    latest_dates: list[date] = []

    for instrument in expected_instruments:
        bars = list(bars_by_instrument.get(instrument, []))
        if not bars:
            failed_symbols.append(instrument.symbol)
            items.append(DataFreshnessItem(instrument, None, None, "获取失败"))
            continue
        latest_date = bars[-1].date
        age_days = max(0, (report_date - latest_date).days)
        latest_dates.append(latest_date)
        if age_days > stale_after_days:
            status = "滞后"
            stale_symbols.append(instrument.symbol)
        elif instrument.asset_type.lower() == "fund" and age_days >= 1:
            status = "基金净值可能滞后"
        else:
            status = "正常"
        items.append(DataFreshnessItem(instrument, latest_date, age_days, status))

    return DataFreshnessReport(
        latest_date=max(latest_dates) if latest_dates else None,
        stale_symbols=tuple(stale_symbols),
        failed_symbols=tuple(failed_symbols),
        items=tuple(items),
    )

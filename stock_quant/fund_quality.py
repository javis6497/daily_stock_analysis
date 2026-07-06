from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .indicators import max_drawdown
from .models import Bar, FundQualityProfile, Instrument


def build_fund_quality_profiles(
    bars_by_instrument: Mapping[Instrument, Sequence[Bar]],
    metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, FundQualityProfile]:
    metadata = metadata or {}
    profiles: dict[str, FundQualityProfile] = {}
    for instrument, bars in bars_by_instrument.items():
        if instrument.asset_type.lower() not in {"fund", "etf"} or not bars:
            continue
        closes = [float(bar.close) for bar in bars]
        meta = metadata.get(instrument.symbol, {})
        ret_1m = _rolling_return(closes, 20)
        ret_3m = _rolling_return(closes, 60)
        ret_6m = _rolling_return(closes, 120)
        ret_12m = _rolling_return(closes, 240)
        drawdown = max_drawdown(closes[-240:])
        score = _quality_score(
            ret_1m=ret_1m,
            ret_3m=ret_3m,
            ret_6m=ret_6m,
            ret_12m=ret_12m,
            drawdown=drawdown,
            fund_size=_optional_float(meta.get("fund_size")),
            manager_tenure_days=_optional_int(meta.get("manager_tenure_days")),
            fee_rate=_optional_float(meta.get("fee_rate")),
            holding_concentration=_optional_float(meta.get("holding_concentration")),
        )
        profiles[instrument.symbol] = FundQualityProfile(
            instrument=instrument,
            quality_score=round(score, 2),
            fund_size=_optional_float(meta.get("fund_size")),
            manager_tenure_days=_optional_int(meta.get("manager_tenure_days")),
            category_rank=_optional_str(meta.get("category_rank")),
            fee_rate=_optional_float(meta.get("fee_rate")),
            holding_concentration=_optional_float(meta.get("holding_concentration")),
            return_1m=ret_1m,
            return_3m=ret_3m,
            return_6m=ret_6m,
            return_12m=ret_12m,
            max_drawdown=drawdown,
        )
    return profiles


def fetch_fund_quality_metadata(provider_name: str, instruments: Sequence[Instrument]) -> dict[str, dict[str, Any]]:
    if provider_name.lower() != "akshare":
        return {}
    try:
        import akshare as ak
    except ModuleNotFoundError:
        return {}

    metadata: dict[str, dict[str, Any]] = {}
    for instrument in instruments:
        if instrument.asset_type.lower() != "fund":
            continue
        info = _fetch_one_fund_metadata(ak, instrument.symbol)
        if info:
            metadata[instrument.symbol] = info
    return metadata


def _fetch_one_fund_metadata(ak, symbol: str) -> dict[str, Any]:
    if not hasattr(ak, "fund_individual_basic_info_xq"):
        return {}
    try:
        frame = ak.fund_individual_basic_info_xq(symbol=symbol)
    except Exception:
        return {}

    info: dict[str, Any] = {}
    for _, row in frame.iterrows():
        key = str(row.get("item") or row.get("项目") or row.get("name") or "").strip()
        value = row.get("value") or row.get("值") or row.get("内容")
        if not key:
            continue
        if "规模" in key:
            info["fund_size"] = _parse_chinese_amount(value)
        elif "经理" in key and "年限" in key:
            info["manager_tenure_days"] = _parse_years_to_days(value)
        elif "费率" in key:
            info["fee_rate"] = _parse_percent(value)
        elif "排名" in key:
            info["category_rank"] = str(value)
    return info


def _rolling_return(closes: Sequence[float], days: int) -> float | None:
    if len(closes) < 2:
        return None
    start = closes[-days - 1] if len(closes) > days else closes[0]
    if start == 0:
        return None
    return closes[-1] / start - 1


def _quality_score(
    ret_1m: float | None,
    ret_3m: float | None,
    ret_6m: float | None,
    ret_12m: float | None,
    drawdown: float | None,
    fund_size: float | None,
    manager_tenure_days: int | None,
    fee_rate: float | None,
    holding_concentration: float | None,
) -> float:
    score = 55.0
    for value, weight in ((ret_1m, 60), (ret_3m, 45), (ret_6m, 30), (ret_12m, 20)):
        if value is not None:
            score += max(-10.0, min(12.0, value * weight))
    if drawdown is not None:
        score -= min(22.0, drawdown * 80)
    if fund_size is not None and fund_size >= 2_000_000_000:
        score += 6.0
    if manager_tenure_days is not None and manager_tenure_days >= 730:
        score += 5.0
    if fee_rate is not None and fee_rate <= 0.015:
        score += 3.0
    if holding_concentration is not None and holding_concentration <= 0.55:
        score += 3.0
    return max(0.0, min(100.0, score))


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace("%", "")) / 100 if "%" in str(value) else float(value)
    except ValueError:
        return None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _parse_percent(value: Any) -> float | None:
    return _optional_float(value)


def _parse_years_to_days(value: Any) -> int | None:
    if value in (None, ""):
        return None
    text = str(value)
    try:
        if "年" in text:
            return int(float(text.split("年", 1)[0]) * 365)
        return int(float(text))
    except ValueError:
        return None


def _parse_chinese_amount(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).replace(",", "").strip()
    multiplier = 1.0
    if "亿" in text:
        multiplier = 100_000_000
        text = text.split("亿", 1)[0]
    elif "万" in text:
        multiplier = 10_000
        text = text.split("万", 1)[0]
    try:
        return float(text) * multiplier
    except ValueError:
        return None

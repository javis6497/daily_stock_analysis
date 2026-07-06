from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .models import Bar, FundamentalQualityProfile, Instrument


def build_fundamental_quality_profiles(
    instruments: Sequence[Instrument] | Mapping[Instrument, Sequence[Bar]],
    metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, FundamentalQualityProfile]:
    metadata = metadata or {}
    profiles: dict[str, FundamentalQualityProfile] = {}
    for instrument in _iter_instruments(instruments):
        if instrument.asset_type.lower() != "stock":
            continue
        meta = metadata.get(instrument.symbol, {})
        if not meta:
            continue
        profile = _build_one_profile(instrument, meta)
        profiles[instrument.symbol] = profile
    return profiles


def fetch_fundamental_quality_metadata(provider_name: str, instruments: Sequence[Instrument]) -> dict[str, dict[str, Any]]:
    if provider_name.lower() != "akshare":
        return {}
    stock_symbols = {instrument.symbol for instrument in instruments if instrument.asset_type.lower() == "stock"}
    if not stock_symbols:
        return {}
    try:
        import akshare as ak
    except ModuleNotFoundError:
        return {}

    metadata = _fetch_spot_metadata(ak, stock_symbols)
    _enrich_financial_metadata(ak, metadata)
    return metadata


def _build_one_profile(instrument: Instrument, meta: Mapping[str, Any]) -> FundamentalQualityProfile:
    roe = _optional_ratio(meta.get("roe"))
    gross_margin = _optional_ratio(meta.get("gross_margin"))
    debt_ratio = _optional_ratio(meta.get("debt_ratio"))
    operating_cashflow_ratio = _optional_float(meta.get("operating_cashflow_ratio"))
    pe = _optional_float(meta.get("pe"))
    pb = _optional_float(meta.get("pb"))
    dividend_yield = _optional_ratio(meta.get("dividend_yield"))
    market_cap = _optional_float(meta.get("market_cap"))
    turnover = _optional_float(meta.get("turnover"))
    score, reasons = _quality_score(
        roe=roe,
        gross_margin=gross_margin,
        debt_ratio=debt_ratio,
        operating_cashflow_ratio=operating_cashflow_ratio,
        pe=pe,
        pb=pb,
        dividend_yield=dividend_yield,
        market_cap=market_cap,
        turnover=turnover,
    )
    return FundamentalQualityProfile(
        instrument=instrument,
        quality_score=round(score, 2),
        roe=roe,
        gross_margin=gross_margin,
        debt_ratio=debt_ratio,
        operating_cashflow_ratio=operating_cashflow_ratio,
        pe=pe,
        pb=pb,
        dividend_yield=dividend_yield,
        market_cap=market_cap,
        turnover=turnover,
        reasons=tuple(reasons),
    )


def _quality_score(
    roe: float | None,
    gross_margin: float | None,
    debt_ratio: float | None,
    operating_cashflow_ratio: float | None,
    pe: float | None,
    pb: float | None,
    dividend_yield: float | None,
    market_cap: float | None,
    turnover: float | None,
) -> tuple[float, list[str]]:
    score = 50.0
    reasons: list[str] = []
    if roe is not None:
        if roe >= 0.20:
            score += 18.0
            reasons.append("ROE 优秀")
        elif roe >= 0.12:
            score += 10.0
            reasons.append("ROE 较好")
        elif roe < 0.05:
            score -= 8.0
            reasons.append("ROE 偏低")
    if gross_margin is not None:
        if gross_margin >= 0.40:
            score += 10.0
            reasons.append("毛利率较高")
        elif gross_margin < 0.15:
            score -= 5.0
            reasons.append("毛利率偏低")
    if debt_ratio is not None:
        if debt_ratio <= 0.40:
            score += 10.0
            reasons.append("负债率较低")
        elif debt_ratio >= 0.75:
            score -= 10.0
            reasons.append("负债率偏高")
    if operating_cashflow_ratio is not None:
        if operating_cashflow_ratio >= 1.0:
            score += 8.0
            reasons.append("经营现金流覆盖较好")
        elif operating_cashflow_ratio < 0:
            score -= 8.0
            reasons.append("经营现金流承压")
    if pe is not None:
        if 5 <= pe <= 35:
            score += 6.0
            reasons.append("估值 PE 处于可观察区间")
        elif pe > 80 or pe <= 0:
            score -= 8.0
            reasons.append("PE 估值风险偏高")
    if pb is not None:
        if 0 < pb <= 10:
            score += 3.0
            reasons.append("PB 未显著失控")
        elif pb > 15:
            score -= 4.0
            reasons.append("PB 偏高")
    if dividend_yield is not None and dividend_yield > 0:
        score += 3.0
        reasons.append("具备分红收益")
    if market_cap is not None and market_cap >= 50_000_000_000:
        score += 3.0
        reasons.append("市值规模较高")
    if turnover is not None and turnover >= 500_000_000:
        score += 2.0
        reasons.append("成交额流动性较好")
    if not reasons:
        reasons.append("基本面字段不足，仅保留技术评分")
    return max(0.0, min(100.0, score)), reasons


def _fetch_spot_metadata(ak, stock_symbols: set[str]) -> dict[str, dict[str, Any]]:
    if not hasattr(ak, "stock_zh_a_spot_em"):
        return {}
    try:
        frame = ak.stock_zh_a_spot_em()
    except Exception:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        symbol = _text(row, "代码", "symbol")
        if symbol not in stock_symbols:
            continue
        result[symbol] = {
            "turnover": _number(row, "成交额", "amount"),
            "market_cap": _number(row, "总市值", "market_cap"),
            "pe": _number(row, "市盈率-动态", "动态市盈率", "pe"),
            "pb": _number(row, "市净率", "pb"),
        }
    return result


def _enrich_financial_metadata(ak, metadata: dict[str, dict[str, Any]]) -> None:
    if not metadata or not hasattr(ak, "stock_financial_abstract_ths"):
        return
    for symbol, meta in metadata.items():
        try:
            frame = ak.stock_financial_abstract_ths(symbol=symbol)
        except Exception:
            continue
        if frame.empty:
            continue
        latest = frame.iloc[0]
        meta.setdefault("roe", _first_number(latest, ("净资产收益率", "ROE")))
        meta.setdefault("gross_margin", _first_number(latest, ("销售毛利率", "毛利率")))
        meta.setdefault("debt_ratio", _first_number(latest, ("资产负债率",)))
        meta.setdefault("operating_cashflow_ratio", _first_number(latest, ("经营现金流量净额/净利润", "经营现金流净利润比")))


def _iter_instruments(
    instruments: Sequence[Instrument] | Mapping[Instrument, Sequence[Bar]],
) -> Sequence[Instrument]:
    if isinstance(instruments, Mapping):
        return list(instruments.keys())
    return instruments


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def _optional_ratio(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        number = float(text.replace(",", "").replace("%", ""))
    except ValueError:
        return None
    if "%" in text or abs(number) > 1:
        return number / 100
    return number


def _text(row, *keys: str) -> str:
    for key in keys:
        value = row.get(key) if hasattr(row, "get") else None
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _number(row, *keys: str) -> float | None:
    text = _text(row, *keys)
    if not text:
        return None
    return _optional_float(text)


def _first_number(row, keys: Sequence[str]) -> float | None:
    for key in keys:
        value = row.get(key) if hasattr(row, "get") else None
        ratio = _optional_ratio(value)
        if ratio is not None:
            return ratio
    return None

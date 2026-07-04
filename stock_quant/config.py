from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .models import Instrument


@dataclass(frozen=True)
class DataConfig:
    provider: str = "akshare"
    lookback_days: int = 180


@dataclass(frozen=True)
class ReportConfig:
    top_n: int = 5
    risk_profile: str = "balanced"
    skip_non_trading_day: bool = True


@dataclass(frozen=True)
class NotifyConfig:
    channel: str = "dingtalk"


@dataclass(frozen=True)
class NewsConfig:
    provider: str = "akshare"
    keywords: list[str] = field(default_factory=list)
    max_items: int = 8


@dataclass(frozen=True)
class RecommendationConfig:
    enabled: bool = True
    include_default_universe: bool = True
    include_dynamic_a_shares: bool = True
    include_dynamic_etfs: bool = True
    exclude_watchlist: bool = True
    dynamic_a_share_limit: int = 20
    dynamic_etf_limit: int = 20
    min_turnover: float = 500_000_000
    min_etf_turnover: float = 100_000_000
    min_market_cap: float = 50_000_000_000
    min_pe: float = 0.0
    max_pe: float = 80.0
    min_pb: float = 0.0
    max_pb: float = 10.0
    min_pct_change: float = -5.0
    max_pct_change: float = 7.0
    max_candidate_single_day_pct: float = 0.07
    max_candidates_per_group: int = 2


@dataclass(frozen=True)
class AppConfig:
    timezone: str = "Asia/Shanghai"
    data: DataConfig = field(default_factory=DataConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    recommendation: RecommendationConfig = field(default_factory=RecommendationConfig)
    watchlist: list[Instrument] = field(default_factory=list)
    candidate_pool: list[Instrument] = field(default_factory=list)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    watchlist = [_parse_instrument(item) for item in raw.get("watchlist", [])]
    if not watchlist:
        raise ValueError("watchlist must contain at least one instrument")

    data_raw = raw.get("data", {}) or {}
    report_raw = raw.get("report", {}) or {}
    notify_raw = raw.get("notify", {}) or {}
    news_raw = raw.get("news", {}) or {}
    recommendation_raw = raw.get("recommendation", {}) or {}

    return AppConfig(
        timezone=str(raw.get("timezone", "Asia/Shanghai")),
        data=DataConfig(
            provider=str(data_raw.get("provider", "akshare")),
            lookback_days=int(data_raw.get("lookback_days", 180)),
        ),
        report=ReportConfig(
            top_n=int(report_raw.get("top_n", 5)),
            risk_profile=str(report_raw.get("risk_profile", "balanced")),
            skip_non_trading_day=bool(report_raw.get("skip_non_trading_day", True)),
        ),
        notify=NotifyConfig(channel=str(notify_raw.get("channel", "dingtalk"))),
        news=NewsConfig(
            provider=str(news_raw.get("provider", "akshare")),
            keywords=list(news_raw.get("keywords", []) or []),
            max_items=int(news_raw.get("max_items", 8)),
        ),
        recommendation=RecommendationConfig(
            enabled=bool(recommendation_raw.get("enabled", True)),
            include_default_universe=bool(recommendation_raw.get("include_default_universe", True)),
            include_dynamic_a_shares=bool(recommendation_raw.get("include_dynamic_a_shares", True)),
            include_dynamic_etfs=bool(recommendation_raw.get("include_dynamic_etfs", True)),
            exclude_watchlist=bool(recommendation_raw.get("exclude_watchlist", True)),
            dynamic_a_share_limit=int(recommendation_raw.get("dynamic_a_share_limit", 20)),
            dynamic_etf_limit=int(recommendation_raw.get("dynamic_etf_limit", 20)),
            min_turnover=float(recommendation_raw.get("min_turnover", 500_000_000)),
            min_etf_turnover=float(recommendation_raw.get("min_etf_turnover", 100_000_000)),
            min_market_cap=float(recommendation_raw.get("min_market_cap", 50_000_000_000)),
            min_pe=float(recommendation_raw.get("min_pe", 0)),
            max_pe=float(recommendation_raw.get("max_pe", 80)),
            min_pb=float(recommendation_raw.get("min_pb", 0)),
            max_pb=float(recommendation_raw.get("max_pb", 10)),
            min_pct_change=float(recommendation_raw.get("min_pct_change", -5)),
            max_pct_change=float(recommendation_raw.get("max_pct_change", 7)),
            max_candidate_single_day_pct=float(recommendation_raw.get("max_candidate_single_day_pct", 0.07)),
            max_candidates_per_group=int(recommendation_raw.get("max_candidates_per_group", 2)),
        ),
        watchlist=watchlist,
        candidate_pool=[_parse_instrument(item) for item in raw.get("candidate_pool", [])],
    )


def _parse_instrument(raw: dict[str, Any]) -> Instrument:
    if not isinstance(raw, dict):
        raise ValueError("instrument entries must be mappings")

    required = ("symbol", "name", "market", "asset_type")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"instrument missing required fields: {', '.join(missing)}")

    return Instrument(
        symbol=str(raw["symbol"]),
        name=str(raw["name"]),
        market=str(raw["market"]),
        asset_type=str(raw["asset_type"]),
        tags=tuple(raw.get("tags", []) or []),
        cost_price=_optional_float(raw.get("cost_price")),
        holding_amount=_optional_float(raw.get("holding_amount")),
        target_weight=_optional_float(raw.get("target_weight")),
        max_weight=_optional_float(raw.get("max_weight")),
        risk_level=_optional_str(raw.get("risk_level")),
        note=_optional_str(raw.get("note")),
    )


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)

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
class AppConfig:
    timezone: str = "Asia/Shanghai"
    data: DataConfig = field(default_factory=DataConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
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
    )

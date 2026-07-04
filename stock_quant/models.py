from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Bar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    market: str
    asset_type: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    cost_price: float | None = None
    holding_amount: float | None = None
    target_weight: float | None = None
    max_weight: float | None = None
    risk_level: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", str(self.symbol))
        object.__setattr__(self, "market", str(self.market))
        object.__setattr__(self, "asset_type", str(self.asset_type))
        if not isinstance(self.tags, tuple):
            object.__setattr__(self, "tags", tuple(self.tags))
        if self.cost_price is not None:
            object.__setattr__(self, "cost_price", float(self.cost_price))
        if self.holding_amount is not None:
            object.__setattr__(self, "holding_amount", float(self.holding_amount))
        if self.target_weight is not None:
            object.__setattr__(self, "target_weight", float(self.target_weight))
        if self.max_weight is not None:
            object.__setattr__(self, "max_weight", float(self.max_weight))
        if self.risk_level is not None:
            object.__setattr__(self, "risk_level", str(self.risk_level))
        if self.note is not None:
            object.__setattr__(self, "note", str(self.note))


@dataclass(frozen=True)
class PriceRange:
    lower: float
    upper: float


@dataclass(frozen=True)
class Signal:
    instrument: Instrument
    status: str
    action: str
    last_close: float
    buy_zone: PriceRange
    stop_loss: float
    take_profit: float
    confidence: float
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    ma20: float | None = None
    ma60: float | None = None
    rsi: float | None = None
    macd_histogram: float | None = None
    atr: float | None = None


@dataclass(frozen=True)
class CandidateScore:
    instrument: Instrument
    score: float
    signal: Signal
    reasons: tuple[str, ...]
    group: str = "未分组"


@dataclass(frozen=True)
class WeeklyHoldingReview:
    instrument: Instrument
    signal: Signal
    weekly_change: float | None = None
    weekly_drawdown: float | None = None


@dataclass(frozen=True)
class MarketIndexSignal:
    instrument: Instrument
    status: str
    last_close: float
    ma20: float | None
    ma60: float | None
    pct20: float | None
    drawdown60: float | None


@dataclass(frozen=True)
class MarketEnvironment:
    status: str
    risk_level: str
    position_bias: str
    summary: str
    index_signals: tuple[MarketIndexSignal, ...] = field(default_factory=tuple)
    up_count: int | None = None
    down_count: int | None = None
    total_turnover: float | None = None


@dataclass(frozen=True)
class PortfolioPosition:
    instrument: Instrument
    market_value: float
    principal: float
    pnl_amount: float
    pnl_pct: float
    weight: float
    max_weight_breached: bool = False


@dataclass(frozen=True)
class PortfolioSummary:
    total_principal: float
    total_market_value: float
    total_pnl_amount: float
    total_pnl_pct: float
    positions: tuple[PortfolioPosition, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DataFreshnessItem:
    instrument: Instrument
    latest_date: date | None
    age_days: int | None
    status: str


@dataclass(frozen=True)
class DataFreshnessReport:
    latest_date: date | None
    stale_symbols: tuple[str, ...] = field(default_factory=tuple)
    failed_symbols: tuple[str, ...] = field(default_factory=tuple)
    items: tuple[DataFreshnessItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BacktestSummary:
    instrument_count: int
    average_period_return: float
    max_drawdown: float
    signal_success_rate: float
    summary: str


@dataclass(frozen=True)
class MonthlyHoldingReview:
    instrument: Instrument
    signal: Signal
    monthly_change: float | None = None
    monthly_drawdown: float | None = None

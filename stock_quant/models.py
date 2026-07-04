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


@dataclass(frozen=True)
class WeeklyHoldingReview:
    instrument: Instrument
    signal: Signal
    weekly_change: float | None = None
    weekly_drawdown: float | None = None

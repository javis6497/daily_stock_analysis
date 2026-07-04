from __future__ import annotations

from collections.abc import Sequence

from .models import PortfolioPosition, PortfolioSummary, Signal


def build_portfolio_summary(signals: Sequence[Signal]) -> PortfolioSummary:
    positions: list[PortfolioPosition] = []
    for signal in signals:
        instrument = signal.instrument
        if instrument.holding_amount is None:
            continue
        principal = float(instrument.holding_amount)
        market_value = _market_value(signal)
        pnl_amount = market_value - principal
        pnl_pct = 0.0 if principal == 0 else pnl_amount / principal
        positions.append(
            PortfolioPosition(
                instrument=instrument,
                market_value=market_value,
                principal=principal,
                pnl_amount=pnl_amount,
                pnl_pct=pnl_pct,
                weight=0.0,
            )
        )

    total_principal = sum(position.principal for position in positions)
    total_market_value = sum(position.market_value for position in positions)
    total_pnl_amount = total_market_value - total_principal
    total_pnl_pct = 0.0 if total_principal == 0 else total_pnl_amount / total_principal

    weighted_positions: list[PortfolioPosition] = []
    warnings: list[str] = []
    for position in positions:
        weight = 0.0 if total_market_value == 0 else position.market_value / total_market_value
        max_weight = position.instrument.max_weight
        breached = max_weight is not None and weight > max_weight
        if breached:
            warnings.append(f"{position.instrument.name} 超过最大仓位 {max_weight:.0%}")
        weighted_positions.append(
            PortfolioPosition(
                instrument=position.instrument,
                market_value=position.market_value,
                principal=position.principal,
                pnl_amount=position.pnl_amount,
                pnl_pct=position.pnl_pct,
                weight=weight,
                max_weight_breached=breached,
            )
        )

    return PortfolioSummary(
        total_principal=round(total_principal, 2),
        total_market_value=round(total_market_value, 2),
        total_pnl_amount=round(total_pnl_amount, 2),
        total_pnl_pct=total_pnl_pct,
        positions=tuple(weighted_positions),
        warnings=tuple(warnings),
    )


def _market_value(signal: Signal) -> float:
    instrument = signal.instrument
    principal = float(instrument.holding_amount or 0.0)
    if instrument.cost_price and instrument.cost_price > 0:
        return principal * signal.last_close / instrument.cost_price
    return principal

from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .alerts import Alert
from .models import CandidateScore, MarketEnvironment, PortfolioSummary, Signal


def write_signal_ledger(
    output_dir: str | Path,
    session: str,
    report_date: date,
    signals: list[Signal],
    candidates: list[CandidateScore],
    market_environment: MarketEnvironment | None,
    portfolio_summary: PortfolioSummary | None,
    alerts: list[Alert],
) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    stem = f"{report_date.isoformat()}-{session}"
    json_name = f"{stem}.json"
    signals_csv_name = f"{stem}-signals.csv"
    candidates_csv_name = f"{stem}-candidates.csv"

    payload = {
        "session": session,
        "report_date": report_date.isoformat(),
        "market_environment": _clean(market_environment),
        "portfolio_summary": _clean(portfolio_summary),
        "signals": [_signal_row(signal) for signal in signals],
        "candidates": [_candidate_row(candidate) for candidate in candidates],
        "alerts": [_clean(alert) for alert in alerts],
    }
    (target / json_name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(target / signals_csv_name, payload["signals"])
    _write_csv(target / candidates_csv_name, payload["candidates"])
    return {
        "json": json_name,
        "signals_csv": signals_csv_name,
        "candidates_csv": candidates_csv_name,
    }


def _signal_row(signal: Signal) -> dict[str, Any]:
    instrument = signal.instrument
    pnl_pct = None
    pnl_amount = None
    if instrument.cost_price and instrument.cost_price > 0:
        pnl_pct = signal.last_close / instrument.cost_price - 1
        if instrument.holding_amount is not None:
            pnl_amount = instrument.holding_amount * pnl_pct
    return {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "asset_type": instrument.asset_type,
        "status": signal.status,
        "action": signal.action,
        "confidence": signal.confidence,
        "last_close": signal.last_close,
        "cost_price": instrument.cost_price,
        "holding_amount": instrument.holding_amount,
        "pnl_pct": pnl_pct,
        "pnl_amount": pnl_amount,
        "buy_zone_lower": signal.buy_zone.lower,
        "buy_zone_upper": signal.buy_zone.upper,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
    }


def _candidate_row(candidate: CandidateScore) -> dict[str, Any]:
    profile = candidate.quality_profile
    return {
        "symbol": candidate.instrument.symbol,
        "name": candidate.instrument.name,
        "asset_type": candidate.instrument.asset_type,
        "score": candidate.score,
        "status": candidate.signal.status,
        "group": candidate.group,
        "quality_score": None if profile is None else profile.quality_score,
        "reasons": "；".join(candidate.reasons),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_clean(item) for item in value]
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if is_dataclass(value):
        return _clean(asdict(value))
    return str(value)

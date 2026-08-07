"""Cross-session persistence of the day's recommended candidates.

盘前/盘中会话把当天的自选外候选推荐落盘到一个按日期命名的 JSON，
盘后会话读取它，生成"今日推荐回顾"（推荐后实际走势）。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .models import CandidateScore


def candidate_picks(
    candidates: list[CandidateScore],
    session: str,
    max_picks: int = 3,
) -> list[dict[str, Any]]:
    """Convert ranked candidates into lightweight daily-pick records.

    只保存"今日关注"里展示的头部候选（默认前 3 只），与消息里用户实际看到的推荐一致。
    """
    picks: list[dict[str, Any]] = []
    for candidate in candidates[:max_picks]:
        signal = candidate.signal
        picks.append(
            {
                "session": session,
                "symbol": candidate.instrument.symbol,
                "name": candidate.instrument.name,
                "asset_type": candidate.instrument.asset_type,
                "ref_price": signal.last_close,
                "buy_low": signal.buy_zone.lower,
                "buy_high": signal.buy_zone.upper,
                "risk": signal.stop_loss,
                "score": candidate.score,
            }
        )
    return picks


def save_daily_picks(
    picks_dir: str | Path,
    report_date: date,
    picks: list[dict[str, Any]],
) -> None:
    path = Path(picks_dir) / f"{report_date.isoformat()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"date": report_date.isoformat(), "picks": picks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_daily_picks(
    picks_dir: str | Path,
    report_date: date,
) -> list[dict[str, Any]]:
    path = Path(picks_dir) / f"{report_date.isoformat()}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return list(data.get("picks", []))


def merge_picks(existing: list[dict[str, Any]], new_picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append new session picks to the day's existing picks, keeping both
    盘前 and 盘中 entries so the recap can show intraday evolution."""
    merged = list(existing)
    seen = {(p.get("session"), p.get("symbol")) for p in merged}
    for pick in new_picks:
        key = (pick.get("session"), pick.get("symbol"))
        if key not in seen:
            merged.append(pick)
            seen.add(key)
    return merged

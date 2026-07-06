from __future__ import annotations

from collections.abc import Sequence

from .models import Signal, ThesisReview


def build_thesis_reviews(signals: Sequence[Signal]) -> dict[str, ThesisReview]:
    reviews: dict[str, ThesisReview] = {}
    for signal in signals:
        instrument = signal.instrument
        if not instrument.thesis and not instrument.invalidation and not instrument.thesis_risks:
            continue
        status, note = _review_signal(signal)
        reviews[instrument.symbol] = ThesisReview(
            instrument=instrument,
            status=status,
            note=note,
        )
    return reviews


def _review_signal(signal: Signal) -> tuple[str, str]:
    instrument = signal.instrument
    if signal.stop_loss > 0 and signal.last_close <= signal.stop_loss:
        return "逻辑漂移", _note("跌破风险位", instrument.invalidation)
    if signal.status == "偏弱" or signal.action == "降低仓位":
        return "逻辑漂移", _note("信号转弱，原持仓逻辑需要人工复核", instrument.invalidation)
    if signal.status == "偏强":
        return "有效", "持仓逻辑未触发失效条件，继续按风险位和止盈位跟踪。"
    return "观察", "持仓逻辑未明确失效，但趋势确认不足，等待后续信号。"


def _note(reason: str, invalidation: str | None) -> str:
    if invalidation:
        return f"{reason}；失效条件：{invalidation}"
    return reason

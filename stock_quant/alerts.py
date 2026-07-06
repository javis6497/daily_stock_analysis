from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import CandidateScore, DataFreshnessReport, PortfolioSummary, Signal


@dataclass(frozen=True)
class Alert:
    level: str
    title: str
    message: str


def build_alerts(
    signals: Sequence[Signal],
    candidates: Sequence[CandidateScore],
    freshness_report: DataFreshnessReport | None,
    portfolio_summary: PortfolioSummary | None,
) -> list[Alert]:
    alerts: list[Alert] = []
    for signal in signals:
        if signal.stop_loss > 0 and signal.last_close <= signal.stop_loss:
            alerts.append(
                Alert(
                    level="high",
                    title="跌破风险位",
                    message=f"{signal.instrument.name} ({signal.instrument.symbol}) 最新价 {signal.last_close:.4f} 已低于风险位 {signal.stop_loss:.4f}。",
                )
            )
        elif signal.take_profit > 0 and signal.last_close >= signal.take_profit:
            alerts.append(
                Alert(
                    level="medium",
                    title="触发止盈观察",
                    message=f"{signal.instrument.name} ({signal.instrument.symbol}) 已达到止盈/减仓观察位 {signal.take_profit:.4f}。",
                )
            )

    if portfolio_summary is not None:
        for warning in portfolio_summary.warnings:
            alerts.append(Alert(level="medium", title="仓位超限", message=warning))

    if freshness_report is not None:
        if freshness_report.stale_symbols:
            alerts.append(
                Alert(
                    level="medium",
                    title="数据滞后",
                    message=f"以下标的行情日期滞后：{', '.join(freshness_report.stale_symbols)}。",
                )
            )
        if freshness_report.failed_symbols:
            alerts.append(
                Alert(
                    level="high",
                    title="数据获取失败",
                    message=f"以下标的行情获取失败：{', '.join(freshness_report.failed_symbols)}。",
                )
            )

    for candidate in candidates:
        if candidate.score >= 95:
            alerts.append(
                Alert(
                    level="low",
                    title="高分候选观察",
                    message=f"{candidate.instrument.name} ({candidate.instrument.symbol}) 候选评分 {candidate.score:.2f}，仅作为候选观察。",
                )
            )
    return alerts

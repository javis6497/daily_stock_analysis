from __future__ import annotations

from datetime import date

from .config import AppConfig
from .models import CandidateScore, Signal
from .news import NewsItem


def render_report(
    session: str,
    report_date: date,
    config: AppConfig,
    signals: list[Signal],
    candidates: list[CandidateScore],
    news_items: list[NewsItem],
) -> str:
    title = "盘前量化日报" if session == "premarket" else "盘后量化复盘"
    lines = [
        f"# {title} - {report_date.isoformat()}",
        "",
        f"- 风险档位：{config.report.risk_profile}",
        f"- 推送口径：量化研究信号 + 风险提示 + 人工确认",
        "",
        "## 自选股/基金信号",
    ]

    if signals:
        for signal in signals:
            instrument = signal.instrument
            lines.extend(
                [
                    f"### {instrument.name} ({instrument.symbol})",
                    f"- 状态：{signal.status}；动作：{signal.action}；置信度：{signal.confidence:.0%}",
                    f"- 最新价：{signal.last_close:.4f}；MA20：{_fmt(signal.ma20)}；MA60：{_fmt(signal.ma60)}；RSI：{_fmt(signal.rsi)}",
                    f"- 买入观察区：{signal.buy_zone.lower:.4f} - {signal.buy_zone.upper:.4f}",
                    f"- 风险位：{signal.stop_loss:.4f}；止盈/减仓观察位：{signal.take_profit:.4f}",
                    f"- 依据：{'；'.join(signal.reasons)}",
                    f"- 风险：{'；'.join(signal.risks)}",
                    "",
                ]
            )
    else:
        lines.extend(["- 暂无可用自选标的信号。", ""])

    lines.append("## 潜力候选")
    if candidates:
        for rank, candidate in enumerate(candidates, start=1):
            signal = candidate.signal
            lines.extend(
                [
                    f"{rank}. {candidate.instrument.name} ({candidate.instrument.symbol}) - 综合分 {candidate.score:.2f}",
                    f"   - 状态：{signal.status}；观察区：{signal.buy_zone.lower:.4f} - {signal.buy_zone.upper:.4f}；风险位：{signal.stop_loss:.4f}",
                ]
            )
    else:
        lines.append("- 暂无候选标的。")

    lines.extend(["", "## 相关资讯"])
    if news_items:
        for item in news_items:
            lines.append(f"- [{item.title}]({item.url}) - {item.source} {item.published_at}")
    else:
        lines.append("- 暂无匹配资讯。")

    lines.extend(
        [
            "",
            "## 免责声明",
            "本报告仅为量化研究信号和风险提示，不自动交易，不构成保证收益或个人投顾建议。任何操作需自行判断并控制仓位风险。",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}"

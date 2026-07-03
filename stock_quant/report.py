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
    return "\n\n---\n\n".join(
        [
            render_action_report(session, report_date, config, signals, candidates),
            render_daily_news_report(session, report_date, config, news_items),
        ]
    )


def render_action_report(
    session: str,
    report_date: date,
    config: AppConfig,
    signals: list[Signal],
    candidates: list[CandidateScore],
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
                    _holding_line(signal),
                    f"- 买入观察区：{signal.buy_zone.lower:.4f} - {signal.buy_zone.upper:.4f}",
                    f"- 风险位：{signal.stop_loss:.4f}；止盈/减仓观察位：{signal.take_profit:.4f}",
                    f"- 依据：{'；'.join(signal.reasons)}",
                    f"- 风险：{'；'.join(signal.risks)}",
                    "",
                ]
            )
    else:
        lines.extend(["- 暂无可用自选标的信号。", ""])

    lines.append("## 自选外量化候选（潜力候选）")
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

    lines.extend(
        [
            "",
            "## 免责声明",
            "本报告仅为量化研究信号和风险提示，不自动交易，不构成保证收益或个人投顾建议。任何操作需自行判断并控制仓位风险。",
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def render_daily_news_report(
    session: str,
    report_date: date,
    config: AppConfig,
    news_items: list[NewsItem],
) -> str:
    title = "盘前资讯摘要" if session == "premarket" else "盘后资讯摘要"
    lines = [
        f"# {title} - {report_date.isoformat()}",
        "",
        "- 推送口径：真实资讯聚合 + 自选标的关键词过滤",
        "",
        "## 相关资讯",
    ]
    if news_items:
        for item in news_items:
            title_text = f"[{item.title}]({item.url})" if item.url else item.title
            lines.append(f"- {title_text} - {item.source} {item.published_at}".rstrip())
            if item.summary:
                lines.append(f"  - 摘要：{item.summary}")
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


def render_fund_action_report(
    report_date: date,
    config: AppConfig,
    signals: list[Signal],
) -> str:
    fund_signals = [
        signal
        for signal in signals
        if signal.instrument.asset_type.lower() in {"fund", "etf"}
    ]
    lines = [
        f"# 14:00基金操作提醒 - {report_date.isoformat()}",
        "",
        "- 推送口径：仅自选基金/ETF操作信号，不含股票、不含资讯、不含自选外候选。",
        "- 时间目的：基金通常需在 15:00 前确认申购/赎回，14:00 提前给出量化观察。",
        "- 数据口径：基于当前可用最新净值/行情，场外基金净值可能存在 T 日更新滞后。",
        "",
        "## 自选基金操作信号",
    ]

    if fund_signals:
        for signal in fund_signals:
            instrument = signal.instrument
            lines.extend(
                [
                    f"### {instrument.name} ({instrument.symbol})",
                    f"- 状态：{signal.status}；动作：{signal.action}；置信度：{signal.confidence:.0%}",
                    f"- 最新价/净值：{signal.last_close:.4f}；MA20：{_fmt(signal.ma20)}；MA60：{_fmt(signal.ma60)}；RSI：{_fmt(signal.rsi)}",
                    _holding_line(signal),
                    f"- 买入观察区：{signal.buy_zone.lower:.4f} - {signal.buy_zone.upper:.4f}",
                    f"- 风险位：{signal.stop_loss:.4f}；止盈/减仓观察位：{signal.take_profit:.4f}",
                    f"- 依据：{'；'.join(signal.reasons)}",
                    f"- 风险：{'；'.join(signal.risks)}",
                    "",
                ]
            )
    else:
        lines.extend(["- 当前自选列表中没有基金/ETF信号。", ""])

    lines.extend(
        [
            "## 免责声明",
            "本报告仅为量化研究信号和风险提示，不自动交易，不构成保证收益或个人投顾建议。任何操作需自行判断并控制仓位风险。",
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def render_weekend_news_report(
    report_date: date,
    config: AppConfig,
    news_items: list[NewsItem],
) -> str:
    lines = [
        f"# 周末资讯观察 - {report_date.isoformat()}",
        "",
        "- 推送口径：真实资讯聚合 + 持仓关键词过滤 + 下周关注点",
        "- 周末不生成交易价位或减仓动作，避免用休市行情给出交易结论。",
        "",
        "## 持仓关注",
    ]
    for instrument in config.watchlist:
        lines.append(f"- {instrument.name} ({instrument.symbol})")

    lines.extend(["", "## 相关资讯"])
    if news_items:
        for item in news_items:
            title = f"[{item.title}]({item.url})" if item.url else item.title
            lines.append(f"- {title} - {item.source} {item.published_at}".rstrip())
            if item.summary:
                lines.append(f"  - 摘要：{item.summary}")
    else:
        lines.append("- 暂无匹配资讯；请关注下周一开盘后的市场反馈。")

    lines.extend(
        [
            "",
            "## 下周关注点",
            "- 政策、利率、汇率和海外市场变化对 A 股风险偏好的影响。",
            "- 持仓基金相关行业是否出现持续资金流入或突发风险事件。",
            "- 周一开盘后再结合最新净值、均线和回撤信号判断，不在周末提前下交易结论。",
            "",
            "## 免责声明",
            "本报告仅为资讯聚合和量化研究辅助，不自动交易，不构成保证收益或个人投顾建议。任何操作需自行判断并控制仓位风险。",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def _holding_line(signal: Signal) -> str | None:
    instrument = signal.instrument
    parts: list[str] = []
    if instrument.cost_price is not None:
        parts.append(f"持仓成本：{instrument.cost_price:.4f}")
    if instrument.holding_amount is not None:
        parts.append(f"投入本金：{instrument.holding_amount:.2f}")
    if instrument.cost_price and instrument.cost_price > 0:
        pnl_pct = signal.last_close / instrument.cost_price - 1
        if instrument.holding_amount is not None:
            pnl_amount = instrument.holding_amount * pnl_pct
            parts.append(f"估算盈亏：{pnl_pct:.2%}（{pnl_amount:.2f}）")
        else:
            parts.append(f"估算盈亏：{pnl_pct:.2%}")
    if not parts:
        return None
    return "- " + "；".join(parts)

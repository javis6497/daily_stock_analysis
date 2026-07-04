from __future__ import annotations

from datetime import date

from .config import AppConfig
from .models import CandidateScore, MarketEnvironment, Signal, WeeklyHoldingReview
from .news import NewsItem


def render_report(
    session: str,
    report_date: date,
    config: AppConfig,
    signals: list[Signal],
    candidates: list[CandidateScore],
    news_items: list[NewsItem],
    market_environment: MarketEnvironment | None = None,
) -> str:
    return "\n\n---\n\n".join(
        [
            render_action_report(session, report_date, config, signals, candidates, market_environment),
            render_daily_news_report(session, report_date, config, news_items),
        ]
    )


def render_action_report(
    session: str,
    report_date: date,
    config: AppConfig,
    signals: list[Signal],
    candidates: list[CandidateScore],
    market_environment: MarketEnvironment | None = None,
) -> str:
    title = "盘前量化日报" if session == "premarket" else "盘后量化复盘"
    lines = [
        f"# {title} - {report_date.isoformat()}",
        "",
        f"- 风险档位：{config.report.risk_profile}",
        f"- 推送口径：量化研究信号 + 风险提示 + 人工确认",
        "",
    ]
    lines.extend(_market_environment_lines(market_environment))
    lines.extend(["", "## 自选股/基金信号"])

    if signals:
        for signal in signals:
            instrument = signal.instrument
            lines.extend(
                [
                    f"### {instrument.name} ({instrument.symbol})",
                    f"- 状态：{signal.status}；动作：{signal.action}；置信度：{signal.confidence:.0%}",
                    f"- 最新价：{signal.last_close:.4f}；MA20：{_fmt(signal.ma20)}；MA60：{_fmt(signal.ma60)}；RSI：{_fmt(signal.rsi)}",
                    _holding_line(signal),
                    _position_policy_line(signal),
                    _distance_line(signal),
                    _holding_advice_line(signal),
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
                    f"   - 状态：{signal.status}；分组：{candidate.group}；观察区：{signal.buy_zone.lower:.4f} - {signal.buy_zone.upper:.4f}；风险位：{signal.stop_loss:.4f}",
                    f"   - 筛选理由：{'；'.join(candidate.reasons)}",
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
    market_environment: MarketEnvironment | None = None,
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
    ]
    lines.extend(_market_environment_lines(market_environment))
    lines.extend(["", "## 自选基金操作信号"])

    if fund_signals:
        for signal in fund_signals:
            instrument = signal.instrument
            lines.extend(
                [
                    f"### {instrument.name} ({instrument.symbol})",
                    f"- 状态：{signal.status}；动作：{signal.action}；置信度：{signal.confidence:.0%}",
                    f"- 最新价/净值：{signal.last_close:.4f}；MA20：{_fmt(signal.ma20)}；MA60：{_fmt(signal.ma60)}；RSI：{_fmt(signal.rsi)}",
                    _holding_line(signal),
                    _position_policy_line(signal),
                    _distance_line(signal),
                    _holding_advice_line(signal),
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
    weekly_reviews: list[WeeklyHoldingReview] | None = None,
    candidates: list[CandidateScore] | None = None,
    market_environment: MarketEnvironment | None = None,
) -> str:
    weekly_reviews = weekly_reviews or []
    candidates = candidates or []
    lines = [
        f"# 周末量化周报 - {report_date.isoformat()}",
        "",
        "- 推送口径：本周持仓回顾 + 自选外候选更新 + 资讯摘要 + 下周观察计划",
        "- 周末不生成具体交易价位或即时卖出指令，避免用休市行情给出交易结论。",
        "",
    ]
    lines.extend(_market_environment_lines(market_environment))
    lines.extend(["", "## 本周持仓回顾"])
    if weekly_reviews:
        for review in weekly_reviews:
            signal = review.signal
            lines.extend(
                [
                    f"### {review.instrument.name} ({review.instrument.symbol})",
                    f"- 本周涨跌：{_pct(review.weekly_change)}；本周最大回撤：{_pct(review.weekly_drawdown)}",
                    f"- 最新状态：{signal.status}；下周关注：{_next_week_focus(signal)}",
                ]
            )
    else:
        for instrument in config.watchlist:
            lines.append(f"- {instrument.name} ({instrument.symbol})：暂无可用周度行情，先关注资讯和下周开盘确认。")

    lines.extend(["", "## 自选外候选更新"])
    if candidates:
        for rank, candidate in enumerate(candidates, start=1):
            lines.append(
                f"{rank}. {candidate.instrument.name} ({candidate.instrument.symbol}) - 综合分 {candidate.score:.2f}；状态：{candidate.signal.status}；分组：{candidate.group}"
            )
    else:
        lines.append("- 暂无可用候选更新。")

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
            "## 风险事件日历",
            "- 政策、利率、汇率和海外市场变化对 A 股风险偏好的影响。",
            "- 持仓基金相关行业是否出现持续资金流入或突发风险事件。",
            "- 关注基金净值披露滞后、重仓行业公告和周一开盘后的成交反馈。",
            "",
            "## 下周观察计划",
            "- 偏强标的：优先观察回踩后能否守住 MA20 和近期支撑，不在高波动中追涨。",
            "- 观察标的：等待趋势和动量重新确认，再考虑是否恢复仓位。",
            "- 偏弱标的：优先控制仓位和回撤，反弹未修复均线前不主动加仓。",
            "",
            "## 免责声明",
            "本报告仅为资讯聚合和量化研究辅助，不自动交易，不构成保证收益或个人投顾建议。任何操作需自行判断并控制仓位风险。",
        ]
    )
    return "\n".join(lines)


def render_failure_report(
    report_date: str,
    session: str,
    run_url: str,
    message: str = "",
) -> str:
    lines = [
        f"# 量化日报任务失败 - {report_date}",
        "",
        f"- 任务类型：{session}",
        "- 状态：GitHub Actions 运行失败，未确认本次报告已成功发送。",
    ]
    if message:
        lines.append(f"- 错误摘要：{message}")
    if run_url:
        lines.append(f"- 运行链接：{run_url}")
    lines.extend(
        [
            "",
            "请打开运行链接查看失败步骤；如果是外部数据源波动，后续兜底触发或下一次定时任务会继续尝试。",
        ]
    )
    return "\n".join(lines)


def _market_environment_lines(market_environment: MarketEnvironment | None) -> list[str]:
    if market_environment is None:
        return [
            "## 市场环境",
            "- 暂无可用宽基指数环境数据，按个股/基金自身信号和风险位执行。",
        ]
    lines = [
        "## 市场环境",
        f"- 总体状态：{market_environment.status}；风险等级：{market_environment.risk_level}",
        f"- 仓位倾向：{market_environment.position_bias}",
        f"- 摘要：{market_environment.summary}",
    ]
    if market_environment.index_signals:
        details = []
        for signal in market_environment.index_signals[:4]:
            details.append(
                f"{signal.instrument.name}{signal.status}/20日{_pct(signal.pct20)}/回撤{_pct(signal.drawdown60)}"
            )
        lines.append(f"- 宽基观察：{'；'.join(details)}")
    return lines


def _fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2%}"


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


def _position_policy_line(signal: Signal) -> str | None:
    instrument = signal.instrument
    parts: list[str] = []
    if instrument.target_weight is not None:
        parts.append(f"目标仓位：{instrument.target_weight:.0%}")
    if instrument.max_weight is not None:
        parts.append(f"最大仓位：{instrument.max_weight:.0%}")
    if instrument.risk_level:
        parts.append(f"风险等级：{instrument.risk_level}")
    if instrument.note:
        parts.append(f"备注：{instrument.note}")
    if not parts:
        return None
    return "- " + "；".join(parts)


def _distance_line(signal: Signal) -> str:
    risk_distance = None
    if signal.stop_loss > 0:
        risk_distance = signal.last_close / signal.stop_loss - 1
    take_profit_distance = None
    if signal.last_close > 0:
        take_profit_distance = signal.take_profit / signal.last_close - 1
    return f"- 距离风险位：{_pct(risk_distance)}；距离止盈观察位：{_pct(take_profit_distance)}"


def _holding_advice_line(signal: Signal) -> str:
    advice = _holding_advice(signal)
    return f"- 持仓级建议：{advice}"


def _holding_advice(signal: Signal) -> str:
    if signal.stop_loss > 0 and signal.last_close <= signal.stop_loss:
        return "已触及或跌破风险位，优先控制仓位，暂停加仓，等待人工确认。"
    if signal.status == "偏弱":
        return "偏弱持仓，减仓观察，反弹未修复中期均线前不主动加仓。"
    if signal.stop_loss > 0 and signal.last_close <= signal.stop_loss * 1.03:
        return "接近风险位，轻仓防守，跌破风险位需人工确认是否降仓。"
    if signal.take_profit > 0 and signal.last_close >= signal.take_profit * 0.97:
        return "接近止盈/减仓观察位，偏向分批落袋或收紧风险位。"
    if signal.status == "偏强":
        return "趋势偏强，已有仓位可继续持有，回踩到观察区再考虑分批加仓。"
    return "信号尚未确认，维持轻仓观察，等待量价或均线重新确认。"


def _next_week_focus(signal: Signal) -> str:
    if signal.status == "偏强":
        return f"观察能否守住 MA20（{_fmt(signal.ma20)}）和风险位（{signal.stop_loss:.4f}）"
    if signal.status == "偏弱":
        return f"观察能否重新站回 MA20（{_fmt(signal.ma20)}），否则继续控制回撤"
    return f"观察 MA20（{_fmt(signal.ma20)}）与 MA60（{_fmt(signal.ma60)}）方向是否重新一致"

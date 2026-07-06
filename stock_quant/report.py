from __future__ import annotations

from datetime import date

from .config import AppConfig
from .models import (
    BacktestSummary,
    CandidateScore,
    DataFreshnessReport,
    FundIntradayEstimate,
    MarketEnvironment,
    MonthlyHoldingReview,
    PortfolioSummary,
    PositionAdvice,
    Signal,
    WeeklyHoldingReview,
)
from .news import NewsItem
from .alerts import Alert


def render_report(
    session: str,
    report_date: date,
    config: AppConfig,
    signals: list[Signal],
    candidates: list[CandidateScore],
    news_items: list[NewsItem],
    market_environment: MarketEnvironment | None = None,
    portfolio_summary: PortfolioSummary | None = None,
    freshness_report: DataFreshnessReport | None = None,
    backtest_summary: BacktestSummary | None = None,
    position_advices: dict[str, PositionAdvice] | None = None,
) -> str:
    return "\n\n---\n\n".join(
        [
            render_action_report(
                session,
                report_date,
                config,
                signals,
                candidates,
                market_environment,
                portfolio_summary,
                freshness_report,
                backtest_summary,
                position_advices,
            ),
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
    portfolio_summary: PortfolioSummary | None = None,
    freshness_report: DataFreshnessReport | None = None,
    backtest_summary: BacktestSummary | None = None,
    position_advices: dict[str, PositionAdvice] | None = None,
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
    lines.extend(["", *_portfolio_summary_lines(portfolio_summary)])
    lines.extend(["", *_freshness_lines(freshness_report)])
    lines.extend(["", *_backtest_summary_lines(backtest_summary)])
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
                    _target_position_advice_line(signal, position_advices),
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
                    _candidate_quality_line(candidate),
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
    intraday_estimates: dict[str, FundIntradayEstimate] | None = None,
    position_advices: dict[str, PositionAdvice] | None = None,
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
        "- 数据口径：基于当前可用最新净值/行情；如配置代理 ETF/指数，会显示 14:00 盘中估算。",
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
                    _intraday_estimate_line(signal, intraday_estimates),
                    _holding_line(signal),
                    _position_policy_line(signal),
                    _target_position_advice_line(signal, position_advices),
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
    monthly_reviews: list[MonthlyHoldingReview] | None = None,
    candidates: list[CandidateScore] | None = None,
    market_environment: MarketEnvironment | None = None,
    portfolio_summary: PortfolioSummary | None = None,
) -> str:
    weekly_reviews = weekly_reviews or []
    monthly_reviews = monthly_reviews or []
    candidates = candidates or []
    lines = [
        f"# 周末量化周报 - {report_date.isoformat()}",
        "",
        "- 推送口径：本周持仓回顾 + 自选外候选更新 + 资讯摘要 + 下周观察计划",
        "- 周末不生成具体交易价位或即时卖出指令，避免用休市行情给出交易结论。",
        "",
    ]
    lines.extend(_market_environment_lines(market_environment))
    lines.extend(["", *_weekend_portfolio_summary_lines(portfolio_summary, weekly_reviews, monthly_reviews)])
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

    lines.extend(["", "## 月度复盘"])
    if monthly_reviews:
        for review in monthly_reviews:
            lines.extend(
                [
                    f"### {review.instrument.name} ({review.instrument.symbol})",
                    f"- 近30日涨跌：{_pct(review.monthly_change)}；近30日最大回撤：{_pct(review.monthly_drawdown)}",
                    f"- 当前状态：{review.signal.status}；复盘提示：{_monthly_review_note(review.signal.status)}",
                ]
            )
    else:
        lines.append("- 暂无可用月度行情。")

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


def render_alert_report(
    report_date: date,
    session: str,
    alerts: list[Alert],
) -> str:
    lines = [
        f"# 异常提醒 - {report_date.isoformat()}",
        "",
        f"- 关联任务：{session}",
        "- 推送口径：仅在触发风险位、止盈位、仓位超限或数据异常时发送。",
        "",
        "## 触发事项",
    ]
    if alerts:
        for alert in alerts:
            lines.append(f"- [{alert.level}] {alert.title}：{alert.message}")
    else:
        lines.append("- 暂无异常。")
    lines.extend(
        [
            "",
            "## 免责声明",
            "本提醒仅为量化研究信号和风险提示，不自动交易，不构成保证收益或个人投顾建议。任何操作需自行判断并控制仓位风险。",
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


def _portfolio_summary_lines(portfolio_summary: PortfolioSummary | None) -> list[str]:
    lines = ["## 组合总览"]
    if portfolio_summary is None or portfolio_summary.total_principal <= 0:
        lines.append("- 暂无持仓金额配置，无法估算组合视角。")
        return lines
    lines.extend(
        [
            f"- 投入本金：{portfolio_summary.total_principal:.2f}",
            f"- 组合估算市值：{portfolio_summary.total_market_value:.2f}",
            f"- 估算总盈亏：{portfolio_summary.total_pnl_pct:.2%}（{portfolio_summary.total_pnl_amount:.2f}）",
        ]
    )
    if portfolio_summary.positions:
        top_positions = sorted(portfolio_summary.positions, key=lambda item: item.weight, reverse=True)[:5]
        details = [
            f"{position.instrument.name}{position.weight:.2%}/盈亏{position.pnl_pct:.2%}"
            for position in top_positions
        ]
        if details:
            lines.append(f"- 持仓占比：{'；'.join(details)}")
    if portfolio_summary.warnings:
        lines.append(f"- 仓位提醒：{'；'.join(portfolio_summary.warnings)}")
    return lines


def _freshness_lines(freshness_report: DataFreshnessReport | None) -> list[str]:
    lines = ["## 数据新鲜度"]
    if freshness_report is None:
        lines.append("- 暂无数据新鲜度检查结果。")
        return lines
    latest = freshness_report.latest_date.isoformat() if freshness_report.latest_date else "N/A"
    lines.append(f"- 最新行情日期：{latest}")
    if freshness_report.stale_symbols:
        lines.append(f"- 滞后标的：{', '.join(freshness_report.stale_symbols)}")
    if freshness_report.failed_symbols:
        lines.append(f"- 获取失败：{', '.join(freshness_report.failed_symbols)}")
    if not freshness_report.stale_symbols and not freshness_report.failed_symbols:
        lines.append("- 数据状态：未发现明显滞后或缺失。")
    return lines


def _backtest_summary_lines(backtest_summary: BacktestSummary | None) -> list[str]:
    lines = ["## 回测摘要"]
    if backtest_summary is None or backtest_summary.instrument_count == 0:
        lines.append("- 暂无足够历史数据生成回测摘要。")
        return lines
    lines.extend(
        [
            f"- 覆盖标的：{backtest_summary.instrument_count}",
            f"- 平均区间收益：{backtest_summary.average_period_return:.2%}",
            f"- 扣费后平均净收益：{_pct(backtest_summary.average_net_return)}",
            f"- 基准收益：{_pct(backtest_summary.benchmark_return)}；平均超额：{_pct(backtest_summary.average_excess_return)}",
            f"- 估算交易成本：{_pct(backtest_summary.estimated_cost_rate)}",
            f"- 最大回撤：{backtest_summary.max_drawdown:.2%}",
            f"- 信号成功率：{backtest_summary.signal_success_rate:.2%}",
            f"- 结论：{backtest_summary.summary}",
        ]
    )
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


def _target_position_advice_line(
    signal: Signal,
    advices: dict[str, PositionAdvice] | None,
) -> str | None:
    if not advices:
        return None
    advice = advices.get(signal.instrument.symbol)
    if advice is None:
        return None
    current = "N/A" if advice.current_weight is None else f"{advice.current_weight:.0%}"
    return (
        f"- 建议仓位区间：{advice.suggested_min:.0%} - {advice.suggested_max:.0%}；"
        f"当前占比：{current}；动作：{advice.action}；依据：{advice.reason}"
    )


def _intraday_estimate_line(
    signal: Signal,
    estimates: dict[str, FundIntradayEstimate] | None,
) -> str | None:
    if not estimates:
        return None
    estimate = estimates.get(signal.instrument.symbol)
    if estimate is None:
        return None
    proxy = "无代理标的" if not estimate.proxy_symbol else f"{estimate.proxy_name}({estimate.proxy_symbol})"
    return f"- 14:00盘中估算：{_pct(estimate.estimated_pct)}；代理：{proxy}；说明：{estimate.note}"


def _candidate_quality_line(candidate: CandidateScore) -> str | None:
    profile = candidate.quality_profile
    if profile is None:
        return None
    parts = [
        f"质量分 {profile.quality_score:.1f}",
        f"近1月 {_pct(profile.return_1m)}",
        f"近3月 {_pct(profile.return_3m)}",
        f"最大回撤 {_pct(profile.max_drawdown)}",
    ]
    if profile.fund_size is not None:
        parts.append(f"规模 {profile.fund_size / 100_000_000:.1f}亿")
    if profile.manager_tenure_days is not None:
        parts.append(f"经理任期 {profile.manager_tenure_days}天")
    if profile.fee_rate is not None:
        parts.append(f"费率 {_pct(profile.fee_rate)}")
    if profile.holding_concentration is not None:
        parts.append(f"重仓集中度 {_pct(profile.holding_concentration)}")
    return f"   - 基金质量画像：{'；'.join(parts)}"


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


def _weekend_portfolio_summary_lines(
    portfolio_summary: PortfolioSummary | None,
    weekly_reviews: list[WeeklyHoldingReview],
    monthly_reviews: list[MonthlyHoldingReview],
) -> list[str]:
    lines = ["## 组合周/月总结"]
    if portfolio_summary is not None and portfolio_summary.total_principal > 0:
        lines.extend(
            [
                f"- 组合估算市值：{portfolio_summary.total_market_value:.2f}",
                f"- 组合估算总盈亏：{portfolio_summary.total_pnl_pct:.2%}（{portfolio_summary.total_pnl_amount:.2f}）",
            ]
        )
    if weekly_reviews:
        best_week = max(weekly_reviews, key=lambda item: item.weekly_change if item.weekly_change is not None else -999)
        worst_week = min(weekly_reviews, key=lambda item: item.weekly_change if item.weekly_change is not None else 999)
        lines.append(f"- 本周表现最好：{best_week.instrument.name} {_pct(best_week.weekly_change)}")
        lines.append(f"- 本周风险最高：{worst_week.instrument.name}，本周回撤 {_pct(worst_week.weekly_drawdown)}")
    if monthly_reviews:
        best_month = max(monthly_reviews, key=lambda item: item.monthly_change if item.monthly_change is not None else -999)
        lines.append(f"- 近30日表现最好：{best_month.instrument.name} {_pct(best_month.monthly_change)}")
    if len(lines) == 1:
        lines.append("- 暂无足够持仓数据生成组合总结。")
    return lines


def _next_week_focus(signal: Signal) -> str:
    if signal.status == "偏强":
        return f"观察能否守住 MA20（{_fmt(signal.ma20)}）和风险位（{signal.stop_loss:.4f}）"
    if signal.status == "偏弱":
        return f"观察能否重新站回 MA20（{_fmt(signal.ma20)}），否则继续控制回撤"
    return f"观察 MA20（{_fmt(signal.ma20)}）与 MA60（{_fmt(signal.ma60)}）方向是否重新一致"


def _monthly_review_note(status: str) -> str:
    if status == "偏强":
        return "月度趋势偏强，继续关注回撤是否受控。"
    if status == "偏弱":
        return "月度表现偏弱，优先控制仓位和风险位。"
    return "月度方向未完全确认，等待趋势进一步清晰。"

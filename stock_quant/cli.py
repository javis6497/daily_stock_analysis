from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from datetime import date
from pathlib import Path
from re import sub
from zoneinfo import ZoneInfo

from .backtest import run_backtest
from .calendar import is_cn_trading_day
from .config import load_config
from .data import create_provider, fetch_many, resolve_instrument_names
from .freshness import build_data_freshness
from .market import build_market_environment
from .news import fetch_news, filter_news
from .notify import send_dingtalk_markdown
from .portfolio import build_portfolio_summary
from .ranking import rank_candidates
from .report import (
    render_failure_report,
    render_action_report,
    render_daily_news_report,
    render_fund_action_report,
    render_weekend_news_report,
)
from .strategy import analyze_instrument
from .universe import build_recommendation_pool
from .weekly import build_weekly_reviews
from .review import build_backtest_summary, build_monthly_reviews


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stock_quant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="生成盘前/盘后日报")
    report_parser.add_argument("--session", choices=["premarket", "postmarket", "weekend_news", "fund_action"], required=True)
    report_parser.add_argument("--config", default=os.environ.get("WATCHLIST_CONFIG", "config/watchlist.yml"))
    report_parser.add_argument("--send", action="store_true", help="发送到通知通道")
    report_parser.add_argument("--dry-run", action="store_true", help="只打印报告，不发网络请求")
    report_parser.add_argument("--sample-data", action="store_true", help="强制使用样例行情")
    report_parser.add_argument("--archive-dir", default="", help="保存本次报告 Markdown 和 manifest 的目录")

    backtest_parser = subparsers.add_parser("backtest", help="对自选标的做简单回看")
    backtest_parser.add_argument("--config", default=os.environ.get("WATCHLIST_CONFIG", "config/watchlist.yml"))
    backtest_parser.add_argument("--sample-data", action="store_true")

    failure_parser = subparsers.add_parser("notify-failure", help="发送 GitHub Actions 失败通知")
    failure_parser.add_argument("--session", default="unknown")
    failure_parser.add_argument("--report-date", default="")
    failure_parser.add_argument("--run-url", default="")
    failure_parser.add_argument("--message", default="")
    failure_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "report":
        return _run_report(args)
    if args.command == "backtest":
        return _run_backtest(args)
    if args.command == "notify-failure":
        return _run_notify_failure(args)
    return 2


def _run_report(args: argparse.Namespace) -> int:
    config_path = _resolve_config(args.config)
    app_config = load_config(config_path)
    provider_name = "sample" if args.sample_data else app_config.data.provider
    app_config = _resolve_display_names(app_config, provider_name)
    report_day = date.today()
    try:
        report_day = date.today()
        ZoneInfo(app_config.timezone)
    except Exception:
        pass

    if args.session == "weekend_news":
        return _run_weekend_news_report(args, app_config, report_day)
    if args.session == "fund_action":
        return _run_fund_action_report(args, app_config, report_day, provider_name)

    if app_config.report.skip_non_trading_day and not args.dry_run and not is_cn_trading_day(report_day):
        message = f"{report_day.isoformat()} 不是 A 股交易日，跳过日报。"
        if args.send:
            send_dingtalk_markdown("量化日报跳过", message, dry_run=args.dry_run)
        else:
            print(message)
        return 0

    provider = create_provider(provider_name)
    market_environment = build_market_environment(provider, app_config.data.lookback_days)
    watch_bars = fetch_many(provider, app_config.watchlist, app_config.data.lookback_days)
    candidate_pool = build_recommendation_pool(app_config)
    candidate_bars = fetch_many(provider, candidate_pool, app_config.data.lookback_days, strict=False)
    signals = [
        analyze_instrument(instrument, bars, app_config.report.risk_profile)
        for instrument, bars in watch_bars.items()
    ]
    portfolio_summary = build_portfolio_summary(signals)
    freshness_report = build_data_freshness(report_day, app_config.watchlist, watch_bars)
    backtest_summary = build_backtest_summary(watch_bars, app_config.report.risk_profile)
    candidates = rank_candidates(
        candidate_bars,
        top_n=app_config.report.top_n,
        risk_profile=app_config.report.risk_profile,
        max_per_group=app_config.recommendation.max_candidates_per_group,
        max_single_day_pct=app_config.recommendation.max_candidate_single_day_pct,
        market_environment=market_environment,
    )
    news_items = _collect_news(app_config)
    action_title = "盘前操作建议" if args.session == "premarket" else "盘后操作复盘"
    news_title = "盘前资讯摘要" if args.session == "premarket" else "盘后资讯摘要"
    messages = [
        (
            action_title,
            render_action_report(
                args.session,
                report_day,
                app_config,
                signals,
                candidates,
                market_environment,
                portfolio_summary,
                freshness_report,
                backtest_summary,
            ),
        ),
        (
            news_title,
            render_daily_news_report(args.session, report_day, app_config, news_items),
        ),
    ]
    _archive_messages(args.archive_dir, args.session, report_day, messages)
    _send_messages(messages, send=args.send, dry_run=args.dry_run)
    return 0


def _run_weekend_news_report(args: argparse.Namespace, app_config, report_day: date) -> int:
    news_items = _collect_news(app_config)
    provider = create_provider("sample" if args.sample_data else app_config.data.provider)
    market_environment = build_market_environment(provider, app_config.data.lookback_days)
    watch_bars = fetch_many(provider, app_config.watchlist, app_config.data.lookback_days, strict=False)
    candidate_pool = build_recommendation_pool(app_config)
    candidate_bars = fetch_many(provider, candidate_pool, app_config.data.lookback_days, strict=False)
    weekly_reviews = build_weekly_reviews(watch_bars, app_config.report.risk_profile)
    monthly_reviews = build_monthly_reviews(watch_bars, app_config.report.risk_profile)
    candidates = rank_candidates(
        candidate_bars,
        top_n=app_config.report.top_n,
        risk_profile=app_config.report.risk_profile,
        max_per_group=app_config.recommendation.max_candidates_per_group,
        max_single_day_pct=app_config.recommendation.max_candidate_single_day_pct,
        market_environment=market_environment,
    )
    markdown = render_weekend_news_report(
        report_day,
        app_config,
        news_items,
        weekly_reviews=weekly_reviews,
        monthly_reviews=monthly_reviews,
        candidates=candidates,
        market_environment=market_environment,
    )
    title = "周末量化周报"
    messages = [(title, markdown)]

    _archive_messages(args.archive_dir, args.session, report_day, messages)
    _send_messages(messages, send=args.send, dry_run=args.dry_run)
    return 0


def _run_fund_action_report(args: argparse.Namespace, app_config, report_day: date, provider_name: str) -> int:
    if app_config.report.skip_non_trading_day and not args.dry_run and not is_cn_trading_day(report_day):
        message = f"{report_day.isoformat()} 不是 A 股交易日，跳过基金操作提醒。"
        if args.send:
            send_dingtalk_markdown("基金操作提醒跳过", message, dry_run=args.dry_run)
        else:
            print(message)
        return 0

    fund_watchlist = [
        instrument
        for instrument in app_config.watchlist
        if instrument.asset_type.lower() in {"fund", "etf"}
    ]
    provider = create_provider(provider_name)
    market_environment = build_market_environment(provider, app_config.data.lookback_days)
    watch_bars = fetch_many(provider, fund_watchlist, app_config.data.lookback_days)
    signals = [
        analyze_instrument(instrument, bars, app_config.report.risk_profile)
        for instrument, bars in watch_bars.items()
    ]
    markdown = render_fund_action_report(report_day, app_config, signals, market_environment)
    messages = [("14:00基金操作提醒", markdown)]
    _archive_messages(args.archive_dir, args.session, report_day, messages)
    _send_messages(messages, send=args.send, dry_run=args.dry_run)
    return 0


def _collect_news(app_config) -> list:
    source_items = fetch_news(
        provider=app_config.news.provider,
        max_items=max(app_config.news.max_items * 4, app_config.news.max_items),
    )
    return filter_news(
        source_items,
        list(app_config.watchlist) + list(app_config.candidate_pool),
        app_config.news.keywords,
        max_items=app_config.news.max_items,
    )


def _resolve_display_names(app_config, provider_name: str):
    return replace(
        app_config,
        watchlist=resolve_instrument_names(provider_name, app_config.watchlist),
        candidate_pool=resolve_instrument_names(provider_name, app_config.candidate_pool),
    )


def _send_messages(messages: list[tuple[str, str]], send: bool, dry_run: bool) -> None:
    for idx, (title, markdown) in enumerate(messages):
        if send:
            send_dingtalk_markdown(title, markdown, dry_run=dry_run)
        if dry_run or not send:
            if idx:
                print("\n---\n")
            print(markdown)


def _archive_messages(
    archive_dir: str,
    session: str,
    report_day: date,
    messages: list[tuple[str, str]],
) -> None:
    if not archive_dir:
        return
    target = Path(archive_dir)
    target.mkdir(parents=True, exist_ok=True)
    manifest = {
        "session": session,
        "report_date": report_day.isoformat(),
        "files": [],
    }
    for idx, (title, markdown) in enumerate(messages, start=1):
        filename = f"{idx:02d}-{session}-{_slug(title)}.md"
        path = target / filename
        path.write_text(markdown, encoding="utf-8")
        manifest["files"].append({"title": title, "path": filename})
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _slug(text: str) -> str:
    value = sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", text).strip("-")
    return value or "report"


def _run_backtest(args: argparse.Namespace) -> int:
    config_path = _resolve_config(args.config)
    app_config = load_config(config_path)
    provider_name = "sample" if args.sample_data else app_config.data.provider
    app_config = _resolve_display_names(app_config, provider_name)
    provider = create_provider(provider_name)
    bars_by_instrument = fetch_many(provider, app_config.watchlist, app_config.data.lookback_days)
    result = [
        run_backtest(instrument, bars, app_config.report.risk_profile)
        for instrument, bars in bars_by_instrument.items()
    ]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _run_notify_failure(args: argparse.Namespace) -> int:
    report_date = args.report_date or date.today().isoformat()
    markdown = render_failure_report(
        report_date=report_date,
        session=args.session,
        run_url=args.run_url,
        message=args.message,
    )
    if args.dry_run:
        print(markdown)
        return 0
    send_dingtalk_markdown("量化日报任务失败", markdown, dry_run=False)
    return 0


def _resolve_config(path: str) -> Path:
    config_path = Path(path)
    if config_path.exists():
        return config_path
    example = Path("config/watchlist.example.yml")
    if path == "config/watchlist.yml" and example.exists():
        return example
    return config_path

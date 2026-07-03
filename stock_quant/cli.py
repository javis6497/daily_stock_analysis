from __future__ import annotations

import argparse
import json
import os
from dataclasses import replace
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from .backtest import run_backtest
from .calendar import is_cn_trading_day
from .config import load_config
from .data import create_provider, fetch_many, resolve_instrument_names
from .news import fetch_news, filter_news
from .notify import send_dingtalk_markdown
from .ranking import rank_candidates
from .report import (
    render_action_report,
    render_daily_news_report,
    render_fund_action_report,
    render_weekend_news_report,
)
from .strategy import analyze_instrument
from .universe import build_recommendation_pool


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stock_quant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="生成盘前/盘后日报")
    report_parser.add_argument("--session", choices=["premarket", "postmarket", "weekend_news", "fund_action"], required=True)
    report_parser.add_argument("--config", default=os.environ.get("WATCHLIST_CONFIG", "config/watchlist.yml"))
    report_parser.add_argument("--send", action="store_true", help="发送到通知通道")
    report_parser.add_argument("--dry-run", action="store_true", help="只打印报告，不发网络请求")
    report_parser.add_argument("--sample-data", action="store_true", help="强制使用样例行情")

    backtest_parser = subparsers.add_parser("backtest", help="对自选标的做简单回看")
    backtest_parser.add_argument("--config", default=os.environ.get("WATCHLIST_CONFIG", "config/watchlist.yml"))
    backtest_parser.add_argument("--sample-data", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "report":
        return _run_report(args)
    if args.command == "backtest":
        return _run_backtest(args)
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
    watch_bars = fetch_many(provider, app_config.watchlist, app_config.data.lookback_days)
    candidate_pool = build_recommendation_pool(app_config)
    candidate_bars = fetch_many(provider, candidate_pool, app_config.data.lookback_days, strict=False)
    signals = [
        analyze_instrument(instrument, bars, app_config.report.risk_profile)
        for instrument, bars in watch_bars.items()
    ]
    candidates = rank_candidates(
        candidate_bars,
        top_n=app_config.report.top_n,
        risk_profile=app_config.report.risk_profile,
    )
    news_items = _collect_news(app_config)
    action_title = "盘前操作建议" if args.session == "premarket" else "盘后操作复盘"
    news_title = "盘前资讯摘要" if args.session == "premarket" else "盘后资讯摘要"
    _send_messages(
        [
            (
                action_title,
                render_action_report(args.session, report_day, app_config, signals, candidates),
            ),
            (
                news_title,
                render_daily_news_report(args.session, report_day, app_config, news_items),
            ),
        ],
        send=args.send,
        dry_run=args.dry_run,
    )
    return 0


def _run_weekend_news_report(args: argparse.Namespace, app_config, report_day: date) -> int:
    news_items = _collect_news(app_config)
    markdown = render_weekend_news_report(report_day, app_config, news_items)
    title = "周末资讯观察"

    if args.send:
        send_dingtalk_markdown(title, markdown, dry_run=args.dry_run)
    if args.dry_run or not args.send:
        print(markdown)
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
    watch_bars = fetch_many(provider, fund_watchlist, app_config.data.lookback_days)
    signals = [
        analyze_instrument(instrument, bars, app_config.report.risk_profile)
        for instrument, bars in watch_bars.items()
    ]
    markdown = render_fund_action_report(report_day, app_config, signals)
    _send_messages([("14:00基金操作提醒", markdown)], send=args.send, dry_run=args.dry_run)
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


def _resolve_config(path: str) -> Path:
    config_path = Path(path)
    if config_path.exists():
        return config_path
    example = Path("config/watchlist.example.yml")
    if path == "config/watchlist.yml" and example.exists():
        return example
    return config_path

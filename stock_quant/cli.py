from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from .backtest import run_backtest
from .calendar import is_cn_trading_day
from .config import load_config
from .data import create_provider, fetch_many
from .news import filter_news, sample_news
from .notify import send_dingtalk_markdown
from .ranking import rank_candidates
from .report import render_report
from .strategy import analyze_instrument


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stock_quant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="生成盘前/盘后日报")
    report_parser.add_argument("--session", choices=["premarket", "postmarket"], required=True)
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
    report_day = date.today()
    try:
        report_day = date.today()
        ZoneInfo(app_config.timezone)
    except Exception:
        pass

    if app_config.report.skip_non_trading_day and not args.dry_run and not is_cn_trading_day(report_day):
        message = f"{report_day.isoformat()} 不是 A 股交易日，跳过日报。"
        if args.send:
            send_dingtalk_markdown("量化日报跳过", message, dry_run=args.dry_run)
        else:
            print(message)
        return 0

    provider_name = "sample" if args.sample_data else app_config.data.provider
    provider = create_provider(provider_name)
    watch_bars = fetch_many(provider, app_config.watchlist, app_config.data.lookback_days)
    candidate_pool = app_config.candidate_pool or app_config.watchlist
    candidate_bars = fetch_many(provider, candidate_pool, app_config.data.lookback_days)
    signals = [
        analyze_instrument(instrument, bars, app_config.report.risk_profile)
        for instrument, bars in watch_bars.items()
    ]
    candidates = rank_candidates(
        candidate_bars,
        top_n=app_config.report.top_n,
        risk_profile=app_config.report.risk_profile,
    )
    news_items = filter_news(
        sample_news(),
        list(app_config.watchlist) + list(app_config.candidate_pool),
        app_config.news.keywords,
        max_items=app_config.news.max_items,
    )
    markdown = render_report(args.session, report_day, app_config, signals, candidates, news_items)
    title = "盘前量化日报" if args.session == "premarket" else "盘后量化复盘"

    if args.send:
        send_dingtalk_markdown(title, markdown, dry_run=args.dry_run)
    if args.dry_run or not args.send:
        print(markdown)
    return 0


def _run_backtest(args: argparse.Namespace) -> int:
    config_path = _resolve_config(args.config)
    app_config = load_config(config_path)
    provider_name = "sample" if args.sample_data else app_config.data.provider
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

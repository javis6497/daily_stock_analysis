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
from .alerts import build_alerts
from .dashboard import generate_dashboard
from .fund_intraday import build_fund_intraday_estimates, build_proxy_instruments
from .fund_quality import build_fund_quality_profiles, fetch_fund_quality_metadata
from .ledger import write_signal_ledger
from .market import build_market_environment
from .news import fetch_news, filter_news
from .notify import send_dingtalk_markdown, send_dingtalk_markdown_chunks
from .position_advice import build_position_advices
from .portfolio import build_portfolio_summary
from .ranking import rank_candidates
from .report import (
    render_failure_report,
    render_alert_report,
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
    report_parser.add_argument("--ledger-dir", default="", help="保存结构化信号台账 JSON/CSV 的目录")
    report_parser.add_argument("--dashboard-dir", default="", help="生成 GitHub Pages 静态看板的目录")
    report_parser.add_argument("--pages-enabled", action="store_true", help="标记看板将公开发布到 GitHub Pages")

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
    benchmark_bars = _fetch_benchmark_bars(provider, app_config)
    backtest_summary = build_backtest_summary(
        watch_bars,
        app_config.report.risk_profile,
        buy_fee_rate=app_config.backtest.buy_fee_rate,
        sell_fee_rate=app_config.backtest.sell_fee_rate,
        slippage_rate=app_config.backtest.slippage_rate,
        turnover_cost_rate=app_config.backtest.turnover_cost_rate,
        benchmark_bars=benchmark_bars,
    )
    quality_profiles = build_fund_quality_profiles(
        candidate_bars,
        fetch_fund_quality_metadata(provider_name, list(candidate_bars.keys())),
    )
    candidates = rank_candidates(
        candidate_bars,
        top_n=app_config.report.top_n,
        risk_profile=app_config.report.risk_profile,
        max_per_group=app_config.recommendation.max_candidates_per_group,
        max_single_day_pct=app_config.recommendation.max_candidate_single_day_pct,
        market_environment=market_environment,
        quality_profiles=quality_profiles,
    )
    position_advices = build_position_advices(signals, portfolio_summary, market_environment)
    alerts = build_alerts(signals, candidates, freshness_report, portfolio_summary)
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
                position_advices,
            ),
        ),
        (
            news_title,
            render_daily_news_report(args.session, report_day, app_config, news_items),
        ),
    ]
    if alerts:
        messages.append(("异常提醒", render_alert_report(report_day, args.session, alerts)))
    archived_files = _archive_messages(args.archive_dir, args.session, report_day, messages)
    ledger_json_path = _write_ledger_if_requested(
        args.ledger_dir,
        args.session,
        report_day,
        signals,
        candidates,
        market_environment,
        portfolio_summary,
        alerts,
    )
    _generate_dashboard_if_requested(args.dashboard_dir, report_day, args.session, ledger_json_path, archived_files, args.pages_enabled)
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
    signals = [
        analyze_instrument(instrument, bars, app_config.report.risk_profile)
        for instrument, bars in watch_bars.items()
    ]
    portfolio_summary = build_portfolio_summary(signals)
    quality_profiles = build_fund_quality_profiles(
        candidate_bars,
        fetch_fund_quality_metadata(provider_name="sample" if args.sample_data else app_config.data.provider, instruments=list(candidate_bars.keys())),
    )
    candidates = rank_candidates(
        candidate_bars,
        top_n=app_config.report.top_n,
        risk_profile=app_config.report.risk_profile,
        max_per_group=app_config.recommendation.max_candidates_per_group,
        max_single_day_pct=app_config.recommendation.max_candidate_single_day_pct,
        market_environment=market_environment,
        quality_profiles=quality_profiles,
    )
    markdown = render_weekend_news_report(
        report_day,
        app_config,
        news_items,
        weekly_reviews=weekly_reviews,
        monthly_reviews=monthly_reviews,
        candidates=candidates,
        market_environment=market_environment,
        portfolio_summary=portfolio_summary,
    )
    title = "周末量化周报"
    messages = [(title, markdown)]

    archived_files = _archive_messages(args.archive_dir, args.session, report_day, messages)
    ledger_json_path = _write_ledger_if_requested(
        args.ledger_dir,
        args.session,
        report_day,
        signals,
        candidates,
        market_environment,
        portfolio_summary,
        [],
    )
    _generate_dashboard_if_requested(args.dashboard_dir, report_day, args.session, ledger_json_path, archived_files, args.pages_enabled)
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
    portfolio_summary = build_portfolio_summary(signals)
    position_advices = build_position_advices(signals, portfolio_summary, market_environment)
    proxy_bars = fetch_many(provider, build_proxy_instruments(signals), app_config.data.lookback_days, strict=False)
    intraday_estimates = build_fund_intraday_estimates(signals, proxy_bars, market_environment)
    alerts = build_alerts(signals, [], build_data_freshness(report_day, fund_watchlist, watch_bars), portfolio_summary)
    markdown = render_fund_action_report(
        report_day,
        app_config,
        signals,
        market_environment,
        intraday_estimates,
        position_advices,
    )
    messages = [("14:00基金操作提醒", markdown)]
    if alerts:
        messages.append(("基金异常提醒", render_alert_report(report_day, args.session, alerts)))
    archived_files = _archive_messages(args.archive_dir, args.session, report_day, messages)
    ledger_json_path = _write_ledger_if_requested(
        args.ledger_dir,
        args.session,
        report_day,
        signals,
        [],
        market_environment,
        portfolio_summary,
        alerts,
    )
    _generate_dashboard_if_requested(args.dashboard_dir, report_day, args.session, ledger_json_path, archived_files, args.pages_enabled)
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
            results = send_dingtalk_markdown_chunks(title, markdown, dry_run=dry_run)
            for part, result in enumerate(results, start=1):
                errcode = result.get("errcode", "dry_run")
                print(f"DingTalk sent: {title} part {part}/{len(results)} errcode={errcode}")
        if dry_run or not send:
            if idx:
                print("\n---\n")
            print(markdown)


def _archive_messages(
    archive_dir: str,
    session: str,
    report_day: date,
    messages: list[tuple[str, str]],
) -> list[Path]:
    if not archive_dir:
        return []
    target = Path(archive_dir)
    target.mkdir(parents=True, exist_ok=True)
    manifest = {
        "session": session,
        "report_date": report_day.isoformat(),
        "files": [],
    }
    archived_files: list[Path] = []
    for idx, (title, markdown) in enumerate(messages, start=1):
        filename = f"{idx:02d}-{session}-{_slug(title)}.md"
        path = target / filename
        path.write_text(markdown, encoding="utf-8")
        archived_files.append(path)
        manifest["files"].append({"title": title, "path": filename})
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return archived_files


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
    benchmark_bars = _fetch_benchmark_bars(provider, app_config)
    result = [
        run_backtest(
            instrument,
            bars,
            app_config.report.risk_profile,
            benchmark_bars=benchmark_bars,
            buy_fee_rate=app_config.backtest.buy_fee_rate,
            sell_fee_rate=app_config.backtest.sell_fee_rate,
            slippage_rate=app_config.backtest.slippage_rate,
            turnover_cost_rate=app_config.backtest.turnover_cost_rate,
        )
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


def _fetch_benchmark_bars(provider, app_config) -> list | None:
    from .models import Instrument

    benchmark = Instrument(
        symbol=app_config.backtest.benchmark_symbol,
        name=app_config.backtest.benchmark_name,
        market="cn",
        asset_type="index",
    )
    try:
        return provider.fetch_bars(benchmark, app_config.data.lookback_days)
    except Exception:
        return None


def _write_ledger_if_requested(
    ledger_dir: str,
    session: str,
    report_day: date,
    signals,
    candidates,
    market_environment,
    portfolio_summary,
    alerts,
) -> Path | None:
    if not ledger_dir:
        return None
    manifest = write_signal_ledger(
        ledger_dir,
        session,
        report_day,
        list(signals),
        list(candidates),
        market_environment,
        portfolio_summary,
        list(alerts),
    )
    return Path(ledger_dir) / manifest["json"]


def _generate_dashboard_if_requested(
    dashboard_dir: str,
    report_day: date,
    session: str,
    ledger_json_path: Path | None,
    archived_files: list[Path],
    pages_enabled: bool,
) -> None:
    if not dashboard_dir or ledger_json_path is None:
        return
    generate_dashboard(
        output_dir=dashboard_dir,
        report_date=report_day,
        session=session,
        ledger_json_path=ledger_json_path,
        report_files=archived_files,
        pages_enabled=pages_enabled,
    )

from __future__ import annotations

from datetime import date

from tests.helpers import make_bars, make_instrument, require_module


def test_render_report_contains_watchlist_candidates_news_and_disclaimer():
    config_mod = require_module("stock_quant.config")
    news_mod = require_module("stock_quant.news")
    ranking = require_module("stock_quant.ranking")
    report = require_module("stock_quant.report")
    strategy = require_module("stock_quant.strategy")

    watch = make_instrument("000001", "平安银行")
    candidate = make_instrument("510300", "沪深300ETF", "etf")
    app_config = config_mod.AppConfig(
        timezone="Asia/Shanghai",
        data=config_mod.DataConfig(provider="sample"),
        report=config_mod.ReportConfig(top_n=1, risk_profile="balanced"),
        notify=config_mod.NotifyConfig(channel="dingtalk"),
        news=config_mod.NewsConfig(keywords=["政策"]),
        watchlist=[watch],
        candidate_pool=[candidate],
    )
    signals = [strategy.analyze_instrument(watch, make_bars("up", count=90))]
    candidates = ranking.rank_candidates({candidate: make_bars("up", count=90)}, 1, "balanced")
    news_items = [
        news_mod.NewsItem(
            title="政策利好推动指数基金关注度提升",
            source="测试源",
            url="https://example.com/news",
            published_at="2026-07-03 08:00",
        )
    ]

    markdown = report.render_report(
        session="premarket",
        report_date=date(2026, 7, 3),
        config=app_config,
        signals=signals,
        candidates=candidates,
        news_items=news_items,
    )

    assert "盘前量化日报" in markdown
    assert "平安银行" in markdown
    assert "潜力候选" in markdown
    assert "沪深300ETF" in markdown
    assert "政策利好" in markdown
    assert "不构成保证收益" in markdown

from __future__ import annotations

from datetime import date

from tests.helpers import make_instrument, require_module


def test_render_weekend_news_report_contains_news_focus_and_no_trade_ranges():
    config_mod = require_module("stock_quant.config")
    news_mod = require_module("stock_quant.news")
    report = require_module("stock_quant.report")
    app_config = config_mod.AppConfig(
        watchlist=[make_instrument("018044", "基金018044", "fund")],
        news=config_mod.NewsConfig(keywords=["政策", "基金"], max_items=3),
    )
    items = [
        news_mod.NewsItem(
            title="政策预期带动基金关注度提升",
            source="测试源",
            url="https://example.com/news",
            published_at="2026-07-04 09:00",
            summary="周末市场关注政策和资金面。",
        )
    ]

    markdown = report.render_weekend_news_report(date(2026, 7, 4), app_config, items)

    assert "周末资讯观察" in markdown
    assert "政策预期带动基金关注度提升" in markdown
    assert "下周关注点" in markdown
    assert "买入观察区" not in markdown
    assert "止损" not in markdown
    assert "不构成保证收益" in markdown

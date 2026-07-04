from __future__ import annotations

from datetime import date

from tests.helpers import make_instrument, require_module


def test_render_weekend_news_report_contains_news_focus_and_no_trade_ranges():
    config_mod = require_module("stock_quant.config")
    models = require_module("stock_quant.models")
    news_mod = require_module("stock_quant.news")
    report = require_module("stock_quant.report")
    fund = make_instrument("018044", "基金018044", "fund")
    candidate = make_instrument("510300", "沪深300ETF", "etf")
    signal = models.Signal(
        instrument=fund,
        status="偏强",
        action="回踩观察",
        last_close=2.2,
        buy_zone=models.PriceRange(2.1, 2.2),
        stop_loss=1.9,
        take_profit=2.4,
        confidence=0.78,
        reasons=("趋势向上",),
        risks=("外部事件风险",),
    )
    weekly = models.WeeklyHoldingReview(
        instrument=fund,
        signal=signal,
        weekly_change=0.035,
        weekly_drawdown=0.018,
    )
    candidate_score = models.CandidateScore(
        instrument=candidate,
        score=82.3,
        signal=models.Signal(
            instrument=candidate,
            status="偏强",
            action="回踩观察",
            last_close=4.2,
            buy_zone=models.PriceRange(4.0, 4.2),
            stop_loss=3.8,
            take_profit=4.6,
            confidence=0.78,
            reasons=("趋势向上",),
            risks=("外部事件风险",),
        ),
        reasons=("状态 偏强",),
    )
    app_config = config_mod.AppConfig(
        watchlist=[fund],
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

    markdown = report.render_weekend_news_report(
        date(2026, 7, 4),
        app_config,
        items,
        weekly_reviews=[weekly],
        candidates=[candidate_score],
    )

    assert "周末量化周报" in markdown
    assert "政策预期带动基金关注度提升" in markdown
    assert "本周持仓回顾" in markdown
    assert "基金018044" in markdown
    assert "本周涨跌：3.50%" in markdown
    assert "本周最大回撤：1.80%" in markdown
    assert "下周观察计划" in markdown
    assert "自选外候选更新" in markdown
    assert "沪深300ETF" in markdown
    assert "买入观察区" not in markdown
    assert "止损" not in markdown
    assert "不构成保证收益" in markdown

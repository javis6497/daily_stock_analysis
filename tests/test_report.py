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


def test_render_report_contains_holding_cost_amount_and_estimated_pnl():
    config_mod = require_module("stock_quant.config")
    models = require_module("stock_quant.models")
    report = require_module("stock_quant.report")

    instrument = models.Instrument(
        symbol="018044",
        name="基金018044",
        market="cn",
        asset_type="fund",
        cost_price=2.0,
        holding_amount=10000,
        target_weight=0.2,
        max_weight=0.3,
        risk_level="medium",
        note="核心基金",
    )
    signal = models.Signal(
        instrument=instrument,
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
    app_config = config_mod.AppConfig(watchlist=[instrument])

    markdown = report.render_action_report(
        session="premarket",
        report_date=date(2026, 7, 3),
        config=app_config,
        signals=[signal],
        candidates=[],
    )

    assert "持仓成本：2.0000" in markdown
    assert "投入本金：10000.00" in markdown
    assert "估算盈亏：10.00%" in markdown
    assert "1000.00" in markdown
    assert "持仓级建议" in markdown
    assert "继续持有" in markdown
    assert "目标仓位：20%" in markdown
    assert "最大仓位：30%" in markdown
    assert "风险等级：medium" in markdown
    assert "备注：核心基金" in markdown
    assert "距离风险位" in markdown
    assert "距离止盈观察位" in markdown


def test_render_daily_news_report_contains_only_news_not_action_advice():
    config_mod = require_module("stock_quant.config")
    news_mod = require_module("stock_quant.news")
    report = require_module("stock_quant.report")
    app_config = config_mod.AppConfig(watchlist=[make_instrument("018044", "基金018044", "fund")])

    markdown = report.render_daily_news_report(
        session="premarket",
        report_date=date(2026, 7, 3),
        config=app_config,
        news_items=[
            news_mod.NewsItem(
                title="基金市场资讯",
                source="测试源",
                url="https://example.com/news",
                published_at="2026-07-03 08:00",
            )
        ],
    )

    assert "盘前资讯摘要" in markdown
    assert "基金市场资讯" in markdown
    assert "买入观察区" not in markdown
    assert "自选股/基金信号" not in markdown


def test_render_fund_action_report_contains_only_fund_signals():
    config_mod = require_module("stock_quant.config")
    models = require_module("stock_quant.models")
    report = require_module("stock_quant.report")
    stock = make_instrument("000001", "平安银行", "stock")
    fund = make_instrument("018044", "基金018044", "fund")
    stock_signal = models.Signal(
        instrument=stock,
        status="偏强",
        action="回踩观察",
        last_close=12.0,
        buy_zone=models.PriceRange(11.5, 12.0),
        stop_loss=11.0,
        take_profit=13.0,
        confidence=0.78,
        reasons=("趋势向上",),
        risks=("外部事件风险",),
    )
    fund_signal = models.Signal(
        instrument=fund,
        status="观察",
        action="等待确认",
        last_close=2.0,
        buy_zone=models.PriceRange(1.9, 2.0),
        stop_loss=1.8,
        take_profit=2.2,
        confidence=0.52,
        reasons=("等待均线确认",),
        risks=("净值滞后",),
    )

    markdown = report.render_fund_action_report(
        report_date=date(2026, 7, 3),
        config=config_mod.AppConfig(watchlist=[stock, fund]),
        signals=[stock_signal, fund_signal],
    )

    assert "14:00基金操作提醒" in markdown
    assert "基金018044" in markdown
    assert "平安银行" not in markdown
    assert "相关资讯" not in markdown
    assert "自选外量化候选" not in markdown

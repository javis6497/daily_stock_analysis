from __future__ import annotations

from datetime import date

from tests.helpers import require_module


def _fund_signal():
    models = require_module("stock_quant.models")
    fund = models.Instrument(
        symbol="018044",
        name="基金018044",
        market="cn",
        asset_type="fund",
        cost_price=2.0,
        holding_amount=1000,
        thesis="长期持有逻辑",
    )
    signal = models.Signal(
        instrument=fund,
        status="偏强",
        action="回踩观察",
        last_close=2.1,
        buy_zone=models.PriceRange(2.0, 2.1),
        stop_loss=1.9,
        take_profit=2.3,
        confidence=0.78,
        reasons=("趋势向上",),
        risks=("市场波动",),
    )
    return fund, signal


def test_fund_action_report_omits_repeated_daily_sections():
    config_mod = require_module("stock_quant.config")
    models = require_module("stock_quant.models")
    report = require_module("stock_quant.report")
    fund, signal = _fund_signal()
    market_environment = models.MarketEnvironment(
        status="进攻",
        risk_level="偏低",
        position_bias="均衡",
        summary="宽基指数向上",
    )
    thesis_review = models.ThesisReview(
        instrument=fund,
        status="有效",
        note="持仓逻辑未失效",
    )

    markdown = report.render_fund_action_report(
        report_date=date(2026, 7, 8),
        config=config_mod.AppConfig(watchlist=[fund]),
        signals=[signal],
        market_environment=market_environment,
        thesis_reviews={"018044": thesis_review},
    )

    assert "14:00基金操作提醒" in markdown
    assert "基金018044" in markdown
    assert "市场环境" not in markdown
    assert "持仓逻辑跟踪" not in markdown
    assert "目标仓位" not in markdown
    assert "备注" not in markdown
    assert markdown.count("免责声明") == 1


def test_postmarket_action_report_omits_premarket_repeated_sections():
    config_mod = require_module("stock_quant.config")
    models = require_module("stock_quant.models")
    report = require_module("stock_quant.report")
    instrument, signal = _fund_signal()
    candidate = models.CandidateScore(
        instrument=models.Instrument("510300", "沪深300ETF", "cn", "etf"),
        score=88,
        signal=signal,
        reasons=("候选理由",),
    )
    backtest_summary = models.BacktestSummary(
        instrument_count=1,
        average_period_return=0.1,
        max_drawdown=0.05,
        signal_success_rate=0.6,
        summary="历史表现正常",
    )
    thesis_review = models.ThesisReview(
        instrument=instrument,
        status="有效",
        note="持仓逻辑未失效",
    )

    markdown = report.render_action_report(
        session="postmarket",
        report_date=date(2026, 7, 8),
        config=config_mod.AppConfig(watchlist=[instrument]),
        signals=[signal],
        candidates=[candidate],
        backtest_summary=backtest_summary,
        thesis_reviews={"018044": thesis_review},
    )

    assert "盘后量化复盘" in markdown
    assert "盘后复盘重点" in markdown
    assert "基金018044" in markdown
    assert "自选外量化候选" not in markdown
    assert "回测摘要" not in markdown
    assert "持仓逻辑跟踪" not in markdown
    assert "买入观察区" not in markdown
    assert "筛选理由" not in markdown

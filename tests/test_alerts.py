from __future__ import annotations

from datetime import date

from tests.helpers import require_module


def test_build_alerts_flags_risk_breach_weight_breach_and_stale_data():
    alerts_mod = require_module("stock_quant.alerts")
    models = require_module("stock_quant.models")
    instrument = models.Instrument(symbol="018044", name="基金018044", market="cn", asset_type="fund")
    signal = models.Signal(
        instrument=instrument,
        status="偏弱",
        action="降低仓位",
        last_close=1.8,
        buy_zone=models.PriceRange(1.7, 1.9),
        stop_loss=1.9,
        take_profit=2.1,
        confidence=0.72,
        reasons=("趋势破坏",),
        risks=("下行风险",),
    )
    portfolio = models.PortfolioSummary(
        total_principal=10000,
        total_market_value=10000,
        total_pnl_amount=0,
        total_pnl_pct=0,
        positions=(),
        warnings=("基金018044 超过最大仓位 30%",),
    )
    freshness = models.DataFreshnessReport(
        latest_date=date(2026, 7, 3),
        stale_symbols=("018044",),
        failed_symbols=("012922",),
        items=(),
    )

    alerts = alerts_mod.build_alerts(
        signals=[signal],
        candidates=[],
        freshness_report=freshness,
        portfolio_summary=portfolio,
    )

    titles = [alert.title for alert in alerts]
    assert "跌破风险位" in titles
    assert "仓位超限" in titles
    assert "数据滞后" in titles
    assert "数据获取失败" in titles


def test_render_alert_report_contains_only_when_alerts_exist():
    alerts_mod = require_module("stock_quant.alerts")
    report = require_module("stock_quant.report")

    markdown = report.render_alert_report(
        report_date=date(2026, 7, 6),
        session="premarket",
        alerts=[
            alerts_mod.Alert(
                level="high",
                title="跌破风险位",
                message="基金018044 跌破风险位。",
            )
        ],
    )

    assert "异常提醒" in markdown
    assert "跌破风险位" in markdown
    assert "不构成保证收益" in markdown

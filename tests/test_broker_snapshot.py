from __future__ import annotations

import json
from datetime import date

from tests.helpers import require_module


def _snapshot_signal():
    models = require_module("stock_quant.models")
    fund = models.Instrument(
        symbol="018044",
        name="Tianhong Nasdaq 100 C",
        market="cn",
        asset_type="fund",
        market_value=765.45,
        holding_pnl_amount=-4.55,
        holding_pnl_pct=-0.0059,
    )
    return models.Signal(
        instrument=fund,
        status="watch",
        action="hold",
        last_close=2.0,
        buy_zone=models.PriceRange(1.9, 2.0),
        stop_loss=1.8,
        take_profit=2.2,
        confidence=0.52,
        reasons=("sample",),
        risks=("sample",),
    )


def test_portfolio_summary_uses_broker_snapshot_when_present():
    portfolio = require_module("stock_quant.portfolio")
    summary = portfolio.build_portfolio_summary([_snapshot_signal()])

    assert summary.total_market_value == 765.45
    assert summary.total_principal == 770.0
    assert summary.total_pnl_amount == -4.55
    assert round(summary.positions[0].pnl_pct, 4) == -0.0059


def test_action_report_renders_broker_snapshot_and_implied_cost():
    config_mod = require_module("stock_quant.config")
    report = require_module("stock_quant.report")
    signal = _snapshot_signal()

    markdown = report.render_action_report(
        session="premarket",
        report_date=date(2026, 7, 7),
        config=config_mod.AppConfig(watchlist=[signal.instrument]),
        signals=[signal],
        candidates=[],
    )

    assert "765.45" in markdown
    assert "-4.55" in markdown
    assert "-0.59%" in markdown
    assert "2.0119" in markdown


def test_signal_ledger_writes_broker_snapshot_fields(tmp_path):
    ledger = require_module("stock_quant.ledger")
    signal = _snapshot_signal()

    manifest = ledger.write_signal_ledger(
        tmp_path,
        session="premarket",
        report_date=date(2026, 7, 7),
        signals=[signal],
        candidates=[],
        market_environment=None,
        portfolio_summary=None,
        alerts=[],
    )

    payload = json.loads((tmp_path / manifest["json"]).read_text(encoding="utf-8"))
    row = payload["signals"][0]

    assert row["market_value"] == 765.45
    assert row["holding_pnl_amount"] == -4.55
    assert row["holding_pnl_pct"] == -0.0059
    assert round(row["implied_cost_price"], 4) == 2.0119

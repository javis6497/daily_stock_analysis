from __future__ import annotations

import json
from datetime import date

from tests.helpers import require_module


def _sample_objects():
    models = require_module("stock_quant.models")
    instrument = models.Instrument(
        symbol="018044",
        name="基金018044",
        market="cn",
        asset_type="fund",
        cost_price=2.0,
        holding_amount=10000,
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
    portfolio = models.PortfolioSummary(
        total_principal=10000,
        total_market_value=11000,
        total_pnl_amount=1000,
        total_pnl_pct=0.1,
        positions=(
            models.PortfolioPosition(
                instrument=instrument,
                market_value=11000,
                principal=10000,
                pnl_amount=1000,
                pnl_pct=0.1,
                weight=1.0,
            ),
        ),
    )
    market = models.MarketEnvironment(
        status="进攻",
        risk_level="偏低",
        position_bias="可维持均衡偏进攻",
        summary="宽基指数趋势向上。",
    )
    return instrument, signal, portfolio, market


def test_write_signal_ledger_outputs_json_and_csv(tmp_path):
    ledger = require_module("stock_quant.ledger")
    _, signal, portfolio, market = _sample_objects()

    manifest = ledger.write_signal_ledger(
        tmp_path,
        session="premarket",
        report_date=date(2026, 7, 6),
        signals=[signal],
        candidates=[],
        market_environment=market,
        portfolio_summary=portfolio,
        alerts=[],
    )

    json_path = tmp_path / manifest["json"]
    csv_path = tmp_path / manifest["signals_csv"]
    assert json_path.exists()
    assert csv_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["market_environment"]["status"] == "进攻"
    assert payload["portfolio_summary"]["total_market_value"] == 11000
    assert payload["signals"][0]["symbol"] == "018044"
    assert "018044" in csv_path.read_text(encoding="utf-8")


def test_generate_dashboard_writes_static_pages(tmp_path):
    dashboard = require_module("stock_quant.dashboard")
    ledger = require_module("stock_quant.ledger")
    _, signal, portfolio, market = _sample_objects()
    ledger_manifest = ledger.write_signal_ledger(
        tmp_path / "ledger",
        session="premarket",
        report_date=date(2026, 7, 6),
        signals=[signal],
        candidates=[],
        market_environment=market,
        portfolio_summary=portfolio,
        alerts=[],
    )
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "01-premarket-action.md").write_text("# 盘前量化日报", encoding="utf-8")

    dashboard.generate_dashboard(
        output_dir=tmp_path / "site",
        report_date=date(2026, 7, 6),
        session="premarket",
        ledger_json_path=tmp_path / "ledger" / ledger_manifest["json"],
        report_files=[report_dir / "01-premarket-action.md"],
        pages_enabled=False,
    )

    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    data = json.loads((tmp_path / "site" / "data" / "latest.json").read_text(encoding="utf-8"))
    assert "量化看板" in html
    assert "基金018044" in html
    assert "Pages 发布默认关闭" in html
    assert data["signals"][0]["symbol"] == "018044"

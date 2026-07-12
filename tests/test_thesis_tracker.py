from __future__ import annotations

from datetime import date

from tests.helpers import require_module


def test_load_config_parses_optional_holding_thesis_fields(tmp_path):
    config_mod = require_module("stock_quant.config")
    config_path = tmp_path / "watchlist.yml"
    config_path.write_text(
        """
watchlist:
  - symbol: "018044"
    name: 基金018044
    market: cn
    asset_type: fund
    thesis: 长期看好宽基修复
    thesis_risks:
      - 跌破长期均线
      - 行业景气下滑
    invalidation: 连续两周低于风险位
""",
        encoding="utf-8",
    )

    config = config_mod.load_config(config_path)

    instrument = config.watchlist[0]
    assert instrument.thesis == "长期看好宽基修复"
    assert instrument.thesis_risks == ("跌破长期均线", "行业景气下滑")
    assert instrument.invalidation == "连续两周低于风险位"


def test_build_thesis_reviews_flags_drift_when_signal_breaks_risk_level():
    models = require_module("stock_quant.models")
    thesis_mod = require_module("stock_quant.thesis_tracker")
    instrument = models.Instrument(
        symbol="018044",
        name="基金018044",
        market="cn",
        asset_type="fund",
        thesis="趋势修复后继续持有",
        thesis_risks=("跌破风险位",),
        invalidation="跌破风险位且信号偏弱",
    )
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

    reviews = thesis_mod.build_thesis_reviews([signal])

    assert reviews["018044"].status == "逻辑漂移"
    assert "跌破风险位" in reviews["018044"].note


def test_render_action_report_contains_thesis_reviews_and_audit_summary():
    config_mod = require_module("stock_quant.config")
    models = require_module("stock_quant.models")
    report = require_module("stock_quant.report")
    audit_mod = require_module("stock_quant.report_audit")
    instrument = models.Instrument(
        symbol="018044",
        name="基金018044",
        market="cn",
        asset_type="fund",
        thesis="宽基修复持有",
        thesis_risks=("风格切换",),
        invalidation="跌破风险位",
    )
    signal = models.Signal(
        instrument=instrument,
        status="观察",
        action="等待确认",
        last_close=2.0,
        buy_zone=models.PriceRange(1.9, 2.0),
        stop_loss=1.8,
        take_profit=2.2,
        confidence=0.52,
        reasons=("等待确认",),
        risks=("风格切换",),
    )
    thesis_review = models.ThesisReview(
        instrument=instrument,
        status="有效",
        note="持仓逻辑未触发失效条件",
    )
    audit_result = audit_mod.audit_report(
        "# 测试\n\n## 免责声明\n本报告仅为量化研究信号和风险提示，不构成保证收益或个人投顾建议。",
        "premarket",
    )

    markdown = report.render_action_report(
        session="premarket",
        report_date=date(2026, 7, 6),
        config=config_mod.AppConfig(watchlist=[instrument]),
        signals=[signal],
        candidates=[],
        thesis_reviews={"018044": thesis_review},
        audit_result=audit_result,
    )

    assert "持仓逻辑状态" in markdown
    assert "1 只持仓均未触发失效条件" in markdown
    assert "宽基修复持有" not in markdown
    assert "报告质检" in markdown

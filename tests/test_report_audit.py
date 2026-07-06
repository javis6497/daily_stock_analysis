from __future__ import annotations

from tests.helpers import require_module


def test_audit_report_flags_trade_commands_and_missing_disclaimer():
    audit_mod = require_module("stock_quant.report_audit")

    result = audit_mod.audit_report(
        "# 测试报告\n\n今天必须满仓买入 600000，保证收益。",
        context="premarket",
    )

    assert result.status == "需要复核"
    assert any(item.rule_id == "forbidden_command" for item in result.items)
    assert any(item.rule_id == "missing_disclaimer" for item in result.items)
    assert result.issue_count >= 2


def test_render_audit_summary_is_report_safe():
    audit_mod = require_module("stock_quant.report_audit")
    result = audit_mod.audit_report(
        "# 测试报告\n\n## 免责声明\n本报告仅为量化研究信号和风险提示，不构成保证收益或个人投顾建议。",
        context="premarket",
    )

    markdown = audit_mod.render_audit_summary(result)

    assert "报告质检" in markdown
    assert "通过" in markdown
    assert "仅为规则审计" in markdown

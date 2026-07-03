from __future__ import annotations

from pathlib import Path


def test_workflow_schedules_beijing_1400_fund_action():
    workflow = Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")

    assert 'cron: "0 6 * * 1-5"' in workflow
    assert "fund_action" in workflow
    assert 'github.event.schedule }}" = "0 6 * * 1-5"' in workflow
    assert "SESSION=fund_action" in workflow

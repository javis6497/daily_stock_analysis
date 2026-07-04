from __future__ import annotations

from pathlib import Path


def _workflow_text() -> str:
    return Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")


def test_workflow_schedules_redundant_windows_for_all_sessions():
    workflow = _workflow_text()

    expected = {
        "premarket": (
            "30 0 * * 1-5",
            "45 0 * * 1-5",
            "0 1 * * 1-5",
        ),
        "fund_action": (
            "0 6 * * 1-5",
            "15 6 * * 1-5",
            "30 6 * * 1-5",
        ),
        "postmarket": (
            "30 8 * * 1-5",
            "45 8 * * 1-5",
            "0 9 * * 1-5",
        ),
        "weekend_news": (
            "30 1 * * 6,0",
            "45 1 * * 6,0",
            "0 2 * * 6,0",
        ),
    }

    for session, crons in expected.items():
        for cron in crons:
            assert f'cron: "{cron}"' in workflow
            assert f'github.event.schedule }}}}" = "{cron}"' in workflow
        assert f"SESSION={session}" in workflow


def test_workflow_skips_duplicate_scheduled_session_with_daily_cache_marker():
    workflow = Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "group: daily-quant-report-${{ github.ref }}" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "REPORT_DATE" in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" in workflow
    assert "cache_key=report-sent-${SESSION}-${report_date}" in workflow
    assert "key: ${{ steps.report-meta.outputs.cache_key }}" in workflow
    assert "github.event_name != 'schedule' || steps.sent-cache.outputs.cache-hit != 'true'" in workflow


def test_workflow_notifies_dingtalk_when_report_job_fails():
    workflow = _workflow_text()

    assert "Notify failure" in workflow
    assert "failure()" in workflow
    assert "env.DINGTALK_WEBHOOK != ''" in workflow
    assert "python -m stock_quant notify-failure" in workflow
    assert "--run-url" in workflow

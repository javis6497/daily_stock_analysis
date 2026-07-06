from __future__ import annotations

from pathlib import Path


def _workflow_text() -> str:
    return Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")


def test_workflow_schedules_redundant_windows_for_all_sessions():
    workflow = _workflow_text()

    expected = {
        "premarket": (
            "37 0 * * 1-5",
            "52 0 * * 1-5",
            "7 1 * * 1-5",
            "30 1 * * 1-5",
        ),
        "fund_action": (
            "3 6 * * 1-5",
            "18 6 * * 1-5",
            "33 6 * * 1-5",
        ),
        "postmarket": (
            "37 8 * * 1-5",
            "52 8 * * 1-5",
            "7 9 * * 1-5",
        ),
        "weekend_news": (
            "37 1 * * 6,0",
            "52 1 * * 6,0",
            "7 2 * * 6,0",
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


def test_workflow_archives_generated_reports_as_artifact():
    workflow = _workflow_text()

    assert "--archive-dir reports" in workflow
    assert "--ledger-dir reports/ledger" in workflow
    assert "--dashboard-dir site" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "path: |\n            reports\n            site" in workflow
    assert "daily-quant-report-${{ env.SESSION }}-${{ env.REPORT_DATE }}" in workflow


def test_workflow_restores_and_saves_dashboard_history_cache():
    workflow = _workflow_text()

    assert "Restore dashboard history" in workflow
    assert "Save dashboard history" in workflow
    assert "dashboard-site-${{ env.REPORT_DATE }}-${{ env.SESSION }}-${{ github.run_id }}" in workflow
    assert "restore-keys: dashboard-site-" in workflow


def test_workflow_pages_publish_is_guarded_by_explicit_variable():
    workflow = _workflow_text()

    assert "ENABLE_PAGES" in workflow
    assert "vars.ENABLE_PAGES == 'true'" in workflow
    assert "actions/configure-pages@v5" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow

from __future__ import annotations

from pathlib import Path


def _workflow_text() -> str:
    return Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")


def test_workflow_schedules_redundant_windows_for_all_sessions():
    workflow = _workflow_text()

    expected = {
        "premarket": (
            "36 0 * * 1-5",
            "43 0 * * 1-5",
            "51 0 * * 1-5",
            "59 0 * * 1-5",
            "8 1 * * 1-5",
            "17 1 * * 1-5",
            "29 1 * * 1-5",
            "38 1 * * 1-5",
            "49 1 * * 1-5",
            "57 1 * * 1-5",
        ),
        "fund_action": (
            "8 6 * * 1-5",
            "17 6 * * 1-5",
            "29 6 * * 1-5",
            "38 6 * * 1-5",
            "49 6 * * 1-5",
        ),
        "postmarket": (
            "36 8 * * 1-5",
            "43 8 * * 1-5",
            "51 8 * * 1-5",
            "59 8 * * 1-5",
            "8 9 * * 1-5",
            "17 9 * * 1-5",
        ),
        "weekend_news": (
            "36 1 * * 6,0",
            "43 1 * * 6,0",
            "51 1 * * 6,0",
            "59 1 * * 6,0",
            "8 2 * * 6,0",
            "17 2 * * 6,0",
        ),
    }

    for session, crons in expected.items():
        for cron in crons:
            assert f'cron: "{cron}"' in workflow
            assert f'"{cron}"' in workflow
        assert f"SESSION={session}" in workflow


def test_workflow_schedule_minutes_avoid_common_peak_slots():
    workflow = _workflow_text()
    peak_minutes = {0, 1, 2, 3, 4, 5, 15, 30, 45}
    cron_lines = [line.strip() for line in workflow.splitlines() if line.strip().startswith("- cron:")]

    assert cron_lines
    for line in cron_lines:
        minute = int(line.split('"', 2)[1].split(" ", 1)[0])
        assert minute not in peak_minutes


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

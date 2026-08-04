from __future__ import annotations

from pathlib import Path


def _workflow_text() -> str:
    return Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")


def test_scheduled_workflows_have_single_fallback_cron():
    # The Cloudflare Worker is the primary on-time trigger; each wrapper keeps a
    # single GitHub `schedule` cron as a fallback when the Worker is down.
    expected = {
        "premarket-report.yml": ("premarket", "08:37", ("29 0 * * 1-5",)),
        "fund-action-report.yml": ("fund_action", "14:07", ("59 5 * * 1-5",)),
        "postmarket-report.yml": ("postmarket", "16:37", ("29 8 * * 1-5",)),
        "weekend-report.yml": ("weekend_news", "09:37", ("29 1 * * 6,0",)),
    }

    for filename, (session, target, crons) in expected.items():
        workflow = Path(".github/workflows", filename).read_text(encoding="utf-8")
        assert "uses: ./.github/workflows/daily-report.yml" in workflow
        assert f"session: {session}" in workflow
        assert f'delivery_target: "{target}"' in workflow
        assert "delivery_tolerance_minutes: 5" in workflow
        assert "scheduled_run: ${{ github.event_name == 'schedule' }}" in workflow
        for cron in crons:
            assert f'cron: "{cron}"' in workflow


def test_daily_report_workflow_is_manual_and_reusable_not_scheduled():
    workflow = _workflow_text()

    assert "workflow_dispatch:" in workflow
    assert "workflow_call:" in workflow
    assert "schedule:" not in workflow
    assert "session:" in workflow
    assert "scheduled_run:" in workflow


def test_workflow_skips_duplicate_scheduled_session_with_persistent_delivery_state():
    workflow = Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "group: daily-quant-report-${{ inputs.session }}-${{ github.ref }}" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "REPORT_DATE" in workflow
    assert "actions/cache/restore@v5" in workflow
    assert "actions/cache/save@v5" in workflow
    assert "state_prefix=report-state-${SESSION}-${report_date}-" in workflow
    assert "restore-keys: ${{ steps.report-meta.outputs.state_prefix }}" in workflow
    assert 'if [ -f ".report-state/${DELIVERY_KEY}.complete" ]' in workflow
    assert "steps.delivery-state.outputs.completed != 'true'" in workflow
    assert "SCHEDULED_RUN: ${{ inputs.scheduled_run == true }}" in workflow
    assert "DELIVERY_JOURNAL_DIR: .report-state" in workflow
    assert workflow.index("Write scheduled delivery receipt") < workflow.index("Upload report artifact")


def test_scheduled_run_enforces_delivery_window_and_skips_test_suite():
    workflow = _workflow_text()

    assert "delivery_target:" in workflow
    assert "delivery_tolerance_minutes:" in workflow
    assert "DELIVERY_TARGET" in workflow
    assert '--delivery-target "$DELIVERY_TARGET"' in workflow
    assert '--delivery-tolerance-minutes "$DELIVERY_TOLERANCE_MINUTES"' in workflow
    assert "if: env.SCHEDULED_RUN != 'true'" in workflow
    assert "DINGTALK_WEBHOOK is required for a scheduled delivery" in workflow
    assert "continue-on-error: ${{ inputs.silent_failure == true }}" in workflow


def test_scheduled_wrappers_suppress_failure_email_but_manual_runs_stay_strict():
    core = _workflow_text()

    assert "silent_failure:" in core
    assert "default: false" in core
    for filename in (
        "premarket-report.yml",
        "fund-action-report.yml",
        "postmarket-report.yml",
        "weekend-report.yml",
    ):
        workflow = Path(".github/workflows", filename).read_text(encoding="utf-8")
        assert "silent_failure: ${{ github.event_name == 'schedule' }}" in workflow


def test_workflow_notifies_dingtalk_when_report_job_fails():
    workflow = _workflow_text()

    assert "Notify failure" in workflow
    assert "failure()" in workflow
    assert "env.DINGTALK_WEBHOOK != ''" in workflow
    assert "python -m stock_quant notify-failure" in workflow
    assert "--run-url" in workflow


def test_workflow_scheduled_failure_notification_is_marker_guarded():
    workflow = _workflow_text()

    assert "((env.SCHEDULED_RUN != 'true' && failure()) || env.SCHEDULED_RUN == 'true')" in workflow
    assert 'if [ -f ".report-state/${DELIVERY_KEY}.complete" ]' in workflow
    assert 'if [ -f ".report-state/${DELIVERY_KEY}.notified" ]' in workflow
    assert 'touch ".report-state/${DELIVERY_KEY}.notified"' in workflow


def test_workflow_logs_scheduling_drift_for_scheduled_runs():
    workflow = _workflow_text()

    assert "Log scheduling drift" in workflow
    assert "if: env.SCHEDULED_RUN == 'true'" in workflow
    assert "delivery_target=$DELIVERY_TARGET" in workflow
    assert "job_start_beijing" in workflow


def test_workflow_archives_generated_reports_as_artifact():
    workflow = _workflow_text()

    assert "--archive-dir reports" in workflow
    assert "--ledger-dir reports/ledger" in workflow
    assert "--dashboard-dir site" in workflow
    assert "actions/upload-artifact@v6" in workflow
    assert "path: |\n            reports\n            site" in workflow
    assert "daily-quant-report-${{ env.SESSION }}-${{ env.REPORT_DATE }}" in workflow


def test_workflow_restores_and_saves_dashboard_history_cache():
    workflow = _workflow_text()

    assert "Restore dashboard history" in workflow
    assert "Save dashboard history" in workflow
    assert "dashboard-site-${{ env.REPORT_DATE }}-${{ env.SESSION }}-${{ github.run_id }}" in workflow
    assert "restore-keys: dashboard-site-" in workflow


def test_workflow_restores_and_saves_market_data_cache():
    workflow = _workflow_text()

    assert "MARKET_DATA_CACHE_DIR: .market-data-cache" in workflow
    assert "Restore market data cache" in workflow
    assert "Save market data cache" in workflow
    assert "restore-keys: market-data-" in workflow


def test_workflow_pages_publish_is_guarded_by_explicit_variable():
    workflow = _workflow_text()

    assert "ENABLE_PAGES" in workflow
    assert "vars.ENABLE_PAGES == 'true'" in workflow
    assert "actions/configure-pages@v5" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow

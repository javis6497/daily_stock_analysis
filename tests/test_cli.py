from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_report_dry_run_generates_premarket_report(tmp_path):
    config_path = tmp_path / "watchlist.yml"
    config_path.write_text(
        """
data:
  provider: sample
report:
  top_n: 1
watchlist:
  - symbol: "000001"
    name: 平安银行
    market: cn
    asset_type: stock
candidate_pool:
  - symbol: "510300"
    name: 沪深300ETF
    market: cn
    asset_type: etf
""",
        encoding="utf-8",
    )

    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_quant",
            "report",
            "--session",
            "premarket",
            "--config",
            str(config_path),
            "--dry-run",
        ],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "盘前量化日报" in result.stdout
    assert "平安银行" in result.stdout


def test_cli_weekend_news_dry_run_generates_news_only_report(tmp_path):
    config_path = tmp_path / "watchlist.yml"
    config_path.write_text(
        """
data:
  provider: sample
news:
  provider: sample
  keywords: ["政策", "基金"]
  max_items: 3
watchlist:
  - symbol: "018044"
    name: 基金018044
    market: cn
    asset_type: fund
""",
        encoding="utf-8",
    )

    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_quant",
            "report",
            "--session",
            "weekend_news",
            "--config",
            str(config_path),
            "--dry-run",
        ],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "周末量化周报" in result.stdout
    assert "本周持仓回顾" in result.stdout
    assert "基金018044" in result.stdout
    assert "本周涨跌" in result.stdout
    assert "买入观察区" not in result.stdout


def test_cli_fund_action_dry_run_generates_fund_only_report(tmp_path):
    config_path = tmp_path / "watchlist.yml"
    config_path.write_text(
        """
data:
  provider: sample
watchlist:
  - symbol: "000001"
    name: 平安银行
    market: cn
    asset_type: stock
  - symbol: "018044"
    name: 基金018044
    market: cn
    asset_type: fund
""",
        encoding="utf-8",
    )

    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_quant",
            "report",
            "--session",
            "fund_action",
            "--config",
            str(config_path),
            "--dry-run",
        ],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "14:00基金操作提醒" in result.stdout
    assert "基金018044" in result.stdout
    assert "平安银行" not in result.stdout
    assert "资讯摘要" not in result.stdout


def test_cli_notify_failure_dry_run_generates_failure_message():
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stock_quant",
            "notify-failure",
            "--session",
            "premarket",
            "--report-date",
            "2026-07-04",
            "--run-url",
            "https://github.com/example/repo/actions/runs/1",
            "--dry-run",
        ],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "量化日报任务失败" in result.stdout
    assert "premarket" in result.stdout
    assert "https://github.com/example/repo/actions/runs/1" in result.stdout


def test_send_daily_messages_sends_action_and_news_separately(monkeypatch):
    cli = __import__("stock_quant.cli", fromlist=["cli"])
    sent = []

    def fake_send(title, markdown, dry_run=False):
        sent.append((title, markdown, dry_run))

    monkeypatch.setattr(cli, "send_dingtalk_markdown", fake_send)

    cli._send_messages(
        [
            ("盘前操作建议", "action text"),
            ("盘前资讯摘要", "news text"),
        ],
        send=True,
        dry_run=False,
    )

    assert sent == [
        ("盘前操作建议", "action text", False),
        ("盘前资讯摘要", "news text", False),
    ]

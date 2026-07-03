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

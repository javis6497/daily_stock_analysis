from __future__ import annotations

import json
from datetime import date
from html import escape
from pathlib import Path


def generate_dashboard(
    output_dir: str | Path,
    report_date: date,
    session: str,
    ledger_json_path: str | Path,
    report_files: list[Path],
    pages_enabled: bool = False,
) -> None:
    target = Path(output_dir)
    data_dir = target / "data"
    reports_dir = target / "reports" / report_date.isoformat() / session
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    ledger_path = Path(ledger_json_path)
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    (data_dir / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for report_file in report_files:
        if not report_file.exists() or report_file.suffix.lower() != ".md":
            continue
        destination = reports_dir / report_file.name
        destination.write_text(report_file.read_text(encoding="utf-8"), encoding="utf-8")

    (target / "index.html").write_text(
        _render_html(payload, _collect_report_files(target), pages_enabled),
        encoding="utf-8",
    )


def _collect_report_files(site_dir: Path) -> list[dict[str, str]]:
    reports_root = site_dir / "reports"
    if not reports_root.exists():
        return []
    files = sorted(reports_root.glob("*/*/*.md"), reverse=True)
    return [
        {
            "name": path.name,
            "path": path.relative_to(site_dir).as_posix(),
        }
        for path in files
    ]


def _render_html(payload: dict, report_files: list[dict[str, str]], pages_enabled: bool) -> str:
    signals = payload.get("signals", [])
    candidates = payload.get("candidates", [])
    market = payload.get("market_environment") or {}
    portfolio = payload.get("portfolio_summary") or {}
    alerts = payload.get("alerts") or []
    publish_note = "" if pages_enabled else "<p class='warn'>Pages 发布默认关闭，避免公开仓库暴露持仓金额。</p>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>量化看板</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172026; background: #f6f8fb; }}
    header {{ background: #153047; color: white; padding: 28px 20px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 20px; }}
    section {{ background: white; border: 1px solid #d8e0e8; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #e3e8ef; border-radius: 6px; padding: 12px; background: #fbfcfe; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e5eaf0; padding: 9px 8px; text-align: left; }}
    th {{ background: #f0f4f8; }}
    .warn {{ color: #8a4b00; background: #fff7e6; border: 1px solid #f2d08a; padding: 10px; border-radius: 6px; }}
    a {{ color: #0b63ce; }}
  </style>
</head>
<body>
  <header>
    <h1>量化看板</h1>
    <div>{escape(payload.get("report_date", ""))} / {escape(payload.get("session", ""))}</div>
  </header>
  <main>
    {publish_note}
    <section>
      <h2>市场与组合</h2>
      <div class="grid">
        <div class="metric">市场状态<br><strong>{escape(str(market.get("status", "N/A")))}</strong></div>
        <div class="metric">风险等级<br><strong>{escape(str(market.get("risk_level", "N/A")))}</strong></div>
        <div class="metric">组合市值<br><strong>{_money(portfolio.get("total_market_value"))}</strong></div>
        <div class="metric">估算盈亏<br><strong>{_pct(portfolio.get("total_pnl_pct"))}</strong></div>
      </div>
    </section>
    <section>
      <h2>当前持仓信号</h2>
      {_signals_table(signals)}
    </section>
    <section>
      <h2>自选外候选</h2>
      {_candidates_table(candidates)}
    </section>
    <section>
      <h2>异常提醒</h2>
      {_alerts_list(alerts)}
    </section>
    <section>
      <h2>历史报告</h2>
      {_report_links(report_files)}
    </section>
  </main>
</body>
</html>
"""


def _signals_table(signals: list[dict]) -> str:
    if not signals:
        return "<p>暂无信号。</p>"
    rows = []
    for item in signals:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('name', '')))}</td>"
            f"<td>{escape(str(item.get('symbol', '')))}</td>"
            f"<td>{escape(str(item.get('status', '')))}</td>"
            f"<td>{_money(item.get('holding_amount'))}</td>"
            f"<td>{_pct(item.get('pnl_pct'))}</td>"
            f"<td>{_number(item.get('stop_loss'))}</td>"
            f"<td>{_number(item.get('take_profit'))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>名称</th><th>代码</th><th>状态</th><th>本金</th><th>盈亏</th><th>风险位</th><th>止盈位</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _candidates_table(candidates: list[dict]) -> str:
    if not candidates:
        return "<p>暂无候选。</p>"
    rows = []
    for item in candidates:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('name', '')))}</td>"
            f"<td>{escape(str(item.get('symbol', '')))}</td>"
            f"<td>{_number(item.get('score'))}</td>"
            f"<td>{escape(str(item.get('group', '')))}</td>"
            f"<td>{_number(item.get('quality_score'))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>名称</th><th>代码</th><th>评分</th><th>分组</th><th>质量分</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _alerts_list(alerts: list[dict]) -> str:
    if not alerts:
        return "<p>暂无异常提醒。</p>"
    return "<ul>" + "".join(f"<li><strong>{escape(str(item.get('title', '')))}</strong>：{escape(str(item.get('message', '')))}</li>" for item in alerts) + "</ul>"


def _report_links(report_files: list[dict[str, str]]) -> str:
    if not report_files:
        return "<p>暂无归档报告。</p>"
    return "<ul>" + "".join(f"<li><a href='{escape(item['path'])}'>{escape(item['name'])}</a></li>" for item in report_files) + "</ul>"


def _money(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):,.2f}"


def _pct(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.2%}"


def _number(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.4f}" if abs(float(value)) < 10 else f"{float(value):.2f}"

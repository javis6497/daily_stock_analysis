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
    thesis_reviews = payload.get("thesis_reviews") or {}
    report_audit = payload.get("report_audit") or {}
    price_history = payload.get("price_history") or {}
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
    details.holding {{ border-top: 1px solid #e1e7ed; }}
    details.holding:last-child {{ border-bottom: 1px solid #e1e7ed; }}
    details.holding summary {{ display: grid; grid-template-columns: minmax(180px, 1.8fr) repeat(3, minmax(90px, .7fr)); gap: 10px; align-items: center; padding: 13px 4px; cursor: pointer; list-style-position: inside; }}
    details.holding[open] summary {{ border-bottom: 1px solid #e8edf2; }}
    .holding-body {{ padding: 14px 4px 18px; }}
    .holding-name {{ font-weight: 700; }}
    .muted {{ color: #65717c; font-size: 13px; }}
    .signal-strong {{ color: #b42318; }}
    .signal-weak {{ color: #137333; }}
    .chart-wrap {{ overflow-x: auto; border: 1px solid #e2e8ee; background: #fff; margin-top: 12px; }}
    .holding-chart {{ display: block; width: 100%; min-width: 620px; height: auto; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 14px; color: #52606d; font-size: 12px; margin: 8px 0; }}
    .dot {{ display: inline-block; width: 18px; height: 3px; margin-right: 5px; vertical-align: middle; }}
    .detail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 9px; margin-top: 12px; }}
    .detail-item {{ padding: 9px 10px; background: #f7f9fb; border-left: 3px solid #aab6c2; }}
    .table-scroll {{ overflow-x: auto; }}
    a {{ color: #0b63ce; }}
    @media (max-width: 720px) {{
      header {{ padding: 20px 16px; }}
      main {{ padding: 12px; }}
      section {{ padding: 13px; }}
      details.holding summary {{ grid-template-columns: 1fr 1fr; }}
      details.holding summary .holding-name {{ grid-column: 1 / -1; }}
    }}
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
      <p class="muted">点击每只持仓可展开或收起完整信号与走势图。</p>
      {_holding_details(signals, price_history, thesis_reviews)}
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
      <h2>报告质检</h2>
      {_audit_panel(report_audit)}
    </section>
    <section>
      <h2>历史报告</h2>
      {_report_links(report_files)}
    </section>
  </main>
  <script>
    function openHoldingFromHash() {{
      if (!location.hash) return;
      const target = document.querySelector(location.hash);
      if (target && target.tagName === "DETAILS") {{
        target.open = true;
        target.scrollIntoView({{ behavior: "smooth", block: "start" }});
      }}
    }}
    window.addEventListener("hashchange", openHoldingFromHash);
    window.addEventListener("DOMContentLoaded", openHoldingFromHash);
  </script>
</body>
</html>
"""


def _holding_details(
    signals: list[dict],
    price_history: dict[str, list[dict]],
    thesis_reviews: dict,
) -> str:
    if not signals:
        return "<p>暂无信号。</p>"
    blocks = []
    for item in signals:
        symbol = str(item.get("symbol", ""))
        status = str(item.get("status", ""))
        status_class = "signal-strong" if status == "偏强" else "signal-weak" if status == "偏弱" else ""
        review = thesis_reviews.get(symbol) or {}
        instrument = review.get("instrument") or {}
        chart = _candlestick_chart(price_history.get(symbol) or [], item)
        blocks.append(
            f"<details class='holding' id='holding-{escape(symbol)}'>"
            "<summary>"
            f"<span class='holding-name'>{escape(str(item.get('name', '')))} <span class='muted'>{escape(symbol)}</span></span>"
            f"<span class='{status_class}'>{escape(status)} / {escape(str(item.get('action', '')))}</span>"
            f"<span>盈亏 {_pct(item.get('pnl_pct'))}</span>"
            f"<span>市值 {_money(item.get('position_market_value') or item.get('market_value'))}</span>"
            "</summary>"
            "<div class='holding-body'>"
            "<div class='detail-grid'>"
            f"<div class='detail-item'>最新价/净值<br><strong>{_number(item.get('last_close'))}</strong></div>"
            f"<div class='detail-item'>持仓成本<br><strong>{_number(item.get('cost_price') or item.get('implied_cost_price'))}</strong></div>"
            f"<div class='detail-item'>投入本金<br><strong>{_money(item.get('position_principal') or item.get('holding_amount'))}</strong></div>"
            f"<div class='detail-item'>估算盈亏<br><strong>{_money(item.get('pnl_amount'))}</strong></div>"
            f"<div class='detail-item'>买入观察区<br><strong>{_number(item.get('buy_zone_lower'))} - {_number(item.get('buy_zone_upper'))}</strong></div>"
            f"<div class='detail-item'>风险位 / 止盈位<br><strong>{_number(item.get('stop_loss'))} / {_number(item.get('take_profit'))}</strong></div>"
            "</div>"
            f"{chart}"
            "<h3>持仓逻辑跟踪</h3>"
            f"<p>{escape(str(instrument.get('thesis') or item.get('thesis') or '未配置持仓逻辑'))}</p>"
            f"<p class='muted'>失效条件：{escape(str(instrument.get('invalidation') or item.get('invalidation') or '未配置'))}</p>"
            f"<p class='muted'>复核：{escape(str(review.get('status') or '暂无'))}；{escape(str(review.get('note') or ''))}</p>"
            "</div></details>"
        )
    return "".join(blocks)


def _candlestick_chart(bars: list[dict], signal: dict) -> str:
    if len(bars) < 2:
        return "<p class='muted'>暂无足够行情绘制 K 线。</p>"
    bars = bars[-90:]
    width, height = 760, 300
    left, right, top, bottom = 52, 16, 18, 35
    plot_width = width - left - right
    plot_height = height - top - bottom
    lows = [float(item["low"]) for item in bars]
    highs = [float(item["high"]) for item in bars]
    low, high = min(lows), max(highs)
    padding = max((high - low) * 0.08, abs(high) * 0.002, 0.001)
    low -= padding
    high += padding
    span = high - low or 1.0

    def y(value: float) -> float:
        return top + (high - value) / span * plot_height

    step = plot_width / len(bars)
    body_width = max(2.0, min(8.0, step * 0.58))
    svg: list[str] = [
        f"<svg class='holding-chart' viewBox='0 0 {width} {height}' role='img' aria-label='最近90日K线走势图'>",
        "<rect width='100%' height='100%' fill='#ffffff'/>",
    ]
    for idx in range(5):
        value = high - span * idx / 4
        y_pos = y(value)
        svg.append(f"<line x1='{left}' y1='{y_pos:.1f}' x2='{width-right}' y2='{y_pos:.1f}' stroke='#edf1f4'/>")
        svg.append(f"<text x='{left-6}' y='{y_pos+4:.1f}' text-anchor='end' font-size='10' fill='#6b7785'>{value:.3f}</text>")
    for idx, bar in enumerate(bars):
        x = left + step * (idx + 0.5)
        open_price = float(bar["open"])
        close = float(bar["close"])
        color = "#c62828" if close >= open_price else "#14833b"
        svg.append(f"<line x1='{x:.1f}' y1='{y(float(bar['high'])):.1f}' x2='{x:.1f}' y2='{y(float(bar['low'])):.1f}' stroke='{color}' stroke-width='1'/>")
        body_top = min(y(open_price), y(close))
        body_height = max(1.0, abs(y(open_price) - y(close)))
        svg.append(f"<rect x='{x-body_width/2:.1f}' y='{body_top:.1f}' width='{body_width:.1f}' height='{body_height:.1f}' fill='{color}'/>")

    closes = [float(item["close"]) for item in bars]
    for period, color in ((20, "#d28b00"), (60, "#1769aa")):
        points = []
        for idx in range(period - 1, len(closes)):
            average = sum(closes[idx - period + 1 : idx + 1]) / period
            x = left + step * (idx + 0.5)
            points.append(f"{x:.1f},{y(average):.1f}")
        if points:
            svg.append(f"<polyline points='{' '.join(points)}' fill='none' stroke='{color}' stroke-width='1.6'/>")

    level_specs = (
        (signal.get("cost_price") or signal.get("implied_cost_price"), "#6b4fa1", "成本"),
        (signal.get("stop_loss"), "#14833b", "风险位"),
        (signal.get("take_profit"), "#c62828", "止盈位"),
    )
    for value, color, label in level_specs:
        if value is None or not low <= float(value) <= high:
            continue
        y_pos = y(float(value))
        svg.append(f"<line x1='{left}' y1='{y_pos:.1f}' x2='{width-right}' y2='{y_pos:.1f}' stroke='{color}' stroke-dasharray='5 4'/>")
        svg.append(f"<text x='{width-right-2}' y='{y_pos-4:.1f}' text-anchor='end' font-size='10' fill='{color}'>{label}</text>")
    svg.append(f"<text x='{left}' y='{height-10}' font-size='10' fill='#6b7785'>{escape(str(bars[0].get('date', '')))}</text>")
    svg.append(f"<text x='{width-right}' y='{height-10}' text-anchor='end' font-size='10' fill='#6b7785'>{escape(str(bars[-1].get('date', '')))}</text>")
    svg.append("</svg>")
    legend = (
        "<div class='legend'>"
        "<span><i class='dot' style='background:#d28b00'></i>MA20</span>"
        "<span><i class='dot' style='background:#1769aa'></i>MA60</span>"
        "<span><i class='dot' style='background:#6b4fa1'></i>成本</span>"
        "<span><i class='dot' style='background:#14833b'></i>风险位</span>"
        "<span><i class='dot' style='background:#c62828'></i>止盈位</span>"
        "</div>"
    )
    return f"<div class='chart-wrap'>{''.join(svg)}</div>{legend}"


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
            f"<td>{escape(str(item.get('quality_type') or ''))}</td>"
            f"<td>{_number(item.get('pe'))} / {_number(item.get('pb'))}</td>"
            "</tr>"
        )
    table = "<table><thead><tr><th>名称</th><th>代码</th><th>评分</th><th>分组</th><th>质量分</th><th>画像</th><th>PE/PB</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    return f"<div class='table-scroll'>{table}</div>"


def _alerts_list(alerts: list[dict]) -> str:
    if not alerts:
        return "<p>暂无异常提醒。</p>"
    return "<ul>" + "".join(f"<li><strong>{escape(str(item.get('title', '')))}</strong>：{escape(str(item.get('message', '')))}</li>" for item in alerts) + "</ul>"


def _thesis_reviews_table(thesis_reviews: dict) -> str:
    if not thesis_reviews:
        return "<p>暂无持仓逻辑配置。</p>"
    rows = []
    for symbol, item in thesis_reviews.items():
        instrument = item.get("instrument") or {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(instrument.get('name') or ''))}</td>"
            f"<td>{escape(str(symbol))}</td>"
            f"<td>{escape(str(item.get('status') or ''))}</td>"
            f"<td>{escape(str(instrument.get('thesis') or ''))}</td>"
            f"<td>{escape(str(instrument.get('invalidation') or ''))}</td>"
            f"<td>{escape(str(item.get('note') or ''))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>名称</th><th>代码</th><th>状态</th><th>持仓逻辑</th><th>失效条件</th><th>复核说明</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _audit_panel(report_audit: dict) -> str:
    if not report_audit:
        return "<p>暂无报告质检结果。</p>"
    items = report_audit.get("items") or []
    lines = [
        f"<p>状态：<strong>{escape(str(report_audit.get('status') or 'N/A'))}</strong>；问题数：{len(items)}</p>"
    ]
    if items:
        lines.append("<ul>")
        for item in items:
            lines.append(
                f"<li>[{escape(str(item.get('level') or ''))}] {escape(str(item.get('rule_id') or ''))}：{escape(str(item.get('message') or ''))}</li>"
            )
        lines.append("</ul>")
    return "".join(lines)


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

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportAuditItem:
    rule_id: str
    level: str
    message: str


@dataclass(frozen=True)
class ReportAuditResult:
    context: str
    status: str
    items: tuple[ReportAuditItem, ...]

    @property
    def issue_count(self) -> int:
        return len(self.items)


FORBIDDEN_COMMANDS = (
    "保证收益",
    "稳赚",
    "无风险",
    "必须买入",
    "立即买入",
    "满仓",
    "梭哈",
    "卖出全部",
    "清仓",
)

DISCLAIMER_MARKERS = (
    "免责声明",
    "不构成保证收益",
    "不构成个人投顾建议",
    "个人投顾建议",
)


def audit_report(markdown: str, context: str) -> ReportAuditResult:
    items: list[ReportAuditItem] = []
    compact = markdown.replace(" ", "")
    command_text = _strip_safe_context(compact)
    if any(keyword in command_text for keyword in FORBIDDEN_COMMANDS):
        items.append(
            ReportAuditItem(
                rule_id="forbidden_command",
                level="high",
                message="报告出现过强交易指令或收益承诺表述，需改为观察、风险提示和人工确认口径。",
            )
        )
    if not _has_disclaimer(markdown):
        items.append(
            ReportAuditItem(
                rule_id="missing_disclaimer",
                level="high",
                message="报告缺少免责声明或不构成投顾建议的表述。",
            )
        )
    if "风险" not in markdown:
        items.append(
            ReportAuditItem(
                rule_id="missing_risk_context",
                level="medium",
                message="报告缺少风险提示，建议补充信号失效、仓位或数据风险。",
            )
        )
    status = "通过" if not items else "需要复核"
    return ReportAuditResult(context=context, status=status, items=tuple(items))


def render_audit_summary(result: ReportAuditResult | None) -> str:
    if result is None:
        return ""
    lines = [
        "## 报告质检",
        f"- 状态：{result.status}；问题数：{result.issue_count}",
        "- 说明：仅为规则审计，用于发现过强交易措辞、缺少风险提示或免责声明等问题。",
    ]
    if result.items:
        for item in result.items:
            lines.append(f"- [{item.level}] {item.rule_id}：{item.message}")
    else:
        lines.append("- 未发现明显合规措辞问题。")
    return "\n".join(lines)


def _has_disclaimer(markdown: str) -> bool:
    marker_count = sum(1 for marker in DISCLAIMER_MARKERS if marker in markdown)
    return marker_count >= 2 or ("免责声明" in markdown and "投顾" in markdown)


def _strip_safe_context(text: str) -> str:
    safe_phrases = (
        "不构成保证收益",
        "不保证收益",
        "不是保证收益",
        "不承诺收益",
        "不构成买入指令",
        "不构成卖出指令",
    )
    for phrase in safe_phrases:
        text = text.replace(phrase, "")
    return text

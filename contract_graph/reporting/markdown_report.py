"""Markdown report output for contract-graph findings."""

from __future__ import annotations

from contract_graph.graph.model import Finding, Severity
from contract_graph.scoring.scorer import ScoreResult


_SEVERITY_EMOJI = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🔵",
    Severity.INFO: "⚪",
}


def generate_markdown_report(
    findings: list[Finding],
    score: ScoreResult,
    node_count: int = 0,
    edge_count: int = 0,
) -> str:
    """Generate a Markdown string summarizing contract-graph findings."""
    lines: list[str] = []
    lines.append("# Contract Graph Report\n")

    # Summary
    grade = _score_grade(score.total_score)
    lines.append(f"**Health Score:** {score.total_score:.0f}/100 ({grade})\n")
    lines.append(f"**Nodes:** {node_count} | **Edges:** {edge_count} | **Findings:** {len(findings)}\n")

    if not findings:
        lines.append("\n✅ No contract drift detected.\n")
        return "\n".join(lines)

    # Severity breakdown
    lines.append("\n## Severity Breakdown\n")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    severity_counts: dict[Severity, int] = {}
    for f in findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
    for sev in Severity:
        count = severity_counts.get(sev, 0)
        if count > 0:
            lines.append(f"| {_SEVERITY_EMOJI.get(sev, '')} {sev.value.upper()} | {count} |")

    # Findings detail
    lines.append("\n## Findings\n")
    for i, f in enumerate(findings, 1):
        emoji = _SEVERITY_EMOJI.get(f.severity, "")
        lines.append(f"### {i}. {emoji} {f.title}\n")
        lines.append(f"- **Severity:** {f.severity.value}")
        lines.append(f"- **Discoverer:** {f.discoverer}")
        if f.file_path:
            lines.append(f"- **File:** `{f.file_path}`")
        if f.description:
            lines.append(f"- **Description:** {f.description}")
        if f.mismatches:
            lines.append("\n| Field | Mismatch | Provider | Consumer |")
            lines.append("|-------|----------|----------|----------|")
            for m in f.mismatches:
                lines.append(
                    f"| `{m.field_name}` | {m.kind.value} | "
                    f"{m.provider_value or '-'} | {m.consumer_value or '-'} |"
                )
        lines.append("")

    # Score per discoverer
    if score.per_discoverer:
        lines.append("\n## Scores by Discoverer\n")
        lines.append("| Discoverer | Score |")
        lines.append("|------------|-------|")
        for disc, s in score.per_discoverer.items():
            lines.append(f"| {disc} | {s:.0f}/100 |")

    return "\n".join(lines)


def write_markdown_report(
    findings: list[Finding],
    score: ScoreResult,
    output_path: str,
    node_count: int = 0,
    edge_count: int = 0,
) -> None:
    """Write markdown report to file."""
    from pathlib import Path

    content = generate_markdown_report(findings, score, node_count, edge_count)
    Path(output_path).write_text(content, encoding="utf-8")


def _score_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"

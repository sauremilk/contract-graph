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
    grade = _score_grade(score.overall_score)
    lines.append(f"**Health Score:** {score.overall_score:.1%} ({grade})\n")
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
        if f.provider_file:
            lines.append(f"- **Provider:** `{f.provider_file}`")
        if f.consumer_file:
            lines.append(f"- **Consumer:** `{f.consumer_file}`")
        if f.description:
            lines.append(f"- **Description:** {f.description}")
        if f.field_name:
            lines.append(f"- **Field:** `{f.field_name}` (mismatch: {f.mismatch_kind})")
        if f.fix_suggestion:
            lines.append(f"- **Fix:** {f.fix_suggestion}")
        lines.append("")

    # Score per discoverer
    if score.discoverer_scores:
        lines.append("\n## Scores by Discoverer\n")
        lines.append("| Discoverer | Score |")
        lines.append("|------------|-------|")
        for disc, s in score.discoverer_scores.items():
            lines.append(f"| {disc} | {s:.1%} |")

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
    """Convert a 0.0-1.0 score to a letter grade."""
    if score >= 0.9:
        return "A"
    if score >= 0.8:
        return "B"
    if score >= 0.7:
        return "C"
    if score >= 0.6:
        return "D"
    return "F"

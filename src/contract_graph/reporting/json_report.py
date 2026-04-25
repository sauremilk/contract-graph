"""JSON report generator."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contract_graph import SCHEMA_VERSION, __version__
from contract_graph.graph.model import ContractGraph, Finding, Severity
from contract_graph.scoring.scorer import ScoreResult


def generate_json_report(
    graph: ContractGraph,
    findings: list[Finding],
    score: ScoreResult,
    repo_path: str = ".",
    duration: float = 0.0,
) -> dict[str, Any]:
    """Generate a structured JSON report conforming to output_schema.json."""
    # Count findings by severity
    by_severity: dict[str, int] = {s.value: 0 for s in Severity}
    for f in findings:
        by_severity[f.severity.value] += 1

    return {
        "tool": "contract-graph",
        "version": __version__,
        "schema_version": SCHEMA_VERSION,
        "findings": [f.to_dict() for f in findings],
        "summary": {
            "total_findings": len(findings),
            "by_severity": by_severity,
            "score": {
                "overall": score.overall_score,
                "grade": _score_grade(score.overall_score),
            },
            "analyzed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": round(duration, 2),
        },
        "contract_graph": {
            "nodes": graph.node_count,
            "edges": graph.edge_count,
        },
    }


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


def write_json_report(report: dict[str, Any], output_path: Path | str) -> None:
    """Write a JSON report to file."""
    path = Path(output_path)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

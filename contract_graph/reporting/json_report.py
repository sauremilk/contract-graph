"""JSON report generator."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contract_graph.graph.model import ContractGraph, Finding
from contract_graph.scoring.scorer import ScoreResult


def generate_json_report(
    graph: ContractGraph,
    findings: list[Finding],
    score: ScoreResult,
    repo_path: str = ".",
    duration: float = 0.0,
) -> dict[str, Any]:
    """Generate a structured JSON report."""
    return {
        "version": "1.0",
        "analyzed_at": datetime.now(UTC).isoformat(),
        "repo_path": repo_path,
        "duration_seconds": round(duration, 2),
        "summary": {
            "total_nodes": graph.node_count,
            "total_edges": graph.edge_count,
            **score.to_dict(),
        },
        **graph.to_dict(),
        "findings": [f.to_dict() for f in findings],
    }


def write_json_report(report: dict[str, Any], output_path: Path | str) -> None:
    """Write a JSON report to file."""
    path = Path(output_path)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

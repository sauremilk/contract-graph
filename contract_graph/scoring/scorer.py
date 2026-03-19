"""Weighted severity scorer — aggregates findings into an overall health score."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contract_graph.graph.model import Finding, Severity

# ── Severity weights for score calculation ─────────────────────────

_SEVERITY_PENALTY: dict[Severity, float] = {
    Severity.CRITICAL: 1.0,
    Severity.HIGH: 0.7,
    Severity.MEDIUM: 0.4,
    Severity.LOW: 0.15,
    Severity.INFO: 0.0,
}


@dataclass
class ScoreResult:
    """Result of scoring a set of findings."""

    overall_score: float  # 0.0 (terrible) to 1.0 (perfect)
    findings_by_severity: dict[str, int]
    total_findings: int
    discoverer_scores: dict[str, float]
    weighted_penalty: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 3),
            "findings_by_severity": self.findings_by_severity,
            "total_findings": self.total_findings,
            "discoverer_scores": {k: round(v, 3) for k, v in self.discoverer_scores.items()},
            "weighted_penalty": round(self.weighted_penalty, 3),
        }


def score_findings(
    findings: list[Finding],
    weights: dict[str, float] | None = None,
    max_penalty: float = 50.0,
) -> ScoreResult:
    """Score a list of findings into an overall health score.

    Args:
        findings: List of findings from policy evaluation.
        weights: Discoverer name -> weight (0.0-1.0). Default: equal weight.
        max_penalty: Maximum total penalty before score reaches 0.

    Returns:
        ScoreResult with overall score and breakdown.
    """
    if not findings:
        return ScoreResult(
            overall_score=1.0,
            findings_by_severity={s.value: 0 for s in Severity},
            total_findings=0,
            discoverer_scores={},
            weighted_penalty=0.0,
        )

    weights = weights or {}

    # Count by severity
    by_severity: dict[str, int] = {s.value: 0 for s in Severity}
    for f in findings:
        by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1

    # Group by discoverer
    by_discoverer: dict[str, list[Finding]] = {}
    for f in findings:
        by_discoverer.setdefault(f.discoverer, []).append(f)

    # Calculate weighted penalty
    total_penalty = 0.0
    discoverer_scores: dict[str, float] = {}

    for disc, disc_findings in by_discoverer.items():
        weight = weights.get(disc, 1.0 / max(len(by_discoverer), 1))
        disc_penalty = sum(_SEVERITY_PENALTY.get(f.severity, 0) for f in disc_findings)
        weighted = disc_penalty * weight
        total_penalty += weighted
        # Per-discoverer score: 1.0 minus normalized penalty
        discoverer_scores[disc] = max(0.0, 1.0 - (disc_penalty / max(len(disc_findings) * 1.0, 1)))

    # Overall score: 1.0 minus normalized total penalty
    overall = max(0.0, 1.0 - (total_penalty / max_penalty))

    return ScoreResult(
        overall_score=overall,
        findings_by_severity=by_severity,
        total_findings=len(findings),
        discoverer_scores=discoverer_scores,
        weighted_penalty=total_penalty,
    )

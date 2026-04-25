"""Mapping layer: contract-graph JSON findings → drift Finding objects.

This module is the semantic core of the adapter.  It is intentionally
isolated so it can be unit-tested without a running subprocess or real
filesystem — all inputs are plain dicts.

Complexity: O(n) where n = number of contract-graph findings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ── Severity mapping ───────────────────────────────────────────────────────
# contract-graph severity values are identical to drift's StrEnum values,
# so we can pass them through after lower-casing.
# Fallback: treat unknown values as "medium" to avoid silent data loss.

_SEVERITY_SCORE: dict[str, float] = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
    "info": 0.0,
}

_FALLBACK_SEVERITY = "medium"
_FALLBACK_SCORE = 0.5

# Signal type string used for all contract-graph findings in drift.
# Using an arbitrary string (not a core SignalType enum) is correct per
# drift's Finding contract — plugin signals are free-form strings.
CONTRACT_GRAPH_SIGNAL_TYPE = "contract_graph_drift"


def map_finding(raw: dict[str, Any]) -> Any:  # Returns drift.models.Finding
    """Map a single contract-graph finding dict to a drift Finding.

    Parameters
    ----------
    raw:
        A dict as produced by ``contract_graph.graph.model.Finding.to_dict()``.
        Required keys: ``discoverer``, ``severity``, ``title``.
        All other keys are optional and fall back to empty/zero.

    Returns
    -------
    drift.models.Finding
        A fully populated drift Finding ready for inclusion in a RepoAnalysis.

    Raises
    ------
    ImportError
        If drift is not installed.  Callers should handle this and degrade gracefully.
    """
    from drift.models import Finding
    from drift.models._enums import Severity

    severity_raw = str(raw.get("severity", _FALLBACK_SEVERITY)).lower()
    if severity_raw not in _SEVERITY_SCORE:
        severity_raw = _FALLBACK_SEVERITY

    severity = Severity(severity_raw)
    score = _SEVERITY_SCORE[severity_raw]

    consumer_file_raw = raw.get("consumer_file") or raw.get("provider_file") or ""
    file_path = Path(consumer_file_raw) if consumer_file_raw else None

    start_line_raw = raw.get("consumer_line") or raw.get("provider_line") or None
    start_line = int(start_line_raw) if start_line_raw else None

    # Preserve the full contract-graph payload in metadata so downstream
    # drift reporters can render provider/consumer context without re-parsing.
    metadata: dict[str, Any] = {
        "contract_graph": {
            "finding_id": raw.get("finding_id", ""),
            "discoverer": raw.get("discoverer", ""),
            "provider_file": raw.get("provider_file", ""),
            "provider_name": raw.get("provider_name", ""),
            "provider_line": raw.get("provider_line", 0),
            "consumer_file": raw.get("consumer_file", ""),
            "consumer_name": raw.get("consumer_name", ""),
            "consumer_line": raw.get("consumer_line", 0),
            "field_name": raw.get("field_name", ""),
            "mismatch_kind": raw.get("mismatch_kind", ""),
        }
    }

    return Finding(
        signal_type=CONTRACT_GRAPH_SIGNAL_TYPE,
        severity=severity,
        score=score,
        title=str(raw.get("title", "Contract drift detected")),
        description=str(raw.get("description", "")),
        file_path=file_path,
        start_line=start_line,
        fix=str(raw.get("fix_suggestion", "")) or None,
        root_cause=str(raw.get("mismatch_kind", "")) or None,
        metadata=metadata,
    )


def map_findings(report: dict[str, Any]) -> list[Any]:
    """Map all findings from a contract-graph JSON report to drift Findings.

    Parameters
    ----------
    report:
        Parsed JSON report as returned by ``contract-graph analyze --format json``.
        Must contain a ``findings`` list; all other fields are optional.

    Returns
    -------
    list[drift.models.Finding]
        Mapped findings.  Malformed individual entries are skipped with a
        warning rather than aborting — partial data beats no data.
    """
    import logging

    logger = logging.getLogger(__name__)

    raw_findings = report.get("findings", [])
    if not isinstance(raw_findings, list):
        logger.warning("contract-graph report: 'findings' is not a list — skipping")
        return []

    results = []
    for i, raw in enumerate(raw_findings):
        if not isinstance(raw, dict):
            logger.warning("contract-graph finding[%d] is not a dict — skipping", i)
            continue
        try:
            results.append(map_finding(raw))
        except Exception as exc:  # noqa: BLE001
            logger.warning("contract-graph finding[%d] mapping failed: %s", i, exc)
    return results

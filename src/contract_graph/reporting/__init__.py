"""Reporting package."""

from contract_graph.graph.model import Severity

# Canonical emoji icons for each severity level.
# Single source of truth — imported by all report modules.
SEVERITY_EMOJI: dict[Severity, str] = {
    Severity.CRITICAL: "\U0001f534",
    Severity.HIGH: "\U0001f7e0",
    Severity.MEDIUM: "\U0001f7e1",
    Severity.LOW: "\U0001f535",
    Severity.INFO: "\u26aa",
}

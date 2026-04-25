"""ContractGraphAdapter — drift IntegrationAdapter for contract-graph.

Adapter tier: ``run``
  - Invokes ``contract-graph analyze {repo_path} --format json`` as a subprocess.
  - Parses stdout JSON via drift's tolerant parser (handles trailing Rich output).
  - Maps each finding to a drift Finding via ``drift_contract_graph.mapping``.

Subprocess contract:
  - exit 0: success (no findings above threshold)
  - exit 1: findings found above threshold  ← both are valid; we parse stdout
  - exit 2: config / invocation error        ← we log and return empty
  - exit 127: binary not found              ← is_available() returns False

O(n) finding mapping; O(1) subprocess overhead per analysis run.
"""

from __future__ import annotations

import json
import logging
import shutil
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from drift.integrations.base import IntegrationContext, IntegrationResult

try:
    from drift.integrations.runner import run_command  # noqa: F401 — imported for monkeypatching
except ImportError:
    run_command = None  # type: ignore[assignment]  # drift not installed; is_available() guards this path

logger = logging.getLogger(__name__)

_BINARY = "contract-graph"
_SIGNAL_TYPE = "contract_graph_drift"

# Findings are surfaced for these drift signals because contract drift and
# system-level misalignment are closely coupled.
_TRIGGER_SIGNALS = [
    "doc_impl_drift",
    "system_misalignment",
    "architecture_violation",
]


class ContractGraphAdapter:
    """drift integration adapter that invokes contract-graph as a subprocess.

    The adapter is intentionally thin — it delegates all analysis logic to
    contract-graph and only handles the subprocess invocation + JSON mapping.
    This keeps the adapter testable without a running analysis pipeline.
    """

    name: str = "contract-graph"
    tier: Literal["run"] = "run"
    enabled: bool = True
    trigger_signals: list[str] = _TRIGGER_SIGNALS

    def is_available(self) -> bool:
        """Return True when the ``contract-graph`` binary is on PATH."""
        return shutil.which(_BINARY) is not None

    def run(self, ctx: IntegrationContext) -> IntegrationResult:
        """Invoke contract-graph and map its output to drift Findings.

        Errors (non-zero exit, timeout, JSON parse failure) degrade
        gracefully: an IntegrationResult with ``summary`` describing the
        failure is returned rather than raising an exception.
        """
        from drift.integrations.base import IntegrationResult

        # Use module-level import so tests can monkeypatch drift_contract_graph.adapter.run_command.
        import drift_contract_graph.adapter as _self_module
        from drift_contract_graph.mapping import map_findings

        _run_command = _self_module.run_command

        repo_posix = ctx.repo_path.as_posix()
        command = [_BINARY, "analyze", repo_posix, "--format", "json"]

        sub = _run_command(
            command,
            repo_path=ctx.repo_path,
            timeout_seconds=getattr(ctx, "timeout_seconds", 60),
        )

        # exit 2 = config error — log and surface as summary, not findings.
        if sub.exit_code == 2:
            logger.warning(
                "contract-graph exited with code 2 (config error). stderr: %s",
                sub.stderr[:500],
            )
            return IntegrationResult(
                source=self.name,
                summary=(
                    f"contract-graph: configuration error (exit 2). "
                    f"Run `{_BINARY} analyze --help` for usage."
                ),
                raw_output=sub.stderr,
            )

        if sub.exit_code == 127 or sub.timed_out:
            return IntegrationResult(
                source=self.name,
                summary=(
                    f"contract-graph: invocation failed "
                    f"(exit {sub.exit_code}, timed_out={sub.timed_out})."
                ),
                raw_output=sub.stderr,
            )

        # exit 0 = clean, exit 1 = findings present — both yield parseable stdout.
        report = _parse_json_tolerant(sub.stdout)
        if report is None:
            logger.warning(
                "contract-graph: could not parse JSON from stdout (first 200 chars): %s",
                sub.stdout[:200],
            )
            return IntegrationResult(
                source=self.name,
                summary="contract-graph: JSON parse failed — check tool output.",
                raw_output=sub.stdout,
            )

        findings = map_findings(report)

        schema_version = report.get("schema_version", "unknown")
        cg_nodes = report.get("contract_graph", {}).get("nodes", "?")
        cg_edges = report.get("contract_graph", {}).get("edges", "?")

        return IntegrationResult(
            source=self.name,
            findings=findings,
            raw_output=sub.stdout,
            summary=(
                f"contract-graph {report.get('version', '?')} "
                f"(schema {schema_version}): "
                f"{len(findings)} finding(s) across {cg_nodes} nodes / {cg_edges} edges."
            ),
            metadata={
                "schema_version": schema_version,
                "contract_graph_version": report.get("version", ""),
                "nodes": cg_nodes,
                "edges": cg_edges,
            },
        )


def _parse_json_tolerant(stdout: str) -> dict | None:
    """Parse JSON from stdout, tolerating trailing Rich/console text.

    contract-graph may emit terminal decorations after the JSON payload when
    invoked without ``--no-color``.  We extract content from the first ``{``
    to the last ``}`` to strip such noise.
    """
    if not stdout:
        return None
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None

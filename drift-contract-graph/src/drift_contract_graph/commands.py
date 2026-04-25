"""``drift contracts`` CLI subcommand group.

Registered via the ``drift.commands`` entry-point so ``drift`` discovers it
automatically.  No modification to the drift codebase required.

Usage:
    drift contracts analyze [OPTIONS] [REPO_PATH]
    drift contracts check   [OPTIONS] [REPO_PATH]

Exit codes (match contract-graph and drift conventions):
    0 — success / no findings above threshold
    1 — findings found above threshold
    2 — config or invocation error
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

# ── Entry-point symbol expected by drift.plugins.discover_command_plugins() ──


@click.group("contracts")
def contracts_command() -> None:
    """Cross-boundary contract drift analysis via contract-graph."""


# ── Sub-commands ──────────────────────────────────────────────────────────────


@contracts_command.command("analyze")
@click.argument(
    "repo_path", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--format",
    "output_format",
    default="terminal",
    type=click.Choice(["terminal", "json", "markdown"]),
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Write report to file instead of stdout.",
)
@click.option(
    "--config",
    "-c",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to contract-graph YAML config.",
)
def analyze_cmd(
    repo_path: Path, output_format: str, output: Path | None, config: Path | None
) -> None:
    """Run full contract analysis and print findings.

    REPO_PATH defaults to the current directory.
    """
    _require_binary()
    cmd = _build_command("analyze", repo_path, output_format, config)
    result = subprocess.run(cmd, capture_output=False, text=True)  # noqa: S603
    if output and output_format == "json":
        # Re-run capturing stdout so we can write to file.
        result2 = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
        output.write_text(result2.stdout, encoding="utf-8")
        click.echo(f"Report written to {output}", err=True)
    sys.exit(result.returncode)


@contracts_command.command("check")
@click.argument(
    "repo_path", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--fail-on",
    default="high",
    type=click.Choice(["critical", "high", "medium", "low", "info"]),
    show_default=True,
    help="Minimum severity that causes a non-zero exit.",
)
@click.option(
    "--config",
    "-c",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to contract-graph YAML config.",
)
def check_cmd(repo_path: Path, fail_on: str, config: Path | None) -> None:
    """CI gate — exit 1 if findings at or above FAIL_ON severity exist.

    Exit codes: 0 = clean, 1 = violations found, 2 = config error.
    """
    _require_binary()
    cmd = ["contract-graph", "check", str(repo_path), "--fail-on", fail_on]
    if config:
        cmd += ["--config", str(config)]
    result = subprocess.run(cmd, capture_output=False, text=True)  # noqa: S603
    sys.exit(result.returncode)


@contracts_command.command("show-mapping")
@click.argument(
    "repo_path", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
def show_mapping_cmd(repo_path: Path) -> None:
    """Show how contract-graph findings map to drift Finding fields.

    Runs a dry analysis and pretty-prints the drift Finding representation
    for each contract-graph finding.  Useful for debugging the mapping.
    """
    _require_binary()
    from drift_contract_graph.adapter import _parse_json_tolerant
    from drift_contract_graph.mapping import map_findings

    cmd = ["contract-graph", "analyze", str(repo_path), "--format", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    report = _parse_json_tolerant(proc.stdout)
    if report is None:
        click.echo("contract-graph produced no parseable JSON output.", err=True)
        sys.exit(2)

    try:
        findings = map_findings(report)
    except ImportError:
        click.echo("drift is not installed — cannot map findings.", err=True)
        sys.exit(2)

    if not findings:
        click.echo("No findings.")
        return

    for f in findings:
        meta = f.metadata.get("contract_graph", {})
        click.echo(
            json.dumps(
                {
                    "signal_type": f.signal_type,
                    "severity": f.severity.value,
                    "score": f.score,
                    "title": f.title,
                    "file_path": str(f.file_path) if f.file_path else None,
                    "start_line": f.start_line,
                    "fix": f.fix,
                    "root_cause": f.root_cause,
                    "contract_graph_meta": meta,
                },
                indent=2,
            )
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_binary() -> None:
    """Abort with a helpful message if contract-graph is not on PATH."""
    if not shutil.which("contract-graph"):
        click.echo(
            "contract-graph: binary not found on PATH.\n"
            "Install it with: pip install contract-graph",
            err=True,
        )
        sys.exit(2)


def _build_command(
    subcommand: str,
    repo_path: Path,
    output_format: str,
    config: Path | None,
) -> list[str]:
    cmd = ["contract-graph", subcommand, str(repo_path), "--format", output_format]
    if config:
        cmd += ["--config", str(config)]
    return cmd

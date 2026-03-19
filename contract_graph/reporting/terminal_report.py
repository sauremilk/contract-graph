"""Rich terminal report generator."""

from __future__ import annotations

from contract_graph.graph.model import Finding, Severity
from contract_graph.reporting import SEVERITY_EMOJI
from contract_graph.scoring.scorer import ScoreResult

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


_SEVERITY_COLORS = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "blue",
    Severity.INFO: "dim",
}


def print_terminal_report(
    findings: list[Finding],
    score: ScoreResult,
    node_count: int = 0,
    edge_count: int = 0,
) -> None:
    """Print a rich terminal report of contract analysis results."""
    if not HAS_RICH:
        _print_plain(findings, score)
        return

    console = Console()

    # Header
    score_color = "green" if score.overall_score >= 0.8 else "yellow" if score.overall_score >= 0.5 else "red"
    console.print(
        Panel(
            f"[bold]Contract Health Score: [{score_color}]{score.overall_score:.1%}[/{score_color}][/bold]\n"
            f"Nodes: {node_count} | Edges: {edge_count} | Findings: {score.total_findings}",
            title="[bold blue]contract-graph[/bold blue]",
            border_style="blue",
        )
    )

    # Severity summary
    summary = Table(show_header=False, box=None, padding=(0, 2))
    for sev in [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
        Severity.INFO,
    ]:
        count = score.findings_by_severity.get(sev.value, 0)
        if count > 0:
            icon = SEVERITY_EMOJI[sev]
            color = _SEVERITY_COLORS[sev]
            summary.add_row(f"{icon} {sev.value.upper()}", f"[{color}]{count}[/{color}]")
    console.print(summary)
    console.print()

    if not findings:
        console.print("[green]✅ No contract violations found![/green]")
        return

    # Findings table
    table = Table(title="Contract Findings", show_lines=True)
    table.add_column("Severity", width=10)
    table.add_column("Title", min_width=30)
    table.add_column("Location", min_width=25)
    table.add_column("Fix", min_width=20)

    for f in sorted(findings, key=lambda x: list(Severity).index(x.severity)):
        icon = SEVERITY_EMOJI.get(f.severity, "")
        color = _SEVERITY_COLORS.get(f.severity, "")
        location = ""
        if f.provider_file and f.consumer_file:
            location = f"{_short(f.provider_file)} → {_short(f.consumer_file)}"
        elif f.consumer_file:
            location = _short(f.consumer_file)
        elif f.provider_file:
            location = _short(f.provider_file)

        table.add_row(
            f"[{color}]{icon} {f.severity.value}[/{color}]",
            f"[{color}]{f.title}[/{color}]",
            location,
            f.fix_suggestion or "",
        )

    console.print(table)


def _short(path: str, max_len: int = 40) -> str:
    """Shorten a path for display."""
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3) :]


def _print_plain(findings: list[Finding], score: ScoreResult) -> None:
    """Fallback plain-text output without rich."""
    print(f"\n=== Contract Health: {score.overall_score:.1%} ===")
    print(f"Total findings: {score.total_findings}")
    for sev, count in score.findings_by_severity.items():
        if count > 0:
            print(f"  {sev}: {count}")
    print()
    for f in findings:
        print(f"[{f.severity.value.upper()}] {f.title}")
        if f.description:
            print(f"  {f.description}")
        if f.fix_suggestion:
            print(f"  Fix: {f.fix_suggestion}")
    print()

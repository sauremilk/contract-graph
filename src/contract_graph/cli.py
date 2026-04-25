"""CLI for contract-graph — analyze, check, impact, init."""

from __future__ import annotations

import json
import sys
import time
from importlib import import_module
from pathlib import Path

import click
import yaml

from contract_graph.config import ConfigError, ContractGraphConfig, generate_default_config, load_config
from contract_graph.discovery.base import DiscovererRegistry
from contract_graph.graph.builder import GraphBuilder
from contract_graph.graph.impact import analyze_impact
from contract_graph.graph.model import ContractGraph
from contract_graph.policy.engine import PolicyEngine
from contract_graph.reporting.json_report import generate_json_report, write_json_report
from contract_graph.reporting.terminal_report import print_terminal_report
from contract_graph.scoring.scorer import score_findings

# Importing these packages triggers their __init__, which auto-registers built-in
# discoverers and policy rules via the @DiscovererRegistry.register / @register_rule decorators.
import_module("contract_graph.discovery")
import_module("contract_graph.policy")


def _run_analysis(config: ContractGraphConfig, root: str) -> tuple[ContractGraph, float]:
    """Core analysis pipeline: parse → discover → build graph."""
    start = time.time()
    builder = GraphBuilder()

    # Run each enabled discoverer
    discovery_dict = config.discovery.model_dump()
    for disc_name, disc_config in discovery_dict.items():
        if not isinstance(disc_config, dict):
            continue
        if not disc_config.get("enabled", False):
            continue

        discoverer = DiscovererRegistry.create(disc_name)
        if discoverer is None:
            continue

        nodes, edges = discoverer.discover(builder.build(), disc_config, root)
        builder.merge_nodes(nodes)
        builder.merge_edges(edges)

    duration = time.time() - start
    return builder.build(), duration


@click.group()
@click.version_option(version="0.1.0", prog_name="contract-graph")
def main() -> None:
    """contract-graph — Cross-boundary contract intelligence."""


@main.command()
@click.option("--config", "config_path", default=None, help="Path to contract-graph.yaml")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "terminal", "both"]),
    default="terminal",
)
@click.option("--output", "output_path", default=None, help="Output file path (for JSON)")
@click.option("--root", default=".", help="Project root directory")
@click.option(
    "--enable-discoverers",
    multiple=True,
    help="Enable specific discoverers (e.g. --enable-discoverers config_usage --enable-discoverers route_activation)",
)
def analyze(
    config_path: str | None, fmt: str, output_path: str | None, root: str, enable_discoverers: tuple[str, ...]
) -> None:
    """Run full contract analysis."""
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"\u274c Config error: {exc}", err=True)
        sys.exit(2)

    # Override discoverer enablement if CLI flags provided
    if enable_discoverers:
        # Disable all discoverers first
        config.discovery.api_type_sync.enabled = False
        config.discovery.config_usage.enabled = False
        config.discovery.route_activation.enabled = False

        # Enable specified ones
        for disc_name in enable_discoverers:
            if disc_name == "api_type_sync":
                config.discovery.api_type_sync.enabled = True
            elif disc_name == "config_usage":
                config.discovery.config_usage.enabled = True
            elif disc_name == "route_activation":
                config.discovery.route_activation.enabled = True
            else:
                click.echo(f"⚠️  Unknown discoverer: {disc_name}", err=True)

    graph, duration = _run_analysis(config, root)

    # Evaluate policies
    engine = PolicyEngine(config.model_dump())
    findings = engine.evaluate(graph)

    # Score
    weights = config.scoring.weights.model_dump()
    score = score_findings(findings, weights)

    # Output
    if fmt in ("terminal", "both"):
        print_terminal_report(findings, score, graph.node_count, graph.edge_count)

    if fmt in ("json", "both"):
        report = generate_json_report(graph, findings, score, root, duration)
        if output_path:
            write_json_report(report, output_path)
            click.echo(f"Report written to {output_path}")
        else:
            click.echo(json.dumps(report, indent=2, default=str))


@main.command()
@click.option("--config", "config_path", default=None, help="Path to contract-graph.yaml")
@click.option(
    "--fail-on",
    default="high",
    type=click.Choice(["critical", "high", "medium", "low"]),
)
@click.option("--root", default=".", help="Project root directory")
def check(config_path: str | None, fail_on: str, root: str) -> None:
    """CI gate check — exit 1 if findings exceed threshold."""
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"\u274c Config error: {exc}", err=True)
        sys.exit(2)
    graph, _ = _run_analysis(config, root)

    engine = PolicyEngine(config.model_dump())
    passed, findings = engine.evaluate_gate(graph, fail_on)

    weights = config.scoring.weights.model_dump()
    score = score_findings(findings, weights)

    print_terminal_report(findings, score, graph.node_count, graph.edge_count)

    if not passed:
        blocking = [f for f in findings if f.severity.value in _severities_at_or_above(fail_on)]
        click.echo(f"\n❌ Gate FAILED: {len(blocking)} finding(s) at or above '{fail_on}' severity.")
        sys.exit(1)
    else:
        click.echo(f"\n✅ Gate PASSED: no findings at or above '{fail_on}' severity.")


@main.command()
@click.argument("file_path")
@click.option("--config", "config_path", default=None, help="Path to contract-graph.yaml")
@click.option("--depth", default=-1, help="Max traversal depth (-1 = unlimited)")
@click.option("--root", default=".", help="Project root directory")
def impact(file_path: str, config_path: str | None, depth: int, root: str) -> None:
    """Analyze change impact for a file."""
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"\u274c Config error: {exc}", err=True)
        sys.exit(2)
    graph, _ = _run_analysis(config, root)

    result = analyze_impact(graph, file_path, depth)
    click.echo(json.dumps(result.to_dict(), indent=2))


@main.command()
@click.option(
    "--preset",
    type=click.Choice(["fullstack", "backend-only", "agent-system"]),
    default="fullstack",
)
@click.option("--output", "output_path", default="contract-graph.yaml")
def init(preset: str, output_path: str) -> None:
    """Generate a contract-graph.yaml config template."""
    config = generate_default_config(preset)
    output = Path(output_path)

    if output.exists():
        click.confirm(f"{output} already exists. Overwrite?", abort=True)

    output.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")
    click.echo(f"✅ Config written to {output} (preset: {preset})")


def _severities_at_or_above(level: str) -> set[str]:
    """Return severity names at or above the given level."""
    order = ["critical", "high", "medium", "low", "info"]
    try:
        idx = order.index(level)
    except ValueError:
        idx = 1  # default to high
    return set(order[: idx + 1])


if __name__ == "__main__":
    main()

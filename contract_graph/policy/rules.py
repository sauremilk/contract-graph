"""Built-in policy rules."""

from __future__ import annotations

from typing import Any

from contract_graph.graph.model import (
    ContractGraph,
    EdgeKind,
    Finding,
    MismatchKind,
    Severity,
)
from contract_graph.policy.engine import register_rule


@register_rule
def no_missing_consumer_fields(graph: ContractGraph, config: dict[str, Any]) -> list[Finding]:
    """Provider fields must exist in consumer (with compatible types)."""
    findings: list[Finding] = []
    for edge in graph.edges:
        if edge.kind != EdgeKind.API_TYPE_SYNC:
            continue
        for mm in edge.mismatches:
            if mm.mismatch_kind == MismatchKind.MISSING_IN_CONSUMER:
                src = graph.get_node(edge.source)
                tgt = graph.get_node(edge.target)
                findings.append(
                    Finding(
                        discoverer="rule:no_missing_consumer_fields",
                        severity=Severity.MEDIUM,
                        title=f"Missing field '{mm.field_name}' in consumer",
                        description=(
                            f"Provider '{src.name if src else edge.source}' has field "
                            f"'{mm.field_name}' (type: {mm.provider_type}) "
                            f"but consumer '{tgt.name if tgt else edge.target}' does not."
                        ),
                        provider_file=str(src.file_path) if src else "",
                        provider_name=src.name if src else "",
                        consumer_file=str(tgt.file_path) if tgt else "",
                        consumer_name=tgt.name if tgt else "",
                        field_name=mm.field_name,
                        mismatch_kind=mm.mismatch_kind.value,
                        fix_suggestion=f"Add '{mm.field_name}: {mm.provider_type}' to the consumer type.",
                    )
                )
    return findings


@register_rule
def no_type_incompatibility(graph: ContractGraph, config: dict[str, Any]) -> list[Finding]:
    """Provider and consumer field types must be compatible."""
    findings: list[Finding] = []
    for edge in graph.edges:
        if edge.kind != EdgeKind.API_TYPE_SYNC:
            continue
        for mm in edge.mismatches:
            if mm.mismatch_kind == MismatchKind.TYPE_INCOMPATIBLE:
                src = graph.get_node(edge.source)
                tgt = graph.get_node(edge.target)
                findings.append(
                    Finding(
                        discoverer="rule:no_type_incompatibility",
                        severity=Severity.HIGH,
                        title=f"Type mismatch: {mm.field_name}",
                        description=(
                            f"Provider type '{mm.provider_type}' is incompatible "
                            f"with consumer type '{mm.consumer_type}'."
                        ),
                        provider_file=str(src.file_path) if src else "",
                        provider_name=src.name if src else "",
                        consumer_file=str(tgt.file_path) if tgt else "",
                        consumer_name=tgt.name if tgt else "",
                        field_name=mm.field_name,
                        mismatch_kind=mm.mismatch_kind.value,
                        fix_suggestion=(
                            f"Change consumer type from '{mm.consumer_type}' to a compatible type."
                        ),
                    )
                )
    return findings


@register_rule
def no_phantom_types(graph: ContractGraph, config: dict[str, Any]) -> list[Finding]:
    """TypeScript types without any matching provider are phantom types."""
    findings: list[Finding] = []

    # Collect all TS nodes that are targets of API_TYPE_SYNC edges
    matched_ts_nodes: set[str] = set()
    for edge in graph.edges:
        if edge.kind == EdgeKind.API_TYPE_SYNC:
            matched_ts_nodes.add(edge.target)

    # Find unmatched TS nodes
    from contract_graph.graph.model import NodeKind

    for nid, node in graph.nodes.items():
        if node.kind in (NodeKind.TS_INTERFACE, NodeKind.TS_TYPE) and nid not in matched_ts_nodes:
            findings.append(
                Finding(
                    discoverer="rule:no_phantom_types",
                    severity=Severity.MEDIUM,
                    title=f"Phantom type: {node.name}",
                    description=(
                        f"TypeScript type '{node.name}' in {node.file_path} "
                        f"has no matching Pydantic model (provider)."
                    ),
                    consumer_file=str(node.file_path),
                    consumer_name=node.name,
                    consumer_line=node.line_start,
                    fix_suggestion="Add a matching Pydantic model or remove the unused TypeScript type.",
                )
            )

    return findings

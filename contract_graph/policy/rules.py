"""Built-in policy rules."""

from __future__ import annotations

from typing import Any

from contract_graph.graph.model import (
    ContractGraph,
    ContractNode,
    EdgeKind,
    Finding,
    MismatchKind,
    Severity,
    _node_ref,
)
from contract_graph.policy.engine import register_rule


def _build_finding(
    *,
    discoverer: str,
    severity: Severity,
    title: str,
    description: str,
    src: ContractNode | None,
    src_id: str,
    tgt: ContractNode | None,
    tgt_id: str,
    field_name: str,
    mismatch_kind: str,
    fix_suggestion: str = "",
) -> Finding:
    """Build a Finding from src/tgt nodes, handling None gracefully."""
    return Finding(
        discoverer=discoverer,
        severity=severity,
        title=title,
        description=description,
        **_node_ref(src, src_id, prefix="provider"),
        **_node_ref(tgt, tgt_id, prefix="consumer"),
        field_name=field_name,
        mismatch_kind=mismatch_kind,
        fix_suggestion=fix_suggestion,
    )


@register_rule
def no_missing_consumer_fields(graph: ContractGraph, config: dict[str, Any]) -> list[Finding]:
    """Provider fields must exist in consumer (with compatible types)."""
    findings: list[Finding] = []
    for edge in graph.edges_by_kind(EdgeKind.API_TYPE_SYNC):
        src = graph.get_node(edge.source)
        tgt = graph.get_node(edge.target)
        for mm in edge.mismatches:
            if mm.mismatch_kind == MismatchKind.MISSING_IN_CONSUMER:
                findings.append(
                    _build_finding(
                        discoverer="rule:no_missing_consumer_fields",
                        severity=Severity.MEDIUM,
                        title=f"Missing field '{mm.field_name}' in consumer",
                        description=(
                            f"Provider '{src.name if src else edge.source}' has field "
                            f"'{mm.field_name}' (type: {mm.provider_type}) "
                            f"but consumer '{tgt.name if tgt else edge.target}' does not."
                        ),
                        src=src,
                        src_id=edge.source,
                        tgt=tgt,
                        tgt_id=edge.target,
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
    for edge in graph.edges_by_kind(EdgeKind.API_TYPE_SYNC):
        src = graph.get_node(edge.source)
        tgt = graph.get_node(edge.target)
        for mm in edge.mismatches:
            if mm.mismatch_kind == MismatchKind.TYPE_INCOMPATIBLE:
                findings.append(
                    _build_finding(
                        discoverer="rule:no_type_incompatibility",
                        severity=Severity.HIGH,
                        title=f"Type mismatch: {mm.field_name}",
                        description=(
                            f"Provider type '{mm.provider_type}' is incompatible "
                            f"with consumer type '{mm.consumer_type}'."
                        ),
                        src=src,
                        src_id=edge.source,
                        tgt=tgt,
                        tgt_id=edge.target,
                        field_name=mm.field_name,
                        mismatch_kind=mm.mismatch_kind.value,
                        fix_suggestion=(f"Change consumer type from '{mm.consumer_type}' to a compatible type."),
                    )
                )
    return findings


@register_rule
def no_extra_consumer_fields(graph: ContractGraph, config: dict[str, Any]) -> list[Finding]:
    """Consumer must not have fields absent from the provider."""
    findings: list[Finding] = []
    for edge in graph.edges_by_kind(EdgeKind.API_TYPE_SYNC):
        src = graph.get_node(edge.source)
        tgt = graph.get_node(edge.target)
        for mm in edge.mismatches:
            if mm.mismatch_kind == MismatchKind.MISSING_IN_PROVIDER:
                findings.append(
                    _build_finding(
                        discoverer="rule:no_extra_consumer_fields",
                        severity=Severity.MEDIUM,
                        title=f"Extra field '{mm.field_name}' in consumer",
                        description=(
                            f"Consumer '{tgt.name if tgt else edge.target}' has field "
                            f"'{mm.field_name}' (type: {mm.consumer_type}) "
                            f"but provider '{src.name if src else edge.source}' does not."
                        ),
                        src=src,
                        src_id=edge.source,
                        tgt=tgt,
                        tgt_id=edge.target,
                        field_name=mm.field_name,
                        mismatch_kind=mm.mismatch_kind.value,
                        fix_suggestion=(f"Add '{mm.field_name}' to the provider model or remove it from the consumer."),
                    )
                )
    return findings


@register_rule
def no_optionality_drift(graph: ContractGraph, config: dict[str, Any]) -> list[Finding]:
    """Optional/required status must match between provider and consumer."""
    findings: list[Finding] = []
    for edge in graph.edges_by_kind(EdgeKind.API_TYPE_SYNC):
        src = graph.get_node(edge.source)
        tgt = graph.get_node(edge.target)
        for mm in edge.mismatches:
            if mm.mismatch_kind == MismatchKind.OPTIONALITY_MISMATCH:
                findings.append(
                    _build_finding(
                        discoverer="rule:no_optionality_drift",
                        severity=Severity.LOW,
                        title=f"Optionality drift: {mm.field_name}",
                        description=(
                            f"Field '{mm.field_name}' has mismatched optionality between "
                            f"provider '{src.name if src else edge.source}' "
                            f"and consumer '{tgt.name if tgt else edge.target}'."
                        ),
                        src=src,
                        src_id=edge.source,
                        tgt=tgt,
                        tgt_id=edge.target,
                        field_name=mm.field_name,
                        mismatch_kind=mm.mismatch_kind.value,
                        fix_suggestion=(f"Align the optionality of '{mm.field_name}' between provider and consumer."),
                    )
                )
    return findings


@register_rule
def no_phantom_types(graph: ContractGraph, config: dict[str, Any]) -> list[Finding]:
    """TypeScript types without any matching provider are phantom types."""
    findings: list[Finding] = []

    # Collect all TS nodes that are targets of API_TYPE_SYNC edges
    matched_ts_nodes: set[str] = {edge.target for edge in graph.edges_by_kind(EdgeKind.API_TYPE_SYNC)}

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
                        f"TypeScript type '{node.name}' in {node.file_path} has no matching Pydantic model (provider)."
                    ),
                    consumer_file=str(node.file_path),
                    consumer_name=node.name,
                    consumer_line=node.line_start,
                    fix_suggestion="Add a matching Pydantic model or remove the unused TypeScript type.",
                )
            )

    return findings

"""Impact analysis — change propagation through the contract graph."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from contract_graph.graph.model import ContractGraph, Severity


@dataclass
class ImpactResult:
    """Result of a change-impact analysis for a given file."""

    file_path: str
    directly_affected: list[str]  # Node IDs in this file
    downstream_nodes: list[str]  # Transitively affected node IDs
    upstream_nodes: list[str]  # Nodes that depend on this file
    risk_level: Severity
    affected_files: set[str]  # Unique files downstream

    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "directly_affected": self.directly_affected,
            "downstream_count": len(self.downstream_nodes),
            "upstream_count": len(self.upstream_nodes),
            "risk": self.risk_level.value,
            "affected_files": sorted(self.affected_files),
        }


def analyze_impact(graph: ContractGraph, file_path: str, depth: int = -1) -> ImpactResult:
    """Analyze the impact of changing a file on downstream contracts."""
    normalized = Path(file_path).as_posix()

    # Find all nodes in this file
    local_nodes = [nid for nid, node in graph.nodes.items() if Path(node.file_path).as_posix().endswith(normalized)]

    # Collect downstream
    all_downstream: set[str] = set()
    for nid in local_nodes:
        all_downstream |= graph.downstream(nid, depth=depth)

    # Collect upstream
    all_upstream: set[str] = set()
    for nid in local_nodes:
        all_upstream |= graph.upstream(nid, depth=depth)

    # Unique affected files
    affected_files: set[str] = set()
    for nid in all_downstream:
        node = graph.get_node(nid)
        if node:
            affected_files.add(str(node.file_path))

    # Determine risk level
    if len(all_downstream) > 10:
        risk = Severity.CRITICAL
    elif len(all_downstream) > 5:
        risk = Severity.HIGH
    elif len(all_downstream) > 2:
        risk = Severity.MEDIUM
    elif all_downstream:
        risk = Severity.LOW
    else:
        risk = Severity.INFO

    return ImpactResult(
        file_path=file_path,
        directly_affected=local_nodes,
        downstream_nodes=sorted(all_downstream),
        upstream_nodes=sorted(all_upstream),
        risk_level=risk,
        affected_files=affected_files,
    )

"""Graph model — ContractNode, ContractEdge, ContractGraph."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import networkx as nx

# ── Node & Edge Kinds ──────────────────────────────────────────────


class NodeKind(StrEnum):
    PYDANTIC_MODEL = "pydantic_model"
    TS_INTERFACE = "ts_interface"
    TS_TYPE = "ts_type"
    CONFIG_KEY = "config_key"
    CODE_READER = "code_reader"
    BACKEND_ROUTE = "backend_route"
    FRONTEND_CALL = "frontend_call"
    DB_TABLE = "db_table"
    DB_MIGRATION = "db_migration"
    INSTRUCTION_SECTION = "instruction_section"


class EdgeKind(StrEnum):
    API_TYPE_SYNC = "api_type_sync"
    CONFIG_USAGE = "config_usage"
    ROUTE_ACTIVATION = "route_activation"
    SCHEMA_EVOLUTION = "schema_evolution"
    INSTRUCTION_REF = "instruction_ref"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MismatchKind(StrEnum):
    MISSING_IN_CONSUMER = "missing_in_consumer"
    MISSING_IN_PROVIDER = "missing_in_provider"
    TYPE_INCOMPATIBLE = "type_incompatible"
    NAMING_MISMATCH = "naming_mismatch"
    OPTIONALITY_MISMATCH = "optionality_mismatch"


# ── Field Info ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class FieldInfo:
    """Describes a single field in a model/interface."""

    name: str
    type_str: str
    is_optional: bool = False
    has_default: bool = False
    default_value: Any = None


@dataclass(frozen=True)
class FieldMismatch:
    """A concrete mismatch between provider and consumer field."""

    field_name: str
    provider_type: str | None  # None if field is missing
    consumer_type: str | None  # None if field is missing
    mismatch_kind: MismatchKind


# ── Contract Node ──────────────────────────────────────────────────


@dataclass
class ContractNode:
    """A node in the contract graph (model, interface, route, config key, etc.)."""

    id: str  # e.g. "backend/api/models/user.py::UserResponse"
    kind: NodeKind
    file_path: Path
    name: str
    fields: dict[str, FieldInfo] = field(default_factory=dict)
    line_start: int = 0
    line_end: int = 0
    file_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_file_hash(self) -> str:
        """Compute SHA-256 hash of the source file for cache invalidation."""
        if self.file_path.exists():
            content = self.file_path.read_bytes()
            self.file_hash = hashlib.sha256(content).hexdigest()[:16]
        return self.file_hash


# ── Contract Edge ──────────────────────────────────────────────────


@dataclass
class ContractEdge:
    """A directed edge representing a contract between two nodes."""

    source: str  # Node ID (provider)
    target: str  # Node ID (consumer)
    kind: EdgeKind
    confidence: float = 1.0  # 0.0-1.0
    field_coverage: float = 0.0  # Fraction of matched fields
    mismatches: list[FieldMismatch] = field(default_factory=list)
    severity: Severity = Severity.INFO
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Finding ────────────────────────────────────────────────────────


@dataclass
class Finding:
    """A concrete contract violation or issue discovered during analysis."""

    discoverer: str
    severity: Severity
    title: str
    description: str
    provider_file: str = ""
    provider_name: str = ""
    provider_line: int = 0
    consumer_file: str = ""
    consumer_name: str = ""
    consumer_line: int = 0
    field_name: str = ""
    mismatch_kind: str = ""
    fix_suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: str(v) if isinstance(v, Severity) else v for k, v in self.__dict__.items()}


# ── Contract Graph ─────────────────────────────────────────────────


class ContractGraph:
    """The main contract graph holding nodes and edges, backed by networkx."""

    def __init__(self) -> None:
        self._nx: nx.DiGraph = nx.DiGraph()
        self.nodes: dict[str, ContractNode] = {}
        self.edges: list[ContractEdge] = []

    def add_node(self, node: ContractNode) -> None:
        self.nodes[node.id] = node
        self._nx.add_node(node.id, kind=node.kind, name=node.name)

    def add_edge(self, edge: ContractEdge) -> None:
        self.edges.append(edge)
        self._nx.add_edge(edge.source, edge.target, kind=edge.kind, severity=edge.severity)

    def get_node(self, node_id: str) -> ContractNode | None:
        return self.nodes.get(node_id)

    def get_edges_from(self, node_id: str) -> list[ContractEdge]:
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[ContractEdge]:
        return [e for e in self.edges if e.target == node_id]

    def downstream(self, node_id: str, depth: int = -1) -> set[str]:
        """BFS downstream from a node. depth=-1 means unlimited."""
        if node_id not in self._nx:
            return set()
        if depth == -1:
            return set(nx.descendants(self._nx, node_id))
        visited: set[str] = set()
        frontier = {node_id}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for n in frontier:
                for succ in self._nx.successors(n):
                    if succ not in visited:
                        visited.add(succ)
                        next_frontier.add(succ)
            frontier = next_frontier
            if not frontier:
                break
        return visited

    def upstream(self, node_id: str, depth: int = -1) -> set[str]:
        """BFS upstream from a node."""
        if node_id not in self._nx:
            return set()
        if depth == -1:
            return set(nx.ancestors(self._nx, node_id))
        visited: set[str] = set()
        frontier = {node_id}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for n in frontier:
                for pred in self._nx.predecessors(n):
                    if pred not in visited:
                        visited.add(pred)
                        next_frontier.add(pred)
            frontier = next_frontier
            if not frontier:
                break
        return visited

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def findings(self) -> list[Finding]:
        """Collect all findings from edges with mismatches."""
        results: list[Finding] = []
        for edge in self.edges:
            src = self.nodes.get(edge.source)
            tgt = self.nodes.get(edge.target)
            for mm in edge.mismatches:
                results.append(
                    Finding(
                        discoverer=edge.kind.value,
                        severity=edge.severity,
                        title=f"{mm.mismatch_kind.value}: {mm.field_name}",
                        description=(f"Provider type '{mm.provider_type}' vs consumer type '{mm.consumer_type}'"),
                        provider_file=str(src.file_path) if src else "",
                        provider_name=src.name if src else edge.source,
                        provider_line=src.line_start if src else 0,
                        consumer_file=str(tgt.file_path) if tgt else "",
                        consumer_name=tgt.name if tgt else edge.target,
                        consumer_line=tgt.line_start if tgt else 0,
                        field_name=mm.field_name,
                        mismatch_kind=mm.mismatch_kind.value,
                    )
                )
        return results

    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph to a dict for JSON output."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "kind": n.kind.value,
                    "file": str(n.file_path),
                    "name": n.name,
                    "fields": {k: {"type": v.type_str, "optional": v.is_optional} for k, v in n.fields.items()},
                    "lines": [n.line_start, n.line_end],
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "kind": e.kind.value,
                    "confidence": e.confidence,
                    "field_coverage": e.field_coverage,
                    "severity": e.severity.value,
                    "mismatches": [
                        {
                            "field": m.field_name,
                            "provider_type": m.provider_type,
                            "consumer_type": m.consumer_type,
                            "kind": m.mismatch_kind.value,
                        }
                        for m in e.mismatches
                    ],
                }
                for e in self.edges
            ],
        }

"""Shared test fixtures for contract-graph."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

import_module("contract_graph.discovery")  # registers built-in discoverers
import_module("contract_graph.policy")  # registers built-in rules

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FULLSTACK_BASIC = FIXTURES_DIR / "fullstack_basic"

# ── Shared constants ────────────────────────────────────────────────────────

DEFAULT_DISCOVERY_CFG: dict[str, Any] = {
    "enabled": True,
    "providers": ["backend/**/*.py"],
    "consumers": ["frontend/**/*.ts"],
    "field_naming": {"provider": "snake_case", "consumer": "camelCase"},
    "custom_mappings": [],
    "base_classes": ["BaseModel"],
}

ALL_DEFAULT_POLICIES: list[dict[str, Any]] = [
    {"name": "no_missing_consumer_fields", "enabled": True},
    {"name": "no_type_incompatibility", "enabled": True},
    {"name": "no_extra_consumer_fields", "enabled": True},
    {"name": "no_optionality_drift", "enabled": True},
    {"name": "no_phantom_types", "enabled": True},
]

# ── Shared helper functions ─────────────────────────────────────────────────


def run_discovery(root: str | Path, config: dict[str, Any] | None = None):
    """Run api_type_sync discovery. Returns (graph, nodes, edges)."""
    from contract_graph.discovery.api_type_sync import ApiTypeSyncDiscoverer
    from contract_graph.graph.builder import GraphBuilder

    disc = ApiTypeSyncDiscoverer()
    builder = GraphBuilder()
    cfg = config or DEFAULT_DISCOVERY_CFG
    nodes, edges = disc.discover(builder.build(), cfg, str(root))
    builder.merge_nodes(nodes)
    builder.merge_edges(edges)
    return builder.build(), nodes, edges


def get_mismatches_by_kind(edges, kind):
    """Flatten all mismatches from a list of edges, filtered by MismatchKind."""
    return [m for e in edges for m in e.mismatches if m.mismatch_kind == kind]


# ── pytest fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def fullstack_basic() -> Path:
    return FULLSTACK_BASIC

"""Tests for API Type Sync discoverer — the MVP killer feature."""

from __future__ import annotations

from pathlib import Path

from contract_graph.discovery.api_type_sync import ApiTypeSyncDiscoverer
from contract_graph.graph.builder import GraphBuilder
from contract_graph.graph.model import (
    EdgeKind,
    MismatchKind,
    NodeKind,
)


def _run_discovery(root: str, config: dict | None = None) -> tuple:
    """Helper: run api_type_sync discovery on the given root."""
    disc = ApiTypeSyncDiscoverer()
    builder = GraphBuilder()
    cfg = config or {
        "enabled": True,
        "providers": ["backend/**/*.py"],
        "consumers": ["frontend/**/*.ts"],
        "field_naming": {"provider": "snake_case", "consumer": "camelCase"},
        "custom_mappings": [],
        "base_classes": ["BaseModel"],
    }
    nodes, edges = disc.discover(builder.build(), cfg, root)
    builder.merge_nodes(nodes)
    builder.merge_edges(edges)
    graph = builder.build()
    return graph, nodes, edges


class TestApiTypeSyncDiscovery:
    def test_discovers_nodes(self, fullstack_basic: Path):
        graph, _nodes, _edges = _run_discovery(str(fullstack_basic))
        assert graph.node_count > 0, "Should discover at least one node"

    def test_discovers_pydantic_models(self, fullstack_basic: Path):
        _graph, nodes, _ = _run_discovery(str(fullstack_basic))
        pydantic_nodes = [n for n in nodes if n.kind == NodeKind.PYDANTIC_MODEL]
        names = {n.name for n in pydantic_nodes}
        assert "MatchResponse" in names
        assert "PlayerStats" in names

    def test_discovers_ts_interfaces(self, fullstack_basic: Path):
        _graph, nodes, _ = _run_discovery(str(fullstack_basic))
        ts_nodes = [n for n in nodes if n.kind == NodeKind.TS_INTERFACE]
        names = {n.name for n in ts_nodes}
        assert "MatchResponse" in names
        assert "PlayerStats" in names

    def test_creates_sync_edges(self, fullstack_basic: Path):
        _graph, _, edges = _run_discovery(str(fullstack_basic))
        sync_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC]
        assert len(sync_edges) >= 2, "Should link at least MatchResponse + PlayerStats"

    def test_detects_missing_field_in_consumer(self, fullstack_basic: Path):
        """match_mode is in backend MatchResponse but missing from frontend."""
        _graph, _, edges = _run_discovery(str(fullstack_basic))
        all_mismatches = []
        for e in edges:
            all_mismatches.extend(e.mismatches)

        missing = [m for m in all_mismatches if m.mismatch_kind == MismatchKind.MISSING_IN_CONSUMER]
        field_names = {m.field_name for m in missing}
        assert "match_mode" in field_names, "match_mode should be detected as missing in consumer"

    def test_detects_extra_field_in_consumer(self, fullstack_basic: Path):
        """favoriteWeapon is in frontend PlayerStats but not in backend."""
        _graph, _, edges = _run_discovery(str(fullstack_basic))
        all_mismatches = []
        for e in edges:
            all_mismatches.extend(e.mismatches)

        missing_provider = [m for m in all_mismatches if m.mismatch_kind == MismatchKind.MISSING_IN_PROVIDER]
        field_names = {m.field_name for m in missing_provider}
        # The discoverer may normalize to snake_case
        assert "favorite_weapon" in field_names or "favoriteWeapon" in field_names

    def test_severity_assigned(self, fullstack_basic: Path):
        _graph, _, edges = _run_discovery(str(fullstack_basic))
        edges_with_mismatches = [e for e in edges if e.mismatches]
        assert edges_with_mismatches, "Should have edges with mismatches"
        for e in edges_with_mismatches:
            assert e.severity is not None

    def test_edge_metadata_populated(self, fullstack_basic: Path):
        _graph, _, edges = _run_discovery(str(fullstack_basic))
        sync_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC]
        for e in sync_edges:
            assert e.source, "Edge should have source node ID"
            assert e.target, "Edge should have target node ID"


class TestNameMatching:
    """Test camelCase ↔ snake_case matching."""

    def test_auto_matching_works(self, fullstack_basic: Path):
        """MatchResponse (both) should match, PlayerStats (both) should match."""
        _graph, _, edges = _run_discovery(str(fullstack_basic))
        sync_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC]
        # Both MatchResponse and PlayerStats should be matched
        assert len(sync_edges) >= 2

    def test_custom_model_mapping(self, fullstack_basic: Path):
        """Custom mapping should override name matching."""
        config = {
            "enabled": True,
            "providers": ["backend/**/*.py"],
            "consumers": ["frontend/**/*.ts"],
            "field_naming": {"provider": "snake_case", "consumer": "camelCase"},
            "custom_mappings": [{"provider": "SessionConfig", "consumer": "SessionConfig"}],
            "base_classes": ["BaseModel"],
        }
        _graph, _, edges = _run_discovery(str(fullstack_basic), config)
        sync_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC]
        assert len(sync_edges) >= 3, "SessionConfig should also be matched via mapping"

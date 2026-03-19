"""Tests for contract_graph.graph.model — graph core."""

from __future__ import annotations

from pathlib import Path

from contract_graph.graph.model import (
    ContractEdge,
    ContractGraph,
    ContractNode,
    EdgeKind,
    FieldInfo,
    FieldMismatch,
    Finding,
    MismatchKind,
    NodeKind,
    Severity,
)


class TestContractNode:
    def test_node_creation(self):
        node = ContractNode(
            id="pydantic::MatchResponse",
            kind=NodeKind.PYDANTIC_MODEL,
            name="MatchResponse",
            file_path=Path("backend/models.py"),
            fields={
                "id": FieldInfo(name="id", type_str="UUID", is_optional=False),
                "score": FieldInfo(name="score", type_str="int", is_optional=False),
            },
        )
        assert node.id == "pydantic::MatchResponse"
        assert node.kind == NodeKind.PYDANTIC_MODEL
        assert len(node.fields) == 2

    def test_node_file_hash_missing(self):
        node = ContractNode(
            id="test",
            kind=NodeKind.PYDANTIC_MODEL,
            name="Test",
            file_path=Path("missing.py"),
        )
        h = node.compute_file_hash()
        assert h == ""

    def test_node_file_hash_with_real_file(self, tmp_path: Path):
        f = tmp_path / "model.py"
        f.write_text("class Foo: pass")
        node = ContractNode(
            id="test",
            kind=NodeKind.PYDANTIC_MODEL,
            name="Test",
            file_path=f,
        )
        h = node.compute_file_hash()
        assert len(h) == 32  # SHA-256 hex[:32]


class TestContractGraph:
    def _make_graph(self) -> ContractGraph:
        g = ContractGraph()
        n1 = ContractNode(id="A", kind=NodeKind.PYDANTIC_MODEL, name="ModelA", file_path=Path("a.py"))
        n2 = ContractNode(
            id="B",
            kind=NodeKind.TS_INTERFACE,
            name="InterfaceB",
            file_path=Path("b.ts"),
        )
        n3 = ContractNode(
            id="C",
            kind=NodeKind.TS_INTERFACE,
            name="InterfaceC",
            file_path=Path("c.ts"),
        )
        g.add_node(n1)
        g.add_node(n2)
        g.add_node(n3)
        g.add_edge(ContractEdge(source="A", target="B", kind=EdgeKind.API_TYPE_SYNC))
        g.add_edge(ContractEdge(source="B", target="C", kind=EdgeKind.API_TYPE_SYNC))
        return g

    def test_node_count(self):
        g = self._make_graph()
        assert g.node_count == 3

    def test_edge_count(self):
        g = self._make_graph()
        assert g.edge_count == 2

    def test_get_node(self):
        g = self._make_graph()
        assert g.get_node("A") is not None
        assert g.get_node("A").name == "ModelA"
        assert g.get_node("Z") is None

    def test_downstream(self):
        g = self._make_graph()
        downstream = g.downstream("A")
        assert "B" in downstream
        assert "C" in downstream

    def test_upstream(self):
        g = self._make_graph()
        upstream = g.upstream("C")
        assert "B" in upstream
        assert "A" in upstream

    def test_downstream_depth_limited(self):
        g = self._make_graph()
        downstream = g.downstream("A", depth=1)
        assert "B" in downstream
        assert "C" not in downstream

    def test_to_dict(self):
        g = self._make_graph()
        d = g.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 2

    def test_edges_from(self):
        g = self._make_graph()
        edges = g.get_edges_from("A")
        assert len(edges) == 1
        assert edges[0].target == "B"

    def test_edges_to(self):
        g = self._make_graph()
        edges = g.get_edges_to("C")
        assert len(edges) == 1
        assert edges[0].source == "B"

    def test_findings_collect(self):
        g = ContractGraph()
        n1 = ContractNode(id="A", kind=NodeKind.PYDANTIC_MODEL, name="A", file_path=Path("a.py"))
        n2 = ContractNode(id="B", kind=NodeKind.TS_INTERFACE, name="B", file_path=Path("b.ts"))
        g.add_node(n1)
        g.add_node(n2)
        g.add_edge(
            ContractEdge(
                source="A",
                target="B",
                kind=EdgeKind.API_TYPE_SYNC,
                mismatches=[
                    FieldMismatch(
                        field_name="x",
                        provider_type="str",
                        consumer_type=None,
                        mismatch_kind=MismatchKind.MISSING_IN_CONSUMER,
                    )
                ],
            )
        )
        findings = g.findings()
        assert len(findings) >= 1


class TestFinding:
    def test_to_dict(self):
        f = Finding(
            title="Missing field",
            severity=Severity.HIGH,
            discoverer="api_type_sync",
            description="Field X missing",
            provider_file="models.py",
            field_name="x",
            mismatch_kind="missing_in_consumer",
        )
        d = f.to_dict()
        assert d["title"] == "Missing field"
        assert d["severity"] == "high"


class TestFieldMismatch:
    def test_creation(self):
        m = FieldMismatch(
            field_name="score",
            mismatch_kind=MismatchKind.TYPE_INCOMPATIBLE,
            provider_type="int",
            consumer_type="string",
        )
        assert m.field_name == "score"
        assert m.mismatch_kind == MismatchKind.TYPE_INCOMPATIBLE

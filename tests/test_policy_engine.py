"""Tests for policy engine and built-in rules."""

from __future__ import annotations

from pathlib import Path

from conftest import ALL_DEFAULT_POLICIES

from contract_graph.graph.builder import GraphBuilder
from contract_graph.graph.model import (
    ContractEdge,
    ContractNode,
    EdgeKind,
    FieldMismatch,
    MismatchKind,
    NodeKind,
    Severity,
)
from contract_graph.policy.engine import PolicyEngine


def _build_graph_with_drift():
    """Build a graph with known mismatches for testing policy rules."""
    builder = GraphBuilder()

    # Provider node
    builder.add_node(
        ContractNode(
            id="pydantic::MatchResponse",
            kind=NodeKind.PYDANTIC_MODEL,
            name="MatchResponse",
            file_path=Path("backend/models.py"),
        )
    )

    # Consumer node
    builder.add_node(
        ContractNode(
            id="ts::MatchResponse",
            kind=NodeKind.TS_INTERFACE,
            name="MatchResponse",
            file_path=Path("frontend/types.ts"),
        )
    )

    # Phantom type (no sync edge targets it)
    builder.add_node(
        ContractNode(
            id="ts::PhantomType",
            kind=NodeKind.TS_INTERFACE,
            name="PhantomType",
            file_path=Path("frontend/types.ts"),
        )
    )

    # Edge with mismatches
    builder.add_edge(
        ContractEdge(
            source="pydantic::MatchResponse",
            target="ts::MatchResponse",
            kind=EdgeKind.API_TYPE_SYNC,
            severity=Severity.HIGH,
            mismatches=[
                FieldMismatch(
                    field_name="match_mode",
                    provider_type="str",
                    consumer_type=None,
                    mismatch_kind=MismatchKind.MISSING_IN_CONSUMER,
                ),
                FieldMismatch(
                    field_name="score",
                    provider_type="int",
                    consumer_type="string",
                    mismatch_kind=MismatchKind.TYPE_INCOMPATIBLE,
                ),
            ],
        )
    )

    return builder.build()


class TestPolicyEngine:
    def test_evaluate_finds_issues(self):
        graph = _build_graph_with_drift()
        engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
        findings = engine.evaluate(graph)
        assert len(findings) > 0

    def test_gate_fails_on_high(self):
        graph = _build_graph_with_drift()
        engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
        passed, findings = engine.evaluate_gate(graph, "high")
        assert not passed, "Gate should fail — we have HIGH severity edge"

    def test_gate_passes_with_low_threshold(self):
        """Empty graph should pass any gate."""
        builder = GraphBuilder()
        builder.add_node(
            ContractNode(
                id="test",
                kind=NodeKind.PYDANTIC_MODEL,
                name="Test",
                file_path=Path("test.py"),
            )
        )
        graph = builder.build()
        engine = PolicyEngine({})
        passed, _findings = engine.evaluate_gate(graph, "critical")
        assert passed

    def test_no_missing_consumer_fields_rule(self):
        graph = _build_graph_with_drift()
        engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
        findings = engine.evaluate(graph)
        missing_findings = [f for f in findings if "missing" in f.title.lower() or "consumer" in f.title.lower()]
        assert len(missing_findings) > 0

    def test_no_type_incompatibility_rule(self):
        graph = _build_graph_with_drift()
        engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
        findings = engine.evaluate(graph)
        type_findings = [f for f in findings if "type" in f.title.lower() or "incompatib" in f.title.lower()]
        assert len(type_findings) > 0

    def test_phantom_type_rule(self):
        graph = _build_graph_with_drift()
        engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
        findings = engine.evaluate(graph)
        phantom_findings = [f for f in findings if "phantom" in f.title.lower()]
        assert len(phantom_findings) > 0
        assert any("PhantomType" in f.description for f in phantom_findings if f.description)


class TestScoring:
    def test_score_perfect(self):
        from contract_graph.scoring.scorer import score_findings

        result = score_findings([], {})
        assert result.overall_score == 1.0

    def test_score_degrades_with_findings(self):
        from contract_graph.graph.model import Finding
        from contract_graph.scoring.scorer import score_findings

        findings = [
            Finding(
                title="Bad",
                severity=Severity.HIGH,
                discoverer="api_type_sync",
                description="",
            ),
            Finding(
                title="Also bad",
                severity=Severity.MEDIUM,
                discoverer="api_type_sync",
                description="",
            ),
        ]
        result = score_findings(findings, {})
        assert result.overall_score < 1.0

    def test_score_has_discoverer_scores(self):
        from contract_graph.graph.model import Finding
        from contract_graph.scoring.scorer import score_findings

        findings = [
            Finding(
                title="A",
                severity=Severity.LOW,
                discoverer="api_type_sync",
                description="",
            ),
            Finding(
                title="B",
                severity=Severity.LOW,
                discoverer="config_usage",
                description="",
            ),
        ]
        result = score_findings(findings, {})
        assert "api_type_sync" in result.discoverer_scores
        assert "config_usage" in result.discoverer_scores

"""Regression demo tests — proves contract-graph catches bugs that mypy + tsc miss.

Each test class targets one specific drift category.  Together they form
the "smoking gun" evidence that static type-checkers alone are insufficient
for cross-boundary contract safety.

Drift types covered:
    1. Missing field in consumer   (backend adds field, frontend doesn't)
    2. Type incompatibility        (backend changes type, frontend stale)
    3. Phantom type                (frontend type with no backend model)
    4. Optionality drift           (Optional in backend, required in frontend)
    5. Clean contract (control)    (no drift — verifies zero false positives)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import ALL_DEFAULT_POLICIES, DEFAULT_DISCOVERY_CFG, get_mismatches_by_kind

from contract_graph.discovery.api_type_sync import ApiTypeSyncDiscoverer
from contract_graph.graph.builder import GraphBuilder
from contract_graph.graph.model import (
    EdgeKind,
    MismatchKind,
    NodeKind,
    Severity,
)
from contract_graph.policy.engine import PolicyEngine
from contract_graph.scoring.scorer import score_findings

REGRESSION_DIR = Path(__file__).parent / "fixtures" / "regression_demo"


def _run(config: dict | None = None):
    """Run full discovery + policy evaluation on the regression fixture."""
    disc = ApiTypeSyncDiscoverer()
    builder = GraphBuilder()
    cfg = config or DEFAULT_DISCOVERY_CFG
    nodes, edges = disc.discover(builder.build(), cfg, str(REGRESSION_DIR))
    builder.merge_nodes(nodes)
    builder.merge_edges(edges)
    graph = builder.build()

    engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
    findings = engine.evaluate(graph)
    return graph, nodes, edges, findings


# ── 1. Missing Field ───────────────────────────────────────────────


class TestMissingFieldDetection:
    """discount_code exists in OrderResponse (backend) but is absent in frontend."""

    def test_missing_field_detected_in_discovery(self):
        _, _, edges, _ = _run()
        missing = get_mismatches_by_kind(edges, MismatchKind.MISSING_IN_CONSUMER)
        field_names = {m.field_name for m in missing}
        assert "discount_code" in field_names

    def test_missing_field_produces_policy_finding(self):
        _, _, _, findings = _run()
        missing_findings = [
            f
            for f in findings
            if f.mismatch_kind == MismatchKind.MISSING_IN_CONSUMER.value and f.field_name == "discount_code"
        ]
        assert len(missing_findings) >= 1

    def test_missing_field_has_fix_suggestion(self):
        _, _, _, findings = _run()
        rule_findings = [
            f for f in findings if f.field_name == "discount_code" and f.discoverer == "rule:no_missing_consumer_fields"
        ]
        assert rule_findings, "Policy rule should produce finding for discount_code"
        assert rule_findings[0].fix_suggestion, "Finding should include a fix suggestion"


# ── 2. Type Mismatch ──────────────────────────────────────────────


class TestTypeMismatchDetection:
    """premium_tier is bool in backend but string in frontend."""

    def test_type_mismatch_detected_in_discovery(self):
        _, _, edges, _ = _run()
        type_mm = get_mismatches_by_kind(edges, MismatchKind.TYPE_INCOMPATIBLE)
        field_names = {m.field_name for m in type_mm}
        assert "premium_tier" in field_names

    def test_type_mismatch_shows_both_types(self):
        _, _, edges, _ = _run()
        type_mm = get_mismatches_by_kind(edges, MismatchKind.TYPE_INCOMPATIBLE)
        mm = next(m for m in type_mm if m.field_name == "premium_tier")
        assert mm.provider_type == "bool"
        assert "string" in mm.consumer_type

    def test_type_mismatch_produces_high_severity_edge(self):
        _, _, edges, _ = _run()
        user_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC and "UserProfile" in e.source]
        assert user_edges, "Should have a sync edge for UserProfile"
        assert user_edges[0].severity in (Severity.HIGH, Severity.CRITICAL)

    def test_type_mismatch_produces_policy_finding(self):
        _, _, _, findings = _run()
        type_findings = [
            f
            for f in findings
            if f.mismatch_kind == MismatchKind.TYPE_INCOMPATIBLE.value and f.field_name == "premium_tier"
        ]
        assert len(type_findings) >= 1


# ── 3. Phantom Type ───────────────────────────────────────────────


class TestPhantomTypeDetection:
    """PaymentMethod exists in frontend but has no backend model."""

    def test_phantom_type_detected_as_node(self):
        _, nodes, _, _ = _run()
        ts_names = {n.name for n in nodes if n.kind == NodeKind.TS_INTERFACE}
        assert "PaymentMethod" in ts_names

    def test_phantom_type_has_no_sync_edge(self):
        _, _, edges, _ = _run()
        sync_targets = {e.target for e in edges if e.kind == EdgeKind.API_TYPE_SYNC}
        payment_nodes = [n for n in _run()[1] if n.name == "PaymentMethod" and n.kind == NodeKind.TS_INTERFACE]
        assert payment_nodes, "PaymentMethod node should exist"
        assert payment_nodes[0].id not in sync_targets

    def test_phantom_type_produces_policy_finding(self):
        _, _, _, findings = _run()
        phantom = [f for f in findings if "phantom" in f.title.lower() and "PaymentMethod" in f.description]
        assert len(phantom) == 1


# ── 4. Optionality Drift ──────────────────────────────────────────


class TestOptionalityDriftDetection:
    """bio is Optional[str] in backend but required string in frontend."""

    def test_optionality_drift_detected_in_discovery(self):
        _, _, edges, _ = _run()
        opt_mm = get_mismatches_by_kind(edges, MismatchKind.OPTIONALITY_MISMATCH)
        field_names = {m.field_name for m in opt_mm}
        assert "bio" in field_names

    def test_optionality_drift_for_last_login(self):
        _, _, edges, _ = _run()
        opt_mm = get_mismatches_by_kind(edges, MismatchKind.OPTIONALITY_MISMATCH)
        field_names = {m.field_name for m in opt_mm}
        assert "last_login" in field_names


# ── 5. Clean Contract (Control / False Positive Check) ─────────


class TestCleanContractNoFalsePositives:
    """NotificationSettings is perfectly synced — should produce zero mismatches."""

    def test_notification_settings_has_sync_edge(self):
        _, _, edges, _ = _run()
        notif_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC and "NotificationSettings" in e.source]
        assert len(notif_edges) == 1

    def test_notification_settings_zero_mismatches(self):
        _, _, edges, _ = _run()
        notif_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC and "NotificationSettings" in e.source]
        assert notif_edges[0].mismatches == []

    def test_notification_settings_full_coverage(self):
        _, _, edges, _ = _run()
        notif_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC and "NotificationSettings" in e.source]
        assert notif_edges[0].field_coverage == 1.0

    def test_notification_settings_severity_info(self):
        _, _, edges, _ = _run()
        notif_edges = [e for e in edges if e.kind == EdgeKind.API_TYPE_SYNC and "NotificationSettings" in e.source]
        assert notif_edges[0].severity == Severity.INFO


# ── 6. Health Score Degrades with Real Drift ───────────────────


class TestHealthScoreDegradation:
    """Proves the fixture has measurable impact on the health score."""

    def test_score_below_perfect(self):
        _, _, _, findings = _run()
        result = score_findings(findings, {"api_type_sync": 1.0})
        assert result.overall_score < 1.0, "Fixture with drift should not score 100"

    def test_score_above_zero(self):
        _, _, _, findings = _run()
        result = score_findings(findings, {"api_type_sync": 1.0})
        assert result.overall_score > 0.0, "Score should not be zero — some contracts are healthy"

    def test_findings_count_matches_expected_drift(self):
        """We expect findings for: discount_code, premium_tier, bio, last_login, PaymentMethod."""
        _, _, _, findings = _run()
        # At least 5 distinct findings covering the 4 drift types + phantom
        assert len(findings) >= 5


# ── 7. CI Gate ─────────────────────────────────────────────────


class TestCIGateBehavior:
    """Proves that `check --fail-on high` correctly blocks this fixture."""

    def test_gate_fails_on_high(self):
        graph, _, _, _ = _run()
        engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
        passed, _findings = engine.evaluate_gate(graph, "high")
        assert not passed, "Gate should FAIL — premium_tier type mismatch is HIGH severity"

    def test_gate_passes_on_critical(self):
        graph, _, _, _ = _run()
        engine = PolicyEngine({"policies": ALL_DEFAULT_POLICIES})
        passed, _findings = engine.evaluate_gate(graph, "critical")
        assert passed, "Gate should pass — no CRITICAL findings in this fixture"

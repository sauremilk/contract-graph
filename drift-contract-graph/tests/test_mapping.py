"""Unit tests for drift_contract_graph.mapping.

Tests are hermetic — no subprocess, no filesystem.  All inputs are plain dicts.
"""

from __future__ import annotations

# ── Helpers ────────────────────────────────────────────────────────────────


def _raw(
    *,
    discoverer: str = "api_type_sync",
    severity: str = "high",
    title: str = "Field userId missing in consumer",
    description: str = "Backend exposes userId; frontend types.ts does not declare it.",
    provider_file: str = "backend/models.py",
    provider_name: str = "UserResponse",
    provider_line: int = 14,
    consumer_file: str = "frontend/types.ts",
    consumer_name: str = "UserResponse",
    consumer_line: int = 3,
    field_name: str = "userId",
    mismatch_kind: str = "missing_in_consumer",
    fix_suggestion: str = "Add userId: string to UserResponse in frontend/types.ts",
    finding_id: str = "CG-abc123def456",
) -> dict:
    return {
        "discoverer": discoverer,
        "severity": severity,
        "title": title,
        "description": description,
        "provider_file": provider_file,
        "provider_name": provider_name,
        "provider_line": provider_line,
        "consumer_file": consumer_file,
        "consumer_name": consumer_name,
        "consumer_line": consumer_line,
        "field_name": field_name,
        "mismatch_kind": mismatch_kind,
        "fix_suggestion": fix_suggestion,
        "finding_id": finding_id,
    }


# ── map_finding ─────────────────────────────────────────────────────────────


class TestMapFinding:
    def test_severity_is_mapped_correctly(self):
        from drift_contract_graph.mapping import map_finding

        for sev, expected_score in [
            ("critical", 1.0),
            ("high", 0.8),
            ("medium", 0.5),
            ("low", 0.2),
            ("info", 0.0),
        ]:
            f = map_finding(_raw(severity=sev))
            assert f.severity.value == sev
            assert f.score == expected_score

    def test_unknown_severity_falls_back_to_medium(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(severity="bogus"))
        assert f.severity.value == "medium"
        assert f.score == 0.5

    def test_signal_type_is_contract_graph_drift(self):
        from drift_contract_graph.mapping import CONTRACT_GRAPH_SIGNAL_TYPE, map_finding

        f = map_finding(_raw())
        assert f.signal_type == CONTRACT_GRAPH_SIGNAL_TYPE

    def test_file_path_is_consumer_file(self):
        from pathlib import Path

        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(consumer_file="frontend/types.ts"))
        assert f.file_path == Path("frontend/types.ts")

    def test_file_path_falls_back_to_provider_file_when_consumer_empty(self):
        from pathlib import Path

        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(consumer_file="", provider_file="backend/models.py"))
        assert f.file_path == Path("backend/models.py")

    def test_file_path_is_none_when_both_empty(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(consumer_file="", provider_file=""))
        assert f.file_path is None

    def test_fix_is_populated_from_fix_suggestion(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(fix_suggestion="Add userId: string"))
        assert f.fix == "Add userId: string"

    def test_fix_is_none_when_fix_suggestion_empty(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(fix_suggestion=""))
        assert f.fix is None

    def test_root_cause_is_mismatch_kind(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(mismatch_kind="type_incompatible"))
        assert f.root_cause == "type_incompatible"

    def test_metadata_contains_contract_graph_block(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(field_name="userId", finding_id="CG-abc123def456"))
        cg = f.metadata["contract_graph"]
        assert cg["field_name"] == "userId"
        assert cg["finding_id"] == "CG-abc123def456"
        assert cg["provider_file"] == "backend/models.py"
        assert cg["consumer_file"] == "frontend/types.ts"

    def test_title_and_description_are_preserved(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(title="My title", description="My desc"))
        assert f.title == "My title"
        assert f.description == "My desc"

    def test_start_line_is_consumer_line(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(consumer_line=42))
        assert f.start_line == 42

    def test_start_line_falls_back_to_provider_line_when_consumer_zero(self):
        from drift_contract_graph.mapping import map_finding

        f = map_finding(_raw(consumer_line=0, provider_line=14))
        assert f.start_line == 14


# ── map_findings ─────────────────────────────────────────────────────────────


class TestMapFindings:
    def test_maps_list_of_findings(self):
        from drift_contract_graph.mapping import map_findings

        report = {"findings": [_raw(), _raw(severity="medium")]}
        results = map_findings(report)
        assert len(results) == 2

    def test_returns_empty_list_when_findings_missing(self):
        from drift_contract_graph.mapping import map_findings

        assert map_findings({}) == []

    def test_returns_empty_list_when_findings_not_a_list(self):
        from drift_contract_graph.mapping import map_findings

        assert map_findings({"findings": "not a list"}) == []

    def test_skips_malformed_entries_without_aborting(self):
        from drift_contract_graph.mapping import map_findings

        # None is not a dict — should be skipped; the valid entry must survive.
        report = {"findings": [None, _raw()]}
        results = map_findings(report)
        assert len(results) == 1

    def test_empty_findings_list_returns_empty(self):
        from drift_contract_graph.mapping import map_findings

        assert map_findings({"findings": []}) == []

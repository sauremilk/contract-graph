"""Unit tests for ContractGraphAdapter.

Tests are hermetic — subprocess calls are monkeypatched.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Fixtures ──────────────────────────────────────────────────────────────────

_VALID_REPORT = """{
  "tool": "contract-graph",
  "version": "1.1.1",
  "schema_version": "1.1",
  "findings": [
    {
      "finding_id": "CG-abc123def456",
      "discoverer": "api_type_sync",
      "severity": "high",
      "title": "Field userId missing in consumer",
      "description": "Backend exposes userId; frontend does not declare it.",
      "provider_file": "backend/models.py",
      "provider_name": "UserResponse",
      "provider_line": 14,
      "consumer_file": "frontend/types.ts",
      "consumer_name": "UserResponse",
      "consumer_line": 3,
      "field_name": "userId",
      "mismatch_kind": "missing_in_consumer",
      "fix_suggestion": "Add userId: string to UserResponse in frontend/types.ts"
    }
  ],
  "summary": {
    "total_findings": 1,
    "by_severity": {"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
    "score": {"overall": 0.8, "grade": "B"},
    "analyzed_at": "2026-04-25T10:00:00+00:00",
    "duration_seconds": 0.12
  },
  "contract_graph": {"nodes": 4, "edges": 2}
}"""


def _make_ctx(repo_path: Path = Path(".")) -> MagicMock:
    ctx = MagicMock()
    ctx.repo_path = repo_path
    ctx.timeout_seconds = 30
    return ctx


def _make_subprocess_result(
    stdout: str = _VALID_REPORT, stderr: str = "", exit_code: int = 1, timed_out: bool = False
) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.exit_code = exit_code
    result.timed_out = timed_out
    return result


# ── is_available ──────────────────────────────────────────────────────────────


class TestIsAvailable:
    def test_returns_true_when_binary_on_path(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        with patch("shutil.which", return_value="/usr/local/bin/contract-graph"):
            assert ContractGraphAdapter().is_available() is True

    def test_returns_false_when_binary_missing(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        with patch("shutil.which", return_value=None):
            assert ContractGraphAdapter().is_available() is False


# ── run — happy path ──────────────────────────────────────────────────────────


class TestAdapterRun:
    def test_maps_one_finding_from_valid_json(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        ctx = _make_ctx()

        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(exit_code=1),
        ):
            result = adapter.run(ctx)

        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.signal_type == "contract_graph_drift"
        assert f.severity.value == "high"
        assert f.title == "Field userId missing in consumer"

    def test_summary_contains_version_and_counts(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        ctx = _make_ctx()

        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(exit_code=1),
        ):
            result = adapter.run(ctx)

        assert "1.1.1" in result.summary
        assert "1 finding" in result.summary

    def test_exit_0_also_produces_findings(self):
        """exit 0 means no findings above --fail-on threshold but may still have lower-sev ones."""
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        ctx = _make_ctx()

        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(exit_code=0),
        ):
            result = adapter.run(ctx)

        assert len(result.findings) == 1  # same payload, exit code differs

    def test_metadata_contains_schema_version(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        with patch(
            "drift_contract_graph.adapter.run_command", return_value=_make_subprocess_result()
        ):
            result = adapter.run(_make_ctx())

        assert result.metadata["schema_version"] == "1.1"

    def test_trailing_rich_output_is_tolerated(self):
        """Rich console text after the JSON must not break parsing."""
        from drift_contract_graph.adapter import ContractGraphAdapter

        noisy = _VALID_REPORT + "\n\n\x1b[32m✓ Analysis complete\x1b[0m\n"
        adapter = ContractGraphAdapter()
        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(stdout=noisy),
        ):
            result = adapter.run(_make_ctx())

        assert len(result.findings) == 1


# ── run — failure modes ───────────────────────────────────────────────────────


class TestAdapterRunFailures:
    def test_exit_2_returns_empty_findings_with_summary(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(exit_code=2, stdout="", stderr="config error"),
        ):
            result = adapter.run(_make_ctx())

        assert result.findings == []
        assert "config error" in result.summary.lower() or "exit 2" in result.summary

    def test_exit_127_returns_empty_findings(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(exit_code=127, stdout=""),
        ):
            result = adapter.run(_make_ctx())

        assert result.findings == []

    def test_timeout_returns_empty_findings(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(timed_out=True, exit_code=1),
        ):
            result = adapter.run(_make_ctx())

        assert result.findings == []

    def test_invalid_json_returns_empty_findings(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(stdout="not json at all"),
        ):
            result = adapter.run(_make_ctx())

        assert result.findings == []
        assert "parse failed" in result.summary.lower() or "json" in result.summary.lower()

    def test_empty_stdout_returns_empty_findings(self):
        from drift_contract_graph.adapter import ContractGraphAdapter

        adapter = ContractGraphAdapter()
        with patch(
            "drift_contract_graph.adapter.run_command",
            return_value=_make_subprocess_result(stdout=""),
        ):
            result = adapter.run(_make_ctx())

        assert result.findings == []


# ── _parse_json_tolerant ──────────────────────────────────────────────────────


class TestParseJsonTolerant:
    def test_parses_clean_json(self):
        from drift_contract_graph.adapter import _parse_json_tolerant

        assert _parse_json_tolerant('{"key": 1}') == {"key": 1}

    def test_parses_json_with_prefix_text(self):
        from drift_contract_graph.adapter import _parse_json_tolerant

        result = _parse_json_tolerant('some prefix\n{"key": 1}')
        assert result == {"key": 1}

    def test_parses_json_with_suffix_text(self):
        from drift_contract_graph.adapter import _parse_json_tolerant

        result = _parse_json_tolerant('{"key": 1}\nsome suffix')
        assert result == {"key": 1}

    def test_returns_none_for_empty_string(self):
        from drift_contract_graph.adapter import _parse_json_tolerant

        assert _parse_json_tolerant("") is None

    def test_returns_none_for_no_braces(self):
        from drift_contract_graph.adapter import _parse_json_tolerant

        assert _parse_json_tolerant("just text without braces") is None

    def test_returns_none_for_malformed_json(self):
        from drift_contract_graph.adapter import _parse_json_tolerant

        assert _parse_json_tolerant("{broken json}}") is None

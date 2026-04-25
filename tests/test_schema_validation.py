"""Schema validation test — ensure contract-graph JSON output is schema-conformant."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestOutputSchemaConformance:
    """Verify that the JSON output conforms to the canonical output_schema.json."""

    @pytest.fixture
    def schema(self):
        """Load the canonical output schema."""
        schema_path = Path(__file__).parent.parent / "src" / "contract_graph" / "output_schema.json"
        with schema_path.open() as f:
            return json.load(f)

    @pytest.fixture
    def fixture_config(self) -> Path:
        """Fixture config pointing at fullstack_basic."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "fullstack_basic"
        return fixtures_dir / "contract-graph.yaml"

    def test_json_report_matches_schema(self, schema, fixture_config, tmp_path: Path):
        """Run CLI analyze and validate JSON output against schema."""
        from click.testing import CliRunner
        from contract_graph.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "analyze",
                "--config", str(fixture_config),
                "--root", str(fixture_config.parent),
                "--format", "json",
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Parse JSON output
        output = result.output.strip()
        report = json.loads(output)

        # Validate against schema
        try:
            jsonschema.validate(report, schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Schema validation failed: {e.message}\nSchema path: {e.schema_path}\nReport: {json.dumps(report, indent=2)}")

    def test_report_has_required_top_level_fields(self, fixture_config):
        """Verify required top-level fields are present."""
        from click.testing import CliRunner
        from contract_graph.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "analyze",
                "--config", str(fixture_config),
                "--root", str(fixture_config.parent),
                "--format", "json",
            ],
        )

        assert result.exit_code == 0
        report = json.loads(result.output.strip())

        # Check required top-level fields per output_schema.json
        assert "tool" in report, "Missing required field: tool"
        assert report["tool"] == "contract-graph", f"Tool should be 'contract-graph', got {report['tool']}"
        
        assert "version" in report, "Missing required field: version"
        assert isinstance(report["version"], str), "version should be a string"
        
        assert "findings" in report, "Missing required field: findings"
        assert isinstance(report["findings"], list), "findings should be a list"
        
        assert "summary" in report, "Missing required field: summary"
        assert isinstance(report["summary"], dict), "summary should be an object"

    def test_summary_has_required_fields(self, fixture_config):
        """Verify summary object has required fields."""
        from click.testing import CliRunner
        from contract_graph.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "analyze",
                "--config", str(fixture_config),
                "--root", str(fixture_config.parent),
                "--format", "json",
            ],
        )

        assert result.exit_code == 0
        report = json.loads(result.output.strip())
        summary = report["summary"]

        # Check required summary fields
        assert "total_findings" in summary, "summary missing: total_findings"
        assert isinstance(summary["total_findings"], int), "total_findings should be int"
        
        assert "by_severity" in summary, "summary missing: by_severity"
        by_sev = summary["by_severity"]
        assert isinstance(by_sev, dict), "by_severity should be dict"
        
        assert "score" in summary, "summary missing: score"
        score = summary["score"]
        assert isinstance(score, dict), "score should be dict"
        assert "overall" in score, "score missing: overall"

    def test_findings_items_have_required_fields(self, fixture_config):
        """Verify each finding has discoverer, severity, title."""
        from click.testing import CliRunner
        from contract_graph.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "analyze",
                "--config", str(fixture_config),
                "--root", str(fixture_config.parent),
                "--format", "json",
            ],
        )

        assert result.exit_code == 0
        report = json.loads(result.output.strip())
        findings = report["findings"]

        for i, finding in enumerate(findings):
            assert "discoverer" in finding, f"Finding {i} missing: discoverer"
            assert "severity" in finding, f"Finding {i} missing: severity"
            assert finding["severity"] in ("critical", "high", "medium", "low", "info"), \
                f"Finding {i} invalid severity: {finding['severity']}"
            assert "title" in finding, f"Finding {i} missing: title"

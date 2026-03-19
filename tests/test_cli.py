"""Tests for the CLI (click commands)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from contract_graph.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def config_file(fullstack_basic: Path, tmp_path: Path) -> Path:
    """Write a minimal config pointing at the fullstack_basic fixture."""
    config = {
        "discovery": {
            "api_type_sync": {
                "enabled": True,
                "provider_paths": ["backend/"],
                "consumer_paths": ["frontend/"],
                "naming_convention": "auto",
            }
        },
        "policy": {"fail_on": "high"},
        "scoring": {"weights": {"api_type_sync": 1.0}},
    }
    cfg = tmp_path / "contract-graph.yaml"
    cfg.write_text(yaml.dump(config))
    return cfg


class TestCLI:
    def test_version(self, runner: CliRunner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "contract-graph" in result.output or "0." in result.output

    def test_analyze_terminal(self, runner: CliRunner, config_file: Path, fullstack_basic: Path):
        result = runner.invoke(main, [
            "analyze",
            "--config", str(config_file),
            "--root", str(fullstack_basic),
            "--format", "terminal",
        ])
        assert result.exit_code == 0

    def test_analyze_json(self, runner: CliRunner, config_file: Path, fullstack_basic: Path):
        result = runner.invoke(main, [
            "analyze",
            "--config", str(config_file),
            "--root", str(fullstack_basic),
            "--format", "json",
        ])
        assert result.exit_code == 0
        # Should be valid JSON
        output = result.output.strip()
        parsed = json.loads(output)
        assert "findings" in parsed or "score" in parsed or "graph" in parsed

    def test_check_returns_exit_code(self, runner: CliRunner, config_file: Path, fullstack_basic: Path):
        result = runner.invoke(main, [
            "check",
            "--config", str(config_file),
            "--root", str(fullstack_basic),
            "--fail-on", "high",
        ])
        # Should either pass (0) or fail (1), not crash
        assert result.exit_code in (0, 1)

    def test_impact_command(self, runner: CliRunner, config_file: Path, fullstack_basic: Path):
        result = runner.invoke(main, [
            "impact",
            "backend/models.py",
            "--config", str(config_file),
            "--root", str(fullstack_basic),
        ])
        assert result.exit_code == 0

    def test_init_command(self, runner: CliRunner, tmp_path: Path):
        output_path = tmp_path / "contract-graph.yaml"
        result = runner.invoke(main, [
            "init",
            "--preset", "fullstack",
            "--output", str(output_path),
        ])
        assert result.exit_code == 0
        assert output_path.exists()

    def test_init_does_not_overwrite(self, runner: CliRunner, tmp_path: Path):
        output_path = tmp_path / "contract-graph.yaml"
        output_path.write_text("existing")
        result = runner.invoke(main, [
            "init",
            "--output", str(output_path),
        ], input="n\n")
        assert result.exit_code != 0 or "existing" == output_path.read_text()

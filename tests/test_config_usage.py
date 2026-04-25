"""Unit tests for config_usage discoverer."""

import pytest
from pathlib import Path
from contract_graph.discovery.config_usage import ConfigUsageDiscoverer
from contract_graph.graph.model import ContractGraph, NodeKind, EdgeKind


@pytest.fixture
def config_usage_discoverer():
    """Instantiate the config usage discoverer."""
    return ConfigUsageDiscoverer()


@pytest.fixture
def empty_graph():
    """Create an empty contract graph."""
    return ContractGraph()


def test_config_usage_discoverer_finds_python_os_getenv(tmp_path, config_usage_discoverer, empty_graph):
    """Test that os.getenv() calls are discovered in Python files."""
    py_file = tmp_path / "config.py"
    py_file.write_text(
        """
import os

API_KEY = os.getenv("API_KEY")
DEBUG = os.getenv('DEBUG', 'false')
"""
    )

    config = {
        "python_paths": ["**/*.py"],
        "typescript_paths": ["**/*.ts"],
    }

    nodes, edges = config_usage_discoverer.discover(empty_graph, config, str(tmp_path))

    # Should find API_KEY and DEBUG
    node_names = {n.name for n in nodes}
    assert "API_KEY" in node_names
    assert "DEBUG" in node_names

    # Both should be CONFIG_KEY nodes
    py_nodes = [n for n in nodes if n.metadata.get("language") == "python"]
    assert all(n.kind == NodeKind.CONFIG_KEY for n in py_nodes)


def test_config_usage_discoverer_finds_python_settings(tmp_path, config_usage_discoverer, empty_graph):
    """Test that settings.VAR_NAME patterns are discovered in Python files."""
    py_file = tmp_path / "app.py"
    py_file.write_text(
        """
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str

settings = Settings()

key = settings.API_KEY
debug = settings.DEBUG_MODE
"""
    )

    config = {
        "python_paths": ["**/*.py"],
        "typescript_paths": ["**/*.ts"],
    }

    nodes, edges = config_usage_discoverer.discover(empty_graph, config, str(tmp_path))

    node_names = {n.name for n in nodes}
    assert "API_KEY" in node_names
    assert "DEBUG_MODE" in node_names


def test_config_usage_discoverer_finds_typescript_process_env(tmp_path, config_usage_discoverer, empty_graph):
    """Test that process.env.VAR_NAME is discovered in TypeScript files."""
    ts_file = tmp_path / "config.ts"
    ts_file.write_text(
        """
const apiKey = process.env.API_KEY;
const debug = process.env["DEBUG_MODE"];
const port = process.env.PORT || 3000;
"""
    )

    config = {
        "python_paths": ["**/*.py"],
        "typescript_paths": ["**/*.ts"],
    }

    nodes, edges = config_usage_discoverer.discover(empty_graph, config, str(tmp_path))

    node_names = {n.name for n in nodes}
    assert "API_KEY" in node_names
    assert "DEBUG_MODE" in node_names
    assert "PORT" in node_names

    # All should be TypeScript nodes
    ts_nodes = [n for n in nodes if n.metadata.get("language") == "typescript"]
    assert len(ts_nodes) >= 3


def test_config_usage_discoverer_finds_typescript_import_meta_env(tmp_path, config_usage_discoverer, empty_graph):
    """Test that import.meta.env.VAR_NAME is discovered in TypeScript files."""
    ts_file = tmp_path / "vite.config.ts"
    ts_file.write_text(
        """
const apiUrl = import.meta.env.VITE_API_URL;
const isDev = import.meta.env.DEV;
"""
    )

    config = {
        "python_paths": ["**/*.py"],
        "typescript_paths": ["**/*.ts"],
    }

    nodes, edges = config_usage_discoverer.discover(empty_graph, config, str(tmp_path))

    node_names = {n.name for n in nodes}
    assert "VITE_API_URL" in node_names
    assert "DEV" in node_names


def test_config_usage_discoverer_creates_edges_for_matching_variables(tmp_path, config_usage_discoverer, empty_graph):
    """Test that edges are created between Python and TS for matching variables."""
    py_file = tmp_path / "config.py"
    py_file.write_text('API_KEY = os.getenv("API_KEY")')

    ts_file = tmp_path / "config.ts"
    ts_file.write_text('const apiKey = process.env.API_KEY;')

    config = {
        "python_paths": ["**/*.py"],
        "typescript_paths": ["**/*.ts"],
    }

    nodes, edges = config_usage_discoverer.discover(empty_graph, config, str(tmp_path))

    # Should have 2 nodes (Python + TypeScript)
    assert len(nodes) == 2

    # Should have 1 edge connecting them
    assert len(edges) == 1
    assert edges[0].kind == EdgeKind.CONFIG_USAGE
    assert edges[0].source == "config:API_KEY:python"
    assert edges[0].target == "config:API_KEY:typescript"


def test_config_usage_discoverer_no_edge_for_unmatched_variables(
    tmp_path, config_usage_discoverer, empty_graph
):
    """Test that no edge is created for variables present in only one language."""
    py_file = tmp_path / "config.py"
    py_file.write_text('PYTHON_ONLY = os.getenv("PYTHON_ONLY")')

    ts_file = tmp_path / "config.ts"
    ts_file.write_text('const tsOnly = process.env.TS_ONLY;')

    config = {
        "python_paths": ["**/*.py"],
        "typescript_paths": ["**/*.ts"],
    }

    nodes, edges = config_usage_discoverer.discover(empty_graph, config, str(tmp_path))

    # Should have 2 nodes but 0 edges
    assert len(nodes) == 2
    assert len(edges) == 0


def test_config_usage_discoverer_handles_missing_files(tmp_path, config_usage_discoverer, empty_graph):
    """Test that missing paths don't cause errors."""
    config = {
        "python_paths": ["**/*.py"],
        "typescript_paths": ["**/*.ts"],
    }

    # tmp_path has no files, but should not crash
    nodes, edges = config_usage_discoverer.discover(empty_graph, config, str(tmp_path))

    assert len(nodes) == 0
    assert len(edges) == 0

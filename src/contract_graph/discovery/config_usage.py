"""Config Usage Discoverer — matches environment variables and config usage across Python/TypeScript."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from contract_graph.discovery.base import BaseDiscoverer, DiscovererRegistry
from contract_graph.graph.model import (
    ContractEdge,
    ContractGraph,
    ContractNode,
    EdgeKind,
    NodeKind,
)

logger = logging.getLogger(__name__)


@DiscovererRegistry.register
class ConfigUsageDiscoverer(BaseDiscoverer):
    """Discovers environment variables and config usage patterns across Python/TypeScript."""

    name: str = "config_usage"

    def discover(
        self,
        graph: ContractGraph,
        config: dict[str, Any],
        root: str,
    ) -> tuple[list[ContractNode], list[ContractEdge]]:
        """Discover config variable usage patterns.

        Config structure (from contract-graph.yaml):
            config_usage:
              enabled: true
              python_paths: ["backend/**/*.py"]
              typescript_paths: ["frontend/**/*.ts"]

        Returns nodes for each variable and edges representing usage in Python/TS.
        """
        new_nodes: list[ContractNode] = []
        new_edges: list[ContractEdge] = []

        root_path = Path(root)

        # Parse config
        python_paths = config.get("python_paths", ["**/*.py"])
        typescript_paths = config.get("typescript_paths", ["**/*.ts", "**/*.tsx"])

        # Discover Python config usage
        py_vars = self._discover_python_config(root_path, python_paths)
        for var_name, locations in py_vars.items():
            first_loc = locations[0]
            node = ContractNode(
                id=f"config:{var_name}:python",
                name=var_name,
                kind=NodeKind.CONFIG_KEY,
                file_path=first_loc["file"],
                line_start=first_loc["line"],
                line_end=first_loc["line"],
                metadata={"language": "python", "usage_count": len(locations)},
            )
            new_nodes.append(node)

        # Discover TypeScript config usage
        ts_vars = self._discover_typescript_config(root_path, typescript_paths)
        for var_name, locations in ts_vars.items():
            first_loc = locations[0]
            node = ContractNode(
                id=f"config:{var_name}:typescript",
                name=var_name,
                kind=NodeKind.CONFIG_KEY,
                file_path=first_loc["file"],
                line_start=first_loc["line"],
                line_end=first_loc["line"],
                metadata={"language": "typescript", "usage_count": len(locations)},
            )
            new_nodes.append(node)

        # Create edges between Python and TypeScript usage of same variable
        for var_name in py_vars:
            if var_name in ts_vars:
                edge = ContractEdge(
                    source=f"config:{var_name}:python",
                    target=f"config:{var_name}:typescript",
                    kind=EdgeKind.CONFIG_USAGE,
                )
                new_edges.append(edge)

        return new_nodes, new_edges

    def _discover_python_config(
        self, root: Path, patterns: list[str]
    ) -> dict[str, list[dict]]:
        """Discover environment variable usage in Python files.

        Recognizes:
        - os.getenv("VAR_NAME")
        - os.environ["VAR_NAME"]
        - settings.VAR_NAME (Pydantic settings)
        """
        variables: dict[str, list[dict]] = {}

        for pattern in patterns:
            for py_file in root.glob(pattern):
                if not py_file.is_file():
                    continue
                try:
                    content = py_file.read_text(encoding="utf-8", errors="replace")
                    lines = content.split("\n")

                    # os.getenv("VAR_NAME") or os.getenv('VAR_NAME')
                    for i, line in enumerate(lines, 1):
                        # os.getenv patterns
                        for match in re.finditer(r'os\.getenv\(["\']([A-Z_][A-Z0-9_]*)["\']', line):
                            var_name = match.group(1)
                            if var_name not in variables:
                                variables[var_name] = []
                            variables[var_name].append(
                                {"file": py_file, "line": i, "context": "os.getenv"}
                            )

                        # os.environ["VAR_NAME"] patterns
                        for match in re.finditer(r'os\.environ\[["\']([A-Z_][A-Z0-9_]*)["\']', line):
                            var_name = match.group(1)
                            if var_name not in variables:
                                variables[var_name] = []
                            variables[var_name].append(
                                {"file": py_file, "line": i, "context": "os.environ"}
                            )

                        # settings.VAR_NAME pattern (common in Pydantic settings)
                        for match in re.finditer(r'settings\.([A-Z_][A-Z0-9_]*)', line):
                            var_name = match.group(1)
                            if var_name not in variables:
                                variables[var_name] = []
                            variables[var_name].append(
                                {"file": py_file, "line": i, "context": "settings"}
                            )

                except (OSError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not read Python file {py_file}: {e}")
                    continue

        return variables

    def _discover_typescript_config(
        self, root: Path, patterns: list[str]
    ) -> dict[str, list[dict]]:
        """Discover environment variable usage in TypeScript files.

        Recognizes:
        - process.env.VAR_NAME
        - import.meta.env.VAR_NAME
        - process.env["VAR_NAME"]
        """
        variables: dict[str, list[dict]] = {}

        for pattern in patterns:
            for ts_file in root.glob(pattern):
                if not ts_file.is_file():
                    continue
                try:
                    content = ts_file.read_text(encoding="utf-8", errors="replace")
                    lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        # process.env.VAR_NAME
                        for match in re.finditer(r'process\.env\.([A-Z_][A-Z0-9_]*)', line):
                            var_name = match.group(1)
                            if var_name not in variables:
                                variables[var_name] = []
                            variables[var_name].append(
                                {"file": ts_file, "line": i, "context": "process.env"}
                            )

                        # import.meta.env.VAR_NAME
                        for match in re.finditer(r'import\.meta\.env\.([A-Z_][A-Z0-9_]*)', line):
                            var_name = match.group(1)
                            if var_name not in variables:
                                variables[var_name] = []
                            variables[var_name].append(
                                {"file": ts_file, "line": i, "context": "import.meta.env"}
                            )

                        # process.env["VAR_NAME"]
                        for match in re.finditer(r'process\.env\[["\']([A-Z_][A-Z0-9_]*)["\']', line):
                            var_name = match.group(1)
                            if var_name not in variables:
                                variables[var_name] = []
                            variables[var_name].append(
                                {"file": ts_file, "line": i, "context": "process.env[]"}
                            )

                except (OSError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not read TypeScript file {ts_file}: {e}")
                    continue

        return variables

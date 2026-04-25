"""Route Activation Discoverer — matches FastAPI routes to TypeScript service calls."""

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
class RouteActivationDiscoverer(BaseDiscoverer):
    """Discovers backend routes and their usage in frontend service clients."""

    name: str = "route_activation"

    def discover(
        self,
        graph: ContractGraph,
        config: dict[str, Any],
        root: str,
    ) -> tuple[list[ContractNode], list[ContractEdge]]:
        """Discover route activation patterns.

        Config structure (from contract-graph.yaml):
            route_activation:
              enabled: true
              backend_paths: ["backend/**/*.py"]
              frontend_paths: ["frontend/**/*.ts"]

        Returns nodes for each route and edges representing calls in frontend.
        """
        new_nodes: list[ContractNode] = []
        new_edges: list[ContractEdge] = []

        root_path = Path(root)

        # Parse config
        backend_paths = config.get("backend_paths", ["**/*.py"])
        frontend_paths = config.get("frontend_paths", ["**/*.ts", "**/*.tsx"])

        # Discover backend routes (FastAPI)
        backend_routes = self._discover_backend_routes(root_path, backend_paths)
        route_by_path: dict[str, dict] = {}

        for route_info in backend_routes:
            route_id = f"route:{route_info['method']}:{route_info['path']}"
            node = ContractNode(
                id=route_id,
                name=f"{route_info['method'].upper()} {route_info['path']}",
                kind=NodeKind.BACKEND_ROUTE,
                file_path=route_info["file"],
                line_start=route_info["line"],
                line_end=route_info["line"],
                metadata={
                    "method": route_info["method"],
                    "path": route_info["path"],
                    "handler": route_info.get("handler", "unknown"),
                },
            )
            new_nodes.append(node)
            route_by_path[route_id] = route_info

        # Discover frontend route calls (fetch/axios/services)
        frontend_calls = self._discover_frontend_calls(root_path, frontend_paths)
        for call_info in frontend_calls:
            call_id = f"call:{call_info['method']}:{call_info['path']}"
            node = ContractNode(
                id=call_id,
                name=f"{call_info['method'].upper()} {call_info['path']}",
                kind=NodeKind.FRONTEND_CALL,
                file_path=call_info["file"],
                line_start=call_info["line"],
                line_end=call_info["line"],
                metadata={
                    "method": call_info["method"],
                    "path": call_info["path"],
                    "context": call_info.get("context", "unknown"),
                },
            )
            new_nodes.append(node)

            # Try to match with backend route
            for route_id, route_info in route_by_path.items():
                if self._routes_match(route_info["path"], call_info["path"]):
                    edge = ContractEdge(
                        source=route_id,
                        target=call_id,
                        kind=EdgeKind.ROUTE_ACTIVATION,
                        confidence=0.9,
                    )
                    new_edges.append(edge)
                    break

        return new_nodes, new_edges

    def _discover_backend_routes(
        self, root: Path, patterns: list[str]
    ) -> list[dict]:
        """Discover FastAPI/Flask routes in Python files.

        Recognizes:
        - @router.get("/path")
        - @router.post("/path")
        - @app.route("/path", methods=["GET"])
        """
        routes: list[dict] = []

        for pattern in patterns:
            for py_file in root.glob(pattern):
                if not py_file.is_file():
                    continue
                try:
                    content = py_file.read_text(encoding="utf-8", errors="replace")
                    lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        # @router.get/post/put/delete("/path")
                        for match in re.finditer(
                            r'@(?:router|app)\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']',
                            line
                        ):
                            method = match.group(1)
                            path = match.group(2)
                            routes.append({
                                "file": py_file,
                                "line": i,
                                "method": method,
                                "path": path,
                                "handler": self._extract_handler_name(lines, i),
                            })

                        # @app.route("/path", methods=["GET", ...])
                        for match in re.finditer(
                            r'@(?:app|router)\.route\(["\']([^"\']+)["\'].*methods=\[([^\]]+)\]',
                            line
                        ):
                            path = match.group(1)
                            methods_str = match.group(2)
                            methods = re.findall(r'["\']([A-Z]+)["\']', methods_str)
                            for method in methods:
                                routes.append({
                                    "file": py_file,
                                    "line": i,
                                    "method": method.lower(),
                                    "path": path,
                                    "handler": self._extract_handler_name(lines, i),
                                })

                except (OSError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not read backend file {py_file}: {e}")
                    continue

        return routes

    def _discover_frontend_calls(
        self, root: Path, patterns: list[str]
    ) -> list[dict]:
        """Discover HTTP calls in TypeScript files.

        Recognizes:
        - fetch("/api/path", {method: "GET"})
        - axios.get("/api/path")
        - client.post("/api/path")
        """
        calls: list[dict] = []

        for pattern in patterns:
            for ts_file in root.glob(pattern):
                if not ts_file.is_file():
                    continue
                try:
                    content = ts_file.read_text(encoding="utf-8", errors="replace")
                    lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        # fetch("/path") without method (defaults to GET)
                        for match in re.finditer(
                            r'fetch\(["\']([^"\']+)["\']',
                            line
                        ):
                            path = match.group(1)
                            # Check if there's a method specified
                            method_match = re.search(r'method\s*:\s*["\']([A-Z]+)["\']', line)
                            method = method_match.group(1).lower() if method_match else "get"
                            calls.append({
                                "file": ts_file,
                                "line": i,
                                "method": method,
                                "path": path,
                                "context": "fetch",
                            })

                        # axios.get/post/put/delete("/path")
                        for match in re.finditer(
                            r'axios\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                            line
                        ):
                            method = match.group(1)
                            path = match.group(2)
                            calls.append({
                                "file": ts_file,
                                "line": i,
                                "method": method,
                                "path": path,
                                "context": "axios",
                            })

                        # client.get/post/put/delete("/path")
                        for match in re.finditer(
                            r'(?:client|service)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                            line
                        ):
                            method = match.group(1)
                            path = match.group(2)
                            calls.append({
                                "file": ts_file,
                                "line": i,
                                "method": method,
                                "path": path,
                                "context": "client",
                            })

                except (OSError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not read frontend file {ts_file}: {e}")
                    continue

        return calls

    def _routes_match(self, backend_path: str, frontend_path: str) -> bool:
        """Check if a backend route path matches a frontend call path.

        Handles path parameter variations like /users/{id} vs /users/:id vs /users/123
        """
        # Normalize paths
        backend = backend_path.lower().strip("/")
        frontend = frontend_path.lower().strip("/")

        # If they're exactly equal, they match
        if backend == frontend:
            return True

        # Convert /path/{id} to /path/:param for comparison
        backend_normalized = re.sub(r'\{[^}]+\}', ':param', backend)
        frontend_normalized = re.sub(r'\{[^}]+\}', ':param', frontend)

        if backend_normalized == frontend_normalized:
            return True

        # For path parameters in frontend (e.g., /users/123), match against backend pattern
        # Split paths into segments and compare
        backend_segments = backend_normalized.split("/")
        frontend_segments = frontend_normalized.split("/")

        # If they don't have the same number of segments, no match
        if len(backend_segments) != len(frontend_segments):
            return False

        # Compare segment by segment
        for bs, fs in zip(backend_segments, frontend_segments):
            # If backend segment is :param, it matches anything
            if bs == ":param":
                continue
            # If frontend segment is :param, it matches anything
            if fs == ":param":
                continue
            # Otherwise, they must be equal
            if bs != fs:
                return False

        return True

    def _extract_handler_name(self, lines: list[str], decorator_line: int) -> str:
        """Extract the function name following a route decorator."""
        for i in range(decorator_line, min(decorator_line + 5, len(lines))):
            line = lines[i]
            match = re.search(r'(?:async\s+)?def\s+(\w+)\s*\(', line)
            if match:
                return match.group(1)
        return "unknown"

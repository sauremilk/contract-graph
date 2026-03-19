"""Base discoverer ABC and registry for pluggable contract discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from contract_graph.graph.model import ContractEdge, ContractGraph, ContractNode


class BaseDiscoverer(ABC):
    """Abstract base for all contract discoverers."""

    name: str = "base"

    @abstractmethod
    def discover(
        self,
        graph: ContractGraph,
        config: dict[str, Any],
        root: str,
    ) -> tuple[list[ContractNode], list[ContractEdge]]:
        """Discover contracts and return nodes + edges to add to the graph.

        Args:
            graph: The current contract graph (may already have nodes from other discoverers).
            config: The discoverer-specific config section from contract-graph.yaml.
            root: The root directory of the project being analyzed.

        Returns:
            Tuple of (new_nodes, new_edges) to add to the graph.
        """
        ...


class DiscovererRegistry:
    """Registry for discoverer classes."""

    _discoverers: dict[str, type[BaseDiscoverer]] = {}

    @classmethod
    def register(cls, discoverer_cls: type[BaseDiscoverer]) -> type[BaseDiscoverer]:
        """Register a discoverer class. Can be used as decorator."""
        cls._discoverers[discoverer_cls.name] = discoverer_cls
        return discoverer_cls

    @classmethod
    def get(cls, name: str) -> type[BaseDiscoverer] | None:
        return cls._discoverers.get(name)

    @classmethod
    def all(cls) -> dict[str, type[BaseDiscoverer]]:
        return dict(cls._discoverers)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BaseDiscoverer | None:
        """Create an instance of a registered discoverer."""
        dcls = cls._discoverers.get(name)
        if dcls is None:
            return None
        return dcls(**kwargs)

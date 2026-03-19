"""Graph builder — constructs ContractGraph from discovered contracts."""

from __future__ import annotations

from contract_graph.graph.model import ContractEdge, ContractGraph, ContractNode


class GraphBuilder:
    """Incrementally builds a ContractGraph from parsed data."""

    def __init__(self) -> None:
        self._graph = ContractGraph()

    def add_node(self, node: ContractNode) -> None:
        """Add a node, deduplicating by ID."""
        self._graph.add_node(node)

    def add_edge(self, edge: ContractEdge) -> None:
        """Add an edge between two nodes."""
        self._graph.add_edge(edge)

    def merge_nodes(self, nodes: list[ContractNode]) -> None:
        """Add multiple nodes at once."""
        for node in nodes:
            self.add_node(node)

    def merge_edges(self, edges: list[ContractEdge]) -> None:
        """Add multiple edges at once."""
        for edge in edges:
            self.add_edge(edge)

    def build(self) -> ContractGraph:
        """Return the constructed graph."""
        return self._graph

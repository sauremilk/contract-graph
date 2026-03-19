"""Discovery package — pluggable contract discoverers."""

from contract_graph.discovery.base import BaseDiscoverer, DiscovererRegistry

__all__ = ["BaseDiscoverer", "DiscovererRegistry"]

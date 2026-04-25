"""Discovery package — auto-registers built-in discoverers on import."""

from contract_graph.discovery import api_type_sync as _api_type_sync  # noqa: F401 (registers discoverer)
from contract_graph.discovery.base import BaseDiscoverer, DiscovererRegistry

__all__ = ["BaseDiscoverer", "DiscovererRegistry"]

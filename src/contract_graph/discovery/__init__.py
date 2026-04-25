"""Discovery package — auto-registers built-in discoverers on import."""

from contract_graph.discovery import api_type_sync as _api_type_sync  # noqa: F401 (registers discoverer)
from contract_graph.discovery import config_usage as _config_usage  # noqa: F401 (registers discoverer)
from contract_graph.discovery import route_activation as _route_activation  # noqa: F401 (registers discoverer)
from contract_graph.discovery.base import BaseDiscoverer, DiscovererRegistry

__all__ = ["BaseDiscoverer", "DiscovererRegistry"]

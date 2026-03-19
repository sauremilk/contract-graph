"""Policy package — auto-registers built-in rules on import."""

from contract_graph.policy import rules as _rules  # noqa: F401 (sideeffect: registers rules)

__all__ = ["rules"]

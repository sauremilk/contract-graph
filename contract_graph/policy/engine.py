"""Policy engine — evaluates rules against the contract graph."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from contract_graph.graph.model import ContractGraph, Finding

# Rule function type: (graph, config) -> list of findings
RuleFunc = Callable[[ContractGraph, dict[str, Any]], list[Finding]]

# Global rule registry
_RULES: dict[str, RuleFunc] = {}


def register_rule(func: RuleFunc) -> RuleFunc:
    """Decorator to register a policy rule."""
    _RULES[func.__name__] = func
    return func


def get_rule(name: str) -> RuleFunc | None:
    return _RULES.get(name)


def all_rules() -> dict[str, RuleFunc]:
    return dict(_RULES)


class PolicyEngine:
    """Evaluates registered rules against a ContractGraph."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.policies: list[dict[str, Any]] = self.config.get("policies", [])

    def evaluate(self, graph: ContractGraph) -> list[Finding]:
        """Run all enabled policy rules and return findings.

        If policy rules are configured, only rule-generated findings are returned
        (not graph.findings()) to avoid duplicates, since rules iterate over the
        same edge mismatches that graph.findings() would report.
        """
        all_findings: list[Finding] = []

        # Run policy rules
        has_rules = False
        for policy in self.policies:
            name = policy.get("name", "")
            enabled = policy.get("enabled", True)
            if not enabled:
                continue

            rule = get_rule(name)
            if rule is None:
                continue

            has_rules = True
            rule_findings = rule(graph, self.config)

            # Override severity from policy config
            policy_severity = policy.get("severity")
            if policy_severity:
                from contract_graph.graph.model import Severity

                try:
                    sev = Severity(policy_severity)
                    for f in rule_findings:
                        f.severity = sev
                except ValueError:
                    pass

            all_findings.extend(rule_findings)

        # Fallback: if no rules configured, use graph-level findings
        if not has_rules:
            all_findings.extend(graph.findings())

        return all_findings

    def evaluate_gate(self, graph: ContractGraph, fail_on: str = "high") -> tuple[bool, list[Finding]]:
        """Run evaluation and determine if the gate passes.

        Returns (passed, findings). passed=False means findings exceed the threshold.
        """
        from contract_graph.graph.model import Severity

        findings = self.evaluate(graph)
        severity_order = [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
            Severity.INFO,
        ]

        try:
            threshold = Severity(fail_on)
        except ValueError:
            threshold = Severity.HIGH

        threshold_idx = severity_order.index(threshold)
        blocking_severities = set(severity_order[: threshold_idx + 1])

        blocking = [f for f in findings if f.severity in blocking_severities]
        return len(blocking) == 0, findings

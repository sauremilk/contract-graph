---
name: Bug report
about: Something is broken or behaving unexpectedly
title: "bug: <short description>"
labels: ["bug", "needs-triage"]
assignees: []
---

## Describe the bug

<!-- A clear, concise description of what is wrong. -->

## Steps to reproduce

```bash
# Minimal reproduction — ideally a single contract-graph analyze invocation
contract-graph analyze --config <path>
```

## Expected behaviour

<!-- What should happen. -->

## Actual behaviour

<!-- What actually happens. Include full terminal output or JSON report if relevant. -->

## Environment

| Field | Value |
|-------|-------|
| contract-graph version | <!-- `contract-graph --version` --> |
| Python version | <!-- `python --version` --> |
| OS | <!-- e.g. macOS 14, Ubuntu 22.04, Windows 11 --> |
| Installation method | <!-- pip / uv / pipx --> |

## Additional context

<!-- Attach config YAML, sample source files, or screenshots if helpful. -->
<!-- Never include real credentials or secrets. -->

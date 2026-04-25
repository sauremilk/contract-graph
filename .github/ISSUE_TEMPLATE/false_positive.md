---
name: False positive / false negative report
about: A finding was raised that should not be (FP) or a real drift was missed (FN)
title: "eval: <FP|FN> — <short description>"
labels: ["eval", "false-positive", "needs-triage"]
assignees: []
---

## Finding type

- [ ] **False positive** — contract-graph raised a finding that is not a real drift
- [ ] **False negative** — contract-graph missed a real drift that should be flagged

## Minimal reproduction

Provide the smallest possible source files that demonstrate the issue.

**Backend (Python/Pydantic):**

```python
# paste relevant model / route snippet
```

**Frontend (TypeScript):**

```typescript
// paste relevant interface / type snippet
```

**Config (`contract-graph.yaml`):**

```yaml
# paste relevant config
```

**Finding produced (or missing):**

```json
# paste the JSON finding or describe what was expected
```

## Expected behaviour

<!-- What finding should (or should not) appear? -->

## contract-graph version

<!-- `contract-graph --version` -->

## Additional context

<!-- Any other parser, discoverer, or graph context that might help. -->

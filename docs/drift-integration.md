<!-- drift Integration Guide -->

# contract-graph ↔ drift Integration

`contract-graph` and `drift` are complementary tools for comprehensive reliability engineering:

- **contract-graph**: Detects static cross-boundary contract drift (Pydantic ↔ TypeScript type mismatches)
- **drift**: Broader reliability tracking, including contract findings, deployment signals, and system health

## Integration Architecture

```text
contract-graph analyze --format json
        ↓
    JSON Report
        ↓
  drift ingest
        ↓
  Unified Dashboard
```

## CLI Integration

### Standalone Analysis

```bash
contract-graph analyze --format json
```

Output is printed to stdout as structured JSON conforming to [`output_schema.json`](../src/contract_graph/output_schema.json).

### Pipe to drift

```bash
contract-graph analyze --format json | drift ingest
```

This pipes the JSON report directly to `drift ingest`, which ingests findings into its unified workspace.

### CI Gate + Pipe

```bash
contract-graph check --fail-on high && contract-graph analyze --format json | drift ingest
```

Checks pass (exit 0), then pipes findings to drift for visibility and trending.

## Output Schema Contract

The JSON output from `contract-graph analyze --format json` conforms to the canonical schema:

**Location:** `src/contract_graph/output_schema.json`

**Top-level structure:**

```json
{
  "tool": "contract-graph",
  "version": "1.x.y",
  "findings": [
    {
      "discoverer": "api_type_sync",
      "severity": "high|medium|low|critical|info",
      "title": "...",
      "description": "...",
      "provider_file": "...",
      "provider_name": "...",
      "provider_line": 0,
      "consumer_file": "...",
      "consumer_name": "...",
      "consumer_line": 0,
      "field_name": "...",
      "mismatch_kind": "missing_in_consumer|missing_in_provider|type_incompatible|optionality_mismatch",
      "fix_suggestion": "..."
    }
  ],
  "summary": {
    "total_findings": 0,
    "by_severity": {
      "critical": 0,
      "high": 0,
      "medium": 0,
      "low": 0,
      "info": 0
    },
    "score": {
      "overall": 0.85,
      "grade": "B"
    },
    "analyzed_at": "2026-04-25T...",
    "duration_seconds": 0.42
  },
  "contract_graph": {
    "nodes": 10,
    "edges": 5
  }
}
```

## Field Semantics for drift Ingestion

When drift consumes contract-graph findings, these fields are critical:

| Field | Semantics | drift Use |
|-------|-----------|-----------|
| `severity` | Finding severity (high → critical, medium → warning) | Gate decisions, priority ranking |
| `title` | Human-readable problem title | Dashboard display, issue title |
| `description` | Detailed explanation | Issue body, root cause tracking |
| `provider_file` | Backend file path (Python) | Change tracking, blame |
| `consumer_file` | Frontend file path (TypeScript) | Change impact, scope |
| `field_name` | Contract field that drifted | Regression tracking |
| `mismatch_kind` | Drift category | Reporting, filtering |
| `fix_suggestion` | Recommended fix action | Remediation guidance |

## Architecture Decision: Standalone CLI

As of v1, `contract-graph` remains a **standalone CLI tool**, not a drift subcommand.

**Rationale:**

- contract-graph can be used independently for local contract analysis
- Pipe model (`... | drift ingest`) enables flexible composition and future tool chains
- Decouples contract-graph release cycle from drift

**Future (v2+):** Integration tighter if unified command-line becomes necessary.

## Example: Full CI Workflow

```bash
#!/bin/bash

# Run contract analysis with gating
contract-graph check --fail-on high \
  --config ./contract-graph.yaml \
  --root .

# If gate passes, pipe findings to drift dashboard
if [ $? -eq 0 ]; then
  contract-graph analyze --format json \
    --config ./contract-graph.yaml \
    --root . | drift ingest
fi
```

## Output Validation

All JSON output is validated against the canonical schema on every run.
Tests verify:

- Required top-level fields (`tool`, `version`, `findings`, `summary`)
- Required `summary` fields (`total_findings`, `by_severity`, `score`)
- Finding object structure (severity, title, provider/consumer fields)
- Severity enum values (critical, high, medium, low, info)

Run validation tests:

```bash
pytest tests/test_schema_validation.py -v
```

## Troubleshooting

### "tool" field missing from output

→ Upgrade to latest contract-graph version (v1.1.0+) where schema conformance is enforced.

### Findings not appearing in drift dashboard

→ Verify `drift ingest` is installed and in PATH: `which drift`
→ Check drift ingestion logs for parse errors

### CI gate passing but no findings piped to drift

→ This is expected: no findings = gate passes = nothing to ingest
→ To force ingestion of empty report: modify CI script to unconditionally pipe `analyze` after `check`

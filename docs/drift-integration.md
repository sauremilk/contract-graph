<!-- drift Integration Guide -->

# contract-graph ↔ drift Integration

`contract-graph` and `drift` are complementary tools for comprehensive reliability engineering:

- **contract-graph**: Detects static cross-boundary contract drift (Pydantic ↔ TypeScript type mismatches)
- **drift**: Broader reliability tracking, including contract findings, deployment signals, and system health

## Integration Options

### Option A — Native adapter (recommended)

Install the `drift-contract-graph` adapter package (in `drift-contract-graph/`).
drift will auto-discover it via the `drift.integrations` entry-point and run it
as part of every `drift analyze` invocation.

```bash
pip install drift-contract-graph
drift analyze   # contract-graph findings appear as native drift Findings
```

The adapter also registers the `drift contracts` CLI subcommand:

```bash
drift contracts analyze .           # full analysis, terminal output
drift contracts check --fail-on high  # CI gate
drift contracts show-mapping .      # inspect the drift Finding representation
```

### Option B — Pipe-based (no adapter required)

```bash
contract-graph analyze --format json | drift ingest
```

### Option C — CI Gate + Pipe

```bash
contract-graph check --fail-on high && contract-graph analyze --format json | drift ingest
```

## Integration Architecture (Option A)

```text
drift analyze
  └─ IntegrationRunner.run_all()
       └─ ContractGraphAdapter.run(ctx)
            └─ subprocess: contract-graph analyze {repo_path} --format json
                 └─ JSON stdout
                      └─ map_findings() → list[drift.models.Finding]
```

**Finding mapping:**

| drift.models.Finding field | Source |
|---|---|
| `signal_type` | `"contract_graph_drift"` |
| `severity` | `finding.severity` (same enum values) |
| `score` | severity-derived (critical=1.0 … info=0.0) |
| `title` | `finding.title` |
| `description` | `finding.description` |
| `file_path` | `consumer_file` (primary violation location) |
| `fix` | `finding.fix_suggestion` |
| `root_cause` | `finding.mismatch_kind` |
| `metadata["contract_graph"]` | Full contract-graph payload + `finding_id` |

## Output Schema Contract (schema_version 1.1)

The JSON output from `contract-graph analyze --format json` conforms to the canonical schema:

**Location:** `src/contract_graph/output_schema.json`

**Top-level structure:**

```json
{
  "tool": "contract-graph",
  "version": "1.x.y",
  "schema_version": "1.1",
  "findings": [
    {
      "finding_id": "CG-e8276e8efe7b",
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
    "by_severity": { "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0 },
    "score": { "overall": 0.85, "grade": "B" },
    "analyzed_at": "2026-04-25T...",
    "duration_seconds": 0.42
  },
  "contract_graph": { "nodes": 10, "edges": 5 }
}
```

### Schema versioning policy

`schema_version` follows `MAJOR.MINOR` semantics:

- **Minor bump** (e.g. `1.1 → 1.2`): additive new fields; downstream consumers must handle unknown fields gracefully (`additionalProperties: true`).
- **Major bump** (e.g. `1.x → 2.0`): breaking — field removals or renames. Announced in CHANGELOG with migration guide.

### `finding_id` stability guarantee

`finding_id` (`CG-<sha256[:12]>`) is computed from `discoverer + provider_file + consumer_file + field_name + mismatch_kind`.
It is **stable across re-runs on unchanged code**, enabling drift-level deduplication and trending.



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

# drift-contract-graph

A **drift** integration adapter that surfaces `contract-graph` cross-boundary contract findings as native drift `Finding` objects.

## What it does

`contract-graph analyze --format json` is invoked as a subprocess. Its structured JSON output is parsed and each finding is mapped to a drift `Finding` with:

| drift field | source |
|---|---|
| `signal_type` | `"contract_graph_drift"` |
| `severity` | directly from contract-graph (same enum values) |
| `score` | severity-derived (`critical=1.0 … info=0.0`) |
| `title` | `finding.title` |
| `description` | `finding.description` |
| `file_path` | `consumer_file` (primary violation location) |
| `fix` | `finding.fix_suggestion` |
| `root_cause` | `finding.mismatch_kind` |
| `metadata` | full contract-graph finding dict + `finding_id` |

## Installation

```bash
pip install drift-contract-graph
```

With both `drift` and `contract-graph` installed, drift will automatically discover the adapter and the `drift contracts` CLI subcommand.

## Usage

### Via `drift.yaml`

No YAML configuration required — the adapter is auto-discovered.  
To pin trigger signals:

```yaml
integrations:
  adapters:
    - name: contract-graph
      enabled: true
      trigger_signals:
        - doc_impl_drift
        - system_misalignment
```

### Via CLI

```bash
drift contracts analyze --repo .
drift contracts check --fail-on high
```

### Manual invocation

```python
from drift_contract_graph.adapter import ContractGraphAdapter
from drift.integrations.base import IntegrationContext
from pathlib import Path

adapter = ContractGraphAdapter()
result = adapter.run(IntegrationContext(repo_path=Path("."), findings=[], config=...))
print(result.findings)
```

## Precision / Recall

| Metric | Baseline | Goal |
|---|---|---|
| Precision | — | ≥ 90% |
| Recall | — | ≥ 85% |
| FP Rate | — | < 10% |

Run the eval suite: `pytest tests/evals/ -v`

## Architecture

```
drift analyze
  └─ IntegrationRunner.run_all()
       └─ ContractGraphAdapter.run(ctx)
            └─ subprocess: contract-graph analyze {repo_path} --format json
                 └─ JSON stdout → parse → map_finding() → drift.Finding
```

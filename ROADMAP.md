# Roadmap

## Implementation Status (Phase 1 Audit)

As of 25 April 2026, the following modules have been audited for v1 readiness:

| Module | Status | Evidence |
|--------|--------|----------|
| `parsing/` | ✅ Functional | `python_parser.py`, `typescript_parser.py`, `yaml_parser.py` fully implemented with AST traversal and field extraction. |
| `discovery/` | ⚠️ Stub | Only `api_type_sync` implemented; `config_usage` and `route_activation` in config but not as discoverers. |
| `graph/` | ✅ Functional | `model.py`, `builder.py`, `impact.py` fully implemented with networkx-backed graph and traversal. |
| `policy/` | ✅ Functional | `engine.py` and `rules.py` with rule registry and 5 built-in policy rules. |
| `reporting/` | ⚠️ Stub | Reporters exist but JSON output structure not yet schema-conformant to `output_schema.json`. |
| `scoring/` | ✅ Functional | Severity-weighted scorer fully implemented in `scorer.py`. |
| `cli.py` | ✅ Functional | Full pipeline with `analyze`/`check`/`impact`/`init` commands. |
| `config.py` | ✅ Functional | Pydantic v2 config models, loading, and presets. |

## v1 Scope (Current Release Target)

**In Scope:**
- Parse Pydantic models from Python and TypeScript interfaces from `.ts` files
- Discover contracts via `api_type_sync`: match Python models → TypeScript interfaces
- Detect 3 core mismatch families:
  1. Missing field in consumer
  2. Type incompatibility 
  3. Optionality mismatch
- Policy engine converts mismatches to findings with severity levels
- Terminal and JSON report output (JSON must be schema-conformant)
- CI gating: `contract-graph check --fail-on high`

**Out of Scope (v1):**
- Additional discoverers: `config_usage`, `route_activation`
- OpenAPI-aware correlation
- SARIF output format
- Performance optimization / incremental builds
- Multi-repo workflows
- Language plugins beyond Python/TypeScript

## v2 Target

- Route activation and config usage discoverers
- OpenAPI contract extraction
- Enhanced TypeScript syntax support (utility types, conditional types)
- SARIF profile for enterprise CI
- Incremental graph mode for large codebases

## Near-Term

- Extend parser coverage for richer TypeScript declarations.
- Add OpenAPI-aware contract correlation.
- Improve false-positive controls with explicit mapping policies.
- Expand fixture suite for edge-case syntax and large projects.

## Mid-Term

- Add discoverers for route activation and config usage drift.
- Introduce stable SARIF output profile for enterprise CI systems.
- Add benchmark harness for parser latency and graph traversal cost.

## drift Integration

- Finalize stable output schema compatibility for downstream drift ingestion.
- Provide a reference CI example that chains `contract-graph` and drift.
- Add cross-tool documentation for interpretation of shared finding semantics.

## Long-Term

- Incremental graph build mode for very large monorepos.
- Optional language plugins beyond Python/TypeScript.
- Multi-repo baseline comparison and trend reporting.

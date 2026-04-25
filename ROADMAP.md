# Roadmap

## Implementation Status (Phase 1 Audit)

As of 25 April 2026, the following modules have been audited for v1 readiness:

| Module | Status | Evidence |
|--------|--------|----------|
| `parsing/` | ✅ Functional | `python_parser.py`, `typescript_parser.py`, `yaml_parser.py` fully implemented with AST traversal and field extraction. Phase 2: TypeScript parser extended for utility types, conditional types, mapped types. |
| `discovery/` | ⚠️ Stub→Partial | Phase 1: Only `api_type_sync` implemented. Phase 2: `config_usage` and `route_activation` discoverers implemented (disabled by default). |
| `graph/` | ✅ Functional | `model.py`, `builder.py`, `impact.py` fully implemented with networkx-backed graph and traversal. |
| `policy/` | ✅ Functional | `engine.py` and `rules.py` with rule registry and 5 built-in policy rules. |
| `reporting/` | ✅ Functional | Phase 1: JSON output refactored to schema-conformance. Phase 2: No changes. |
| `scoring/` | ✅ Functional | Severity-weighted scorer fully implemented in `scorer.py`. Phase 2: Weights include new discoverers (config_usage, route_activation). |
| `cli.py` | ✅ Functional | Phase 1: Full pipeline with `analyze`/`check`/`impact`/`init` commands. Phase 2: Added `--enable-discoverers` flag for CLI-driven activation. |
| `config.py` | ✅ Functional | Pydantic v2 config models, loading, and presets. Phase 2: Added ConfigUsageConfig and RouteActivationConfig models. |

## v1 Scope (Locked — Phase 1)

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
- Additional discoverers enabled by default: `config_usage`, `route_activation` (Phase 2 proof-of-concept, disabled by default)
- OpenAPI-aware correlation
- SARIF output format
- Performance optimization / incremental builds
- Multi-repo workflows
- Language plugins beyond Python/TypeScript

## v2 Target (Phase 2 & Beyond)

**Completed (Phase 2):**
- ✅ Route activation discoverer (proof-of-concept, disabled by default)
- ✅ Config usage discoverer (proof-of-concept, disabled by default)
- ✅ Enhanced TypeScript syntax support (utility types, conditional types, mapped types)
- ✅ CLI flag `--enable-discoverers` for dynamic activation

**Remaining:**
- OpenAPI contract extraction
- SARIF profile for enterprise CI
- Incremental graph mode for large codebases
- Performance benchmarking harness

## Near-Term

- Extend parser coverage for richer TypeScript declarations (Phase 2: ✅ completed)
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

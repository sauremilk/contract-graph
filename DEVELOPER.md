# Developer Guide

## Architecture Overview

The project follows a modular static-analysis pipeline:

- `src/contract_graph/parsing`: AST and syntax-level extraction.
- `src/contract_graph/discovery`: Provider-consumer matching logic.
- `src/contract_graph/graph`: Graph data model, build orchestration, impact analysis.
- `src/contract_graph/policy`: Rule evaluation over discovered mismatches.
- `src/contract_graph/scoring`: Health scoring and severity aggregation.
- `src/contract_graph/reporting`: Terminal, JSON, and Markdown output.
- `src/contract_graph/cache`: File hash and cache helpers.
- `src/contract_graph/cli.py`: CLI entry points and command orchestration.

## Data Flow

1. CLI loads config and resolves root paths.
2. Discoverers parse source files and produce nodes/edges.
3. Graph builder merges contributions into a contract graph.
4. Policy engine evaluates graph mismatches into findings.
5. Scoring computes health indicators.
6. Reporters render output for local or CI usage.

## Design Decisions Log

- `src/` layout for packaging stability and cleaner import boundaries.
- `uv` as the single package manager for local and CI workflows.
- `mypy` as primary type checker for predictable CI/runtime parity.
- `python-semantic-release` for automated version/changelog lifecycle.
- Coverage baseline starts at 60% and is expected to increase incrementally.

## Compatibility Notes

- Keep `contract_graph/output_schema.json` backward compatible for downstream tooling.
- Additive schema changes are preferred over renames/removals.
- CLI exit codes are public API and must remain stable.

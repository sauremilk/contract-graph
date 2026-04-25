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

## Test Strategy

The test suite follows a layered approach:

| Layer | Location | Coverage target | Scope |
|-------|----------|-----------------|-------|
| Unit | `tests/test_parsers.py`, `test_graph_model.py`, `test_policy_engine.py`, etc. | ≥ 70 % of lines | Individual parser functions, graph algorithms, policy rules |
| Integration | `tests/test_api_type_sync.py`, `test_config_usage.py`, `test_route_activation.py` | ≥ 20 % of lines | Full discovery pipeline on fixture files |
| Regression | `tests/test_regression_demo.py` | baseline lock | Known-good scenarios that must never regress |
| Schema | `tests/test_schema_validation.py` | explicit cases | JSON output schema contract stability |

**Golden fixture rule**: files under `tests/fixtures/` are immutable references — do not modify them to fix a test; fix the parser instead.

**Hermetic only**: tests must not access the network or write outside `tmp_path`.

## `make` Targets Reference

| Target | Command | Purpose |
|--------|---------|---------|
| `install` | `uv sync --extra dev` | Set up development environment |
| `lint` | `ruff check src tests` | Lint with Ruff |
| `type-check` | `mypy src/contract_graph` | Static type checking |
| `test` | `pytest tests -q` | Fast test run |
| `test-cov` | `pytest tests --cov=...` | Tests with coverage report (XML + terminal) |
| `build` | `uv build` | Build wheel and sdist |
| `clean` | removes caches/dist | Clean build artifacts |
| `pre-commit-install` | installs hooks | Install pre-commit and pre-push hooks |
| `pre-commit-run` | runs all hooks | Run all pre-commit checks across all files |

## Common Issues

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `mypy` reports missing stubs | Missing dev extras | `uv sync --extra dev` |
| Coverage drops below 60 % | New code without tests | Add unit tests before opening PR |
| `ruff` fails on new file | Import or style issue | `uv run ruff check --fix src tests` |
| CLI returns exit code 2 | Config parse error | Check YAML schema; see `contract-graph.example.yaml` |
| `detect-secrets` baseline mismatch | New fixture with secret-like string | `uv tool run detect-secrets scan --baseline .secrets.baseline` |

## Release Checklist

> Releases are automated by `python-semantic-release`. This checklist is for the manual review before a major version bump.

1. Verify `CHANGELOG.md` top section is accurate and complete.
2. Confirm `output_schema.json` schema version is backward-compatible (additive only).
3. Confirm CLI exit code semantics are unchanged (`0` / `1` / `2`).
4. Run `make test-cov` and confirm coverage is above threshold.
5. Check that `pyproject.toml` classifiers and `requires-python` still reflect the supported range.
6. Tag is applied by CI automatically on merge to `master` if commit messages follow Conventional Commits.

## Maintainer Operations

Repository operations are documented separately so contributor-facing docs stay focused:

- `docs/MAINTAINER_RUNBOOK.md`: release, CI, review, and incident handling.
- `docs/REPOSITORY_GOVERNANCE.md`: repository policy, public contracts, and hygiene rules.
- `.github/workflows/README.md`: current workflow matrix and workflow-change checklist.

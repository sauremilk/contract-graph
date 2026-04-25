# Changelog

All notable changes to this project are documented in this file.

## Unreleased

Short version: drift integration adapter (`drift-contract-graph`) with deterministic finding fingerprints and versioned JSON schema.

### Added

- `schema_version` field in JSON report output (`SCHEMA_VERSION = "1.1"`), now required by `output_schema.json`. Enables downstream consumers to detect schema evolution without parsing tool version strings.
- Deterministic `finding_id` fingerprint (`CG-<sha256[:12]>`) on every `Finding`. Fingerprint is computed from `discoverer + provider_file + consumer_file + field_name + mismatch_kind`, stable across re-runs on unchanged code.
- `drift-contract-graph/` sub-package: a native drift `IntegrationAdapter` that invokes `contract-graph analyze --format json` as a subprocess, maps findings to `drift.models.Finding`, and registers the `drift contracts` CLI subcommand — all via Python entry-points with zero modification to drift's codebase.
- `drift contracts analyze / check / show-mapping` CLI commands registered via `drift.commands` entry-point.
- Precision/Recall eval suite at `drift-contract-graph/tests/evals/` with initial baseline: Precision 100%, Recall 100% on 8 labelled cases.

### Changed

- `Finding.to_dict()` now includes `finding_id` in its output dict.
- `output_schema.json` `required` array extended with `schema_version`; finding `properties` extended with `finding_id` definition.

## 0.1.0 - 2026-04-25

Short version: Initial public baseline with modernized build, quality tooling, and CI/CD foundations.

### Added

- `src/` package layout for `contract_graph`.
- Quality tooling with Ruff, mypy, pre-commit hooks, and secrets scanning baseline.
- CI workflow with lint, type-check, test, and coverage reporting.
- Release workflow based on `python-semantic-release`.
- Community documentation set (`CONTRIBUTING`, `DEVELOPER`, `ROADMAP`, `SECURITY`, `SUPPORT`).
- Initial compatibility scaffolding for drift integration.

### Changed

- Development flow standardized on `uv` and Makefile targets.

### Fixed

- Minor lint and typing inconsistencies in reporting and parser helpers.

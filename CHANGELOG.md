# Changelog

All notable changes to this project are documented in this file.

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

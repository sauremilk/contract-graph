# Repository Governance

This document defines the repository-level quality bar for contract-graph.

## Goals

The repository should be easy to contribute to, predictable to release, and safe to depend on as a CLI and JSON-producing analysis tool.

## Public contracts

The following surfaces are treated as stable contracts:

- CLI exit codes
- CLI flag names and semantics
- YAML configuration keys
- JSON report schema in `src/contract_graph/output_schema.json`
- Public package versioning in `pyproject.toml` and `src/contract_graph/__init__.py`

Changes to these surfaces should be additive whenever possible. Renames and removals must be called out explicitly in `CHANGELOG.md`.

## Required quality gates

Every pull request should preserve these minimum gates:

- Ruff passes
- Mypy passes
- Pytest passes
- CI stays green on supported Python versions
- Secret scanning remains clean or intentionally baselined

Behavioral changes to parsing, discovery, policy, or reporting should include tests. User-visible changes should update docs and changelog entries.

## Documentation policy

The repository keeps a small but explicit docs set:

- `README.md` for user-facing onboarding and workflow
- `CONTRIBUTING.md` for contribution rules
- `DEVELOPER.md` for architecture and local development
- `docs/MAINTAINER_RUNBOOK.md` for repository operations
- `docs/REPOSITORY_GOVERNANCE.md` for repository policy

If a change affects onboarding, maintenance, or release behavior, update the corresponding document in the same PR.

## Review policy

Reviewers should optimize for:

- Correctness over novelty
- Minimal blast radius
- Deterministic behavior
- Backward compatibility for public contracts
- Clear rollback path for CI, release, or packaging changes

## Release discipline

Version metadata must stay aligned across release-facing files. Before a release is considered complete, verify:

- `pyproject.toml` version is correct
- `src/contract_graph/__init__.py` version is correct
- `CHANGELOG.md` top entry matches the release
- GitHub release notes reflect the merged user-visible changes

## Repository hygiene

- Keep top-level files intentional and documented.
- Prefer focused workflows over ad-hoc scripts for recurring repository operations.
- Avoid adding new root files when an existing docs or scripts location is a better fit.
- Keep automation readable enough that a new maintainer can recover it without private context.

# Contributing to contract-graph

Thanks for contributing.

## Development Setup

```bash
uv sync --extra dev
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

Run the local quality gates before opening a PR:

```bash
make lint
make type-check
make test
```

## Commit Convention

This repository uses Conventional Commits.

Allowed prefixes:

- `feat:`
- `fix:`
- `docs:`
- `chore:`
- `ci:`

Examples:

- `feat: add api type sync matcher for alias fields`
- `fix: prevent false optionality mismatch on union types`
- `docs: clarify output schema compatibility guarantees`

## Pull Request Process

1. Create a focused branch with one concern per PR.
2. Keep changes minimal and include tests for behavior changes.
3. Ensure CI is green on Python 3.11 and 3.12.
4. Describe user impact in the PR body.
5. Link related issue(s) and include migration notes if needed.

## Review Expectations

- Prefer small, reviewable PRs.
- Preserve backward compatibility for CLI flags and config keys.
- Avoid changing parser semantics without fixture-based tests.

## Reporting Bugs

Open an issue with:

- Reproduction steps.
- Expected vs actual behavior.
- Sample files or reduced fixture if possible.
- Environment details (OS, Python version, command used).

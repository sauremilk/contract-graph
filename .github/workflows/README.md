# Workflow Matrix

This directory contains the repository automation entry points.

## Active workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | Push and pull request to `master` | Lint, type-check, test, coverage upload, and secret scanning |
| `release.yml` | Successful completion of `CI` on `master` | Run semantic-release and publish release metadata |
| `dependency-review.yml` | Pull request to `master` | Review dependency changes for high-severity advisories |
| `install-smoke.yml` | Weekly schedule (Mon 06:00 UTC) + manual | Build wheel and verify CLI installability on Python 3.11–3.13 |

## Operating rules

- Keep workflows focused and easy to reason about.
- Prefer reusable Makefile targets or repository scripts over large inline shell blocks when logic grows.
- Pin third-party GitHub Actions by major version at minimum; pin by commit hash when workflow criticality increases.
- When changing release behavior, update this file and the maintainer docs in the same PR.

## Change checklist

Before merging workflow changes:

1. Validate the YAML locally if practical.
2. Confirm that the workflow name referenced by dependent workflows still matches exactly.
3. Check permissions for least privilege.
4. Check whether docs or branch-protection expectations need updates.

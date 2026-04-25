# Maintainer Runbook

This runbook documents the normal operating path for maintaining contract-graph as a small but production-grade open-source analysis tool.

## Release path

Normal path:

1. Merge a focused pull request to `master` with a conventional-commit title.
2. Verify that the `CI` workflow completed successfully on the merge commit.
3. Verify that the `Release` workflow completed successfully and created the expected version bump.
4. Confirm that `CHANGELOG.md`, `pyproject.toml`, and `src/contract_graph/__init__.py` agree on the released version.
5. Sanity-check the GitHub release notes before announcing the release.

If release automation fails:

1. Inspect the failed workflow logs first.
2. Fix the underlying issue in a follow-up PR when possible instead of patching tags manually.
3. Use a local `uv run semantic-release version` fallback only after understanding why CI failed.
4. Never force-push release metadata without documenting the reason in the follow-up PR.

## CI triage

When CI fails, prefer the narrowest reproducer:

1. Lint failures: run `make lint`.
2. Type-check failures: run `make type-check`.
3. Test failures: run `make test`.
4. Coverage upload issues: verify that `coverage.xml` is produced by `make test-cov`.
5. Secret-scan failures: rotate or remove the finding, then update `.secrets.baseline` only for intentional false positives.

Escalation rule:

- Fix repository-state problems before merging feature work.
- Avoid merging around broken release or CI infrastructure unless the follow-up owner and recovery plan are explicit.

## Contribution intake

For incoming pull requests:

1. Check that the PR is focused on one concern.
2. Check that validation steps are described and match the actual change.
3. Check that parser or discoverer changes include tests, preferably fixture-based tests.
4. Check that user-visible behavior changes update `README.md`, `CHANGELOG.md`, or both.
5. Ask for smaller follow-up PRs when scope mixes product logic and repo-maintenance work.

## Branch and merge policy

- `master` is the integration branch.
- Keep history reviewable with small PRs and conventional commits.
- Prefer squash merges for noisy branches when commit history does not add review value.
- Do not merge if required checks are red unless the branch is being used only for emergency recovery and the exception is documented.

## Incident log expectations

Document notable repository incidents in the PR or issue that fixed them:

- Broken release automation
- Incorrect version or changelog state
- CI regressions affecting contributors
- Secret scanning false positives that required baseline changes
- Output-schema compatibility regressions

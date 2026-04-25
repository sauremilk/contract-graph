## Context Map

### Files to Modify
| File | Purpose | Changes Needed |
|------|---------|----------------|
| .github/PULL_REQUEST_TEMPLATE.md | Standardize PR quality expectations | Add a review-ready PR template |
| DEVELOPER.md | Developer entry point | Link to maintainer and governance docs |
| docs/MAINTAINER_RUNBOOK.md | Maintainer operations | Document release, CI, and review workflow |
| docs/REPOSITORY_GOVERNANCE.md | Repository policy | Define public contracts and repo hygiene rules |
| .github/workflows/README.md | Automation discoverability | Document current workflow matrix and workflow change rules |

### Dependencies (may need updates)
| File | Relationship |
|------|--------------|
| .github/workflows/release.yml | Referenced by workflow documentation |
| .github/workflows/ci.yml | Referenced by workflow documentation |
| CHANGELOG.md | Mentioned by release and governance policy |
| pyproject.toml | Mentioned by release and governance policy |

### Test Files
| Test | Coverage |
|------|----------|
| tests/test_cli.py | Closest behavioral safety net for CLI/public contract expectations |

### Reference Patterns
| File | Pattern |
|------|---------|
| drift/.github/PULL_REQUEST_TEMPLATE.md | PR quality checklist |
| drift/DEVELOPER.md | Maintainer-doc entry points and workflow matrix |
| drift/.github/workflows/README.md | Workflow inventory and operational notes |

### Risk Assessment
- [ ] Breaking changes to public API
- [ ] Database migrations needed
- [x] Configuration changes required

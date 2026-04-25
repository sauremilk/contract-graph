# contract-graph

[![CI](https://github.com/mick-gsk/contract-graph/actions/workflows/ci.yml/badge.svg)](https://github.com/mick-gsk/contract-graph/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/mick-gsk/contract-graph/branch/master/graph/badge.svg)](https://codecov.io/gh/mick-gsk/contract-graph)
![PyPI Ready](https://img.shields.io/badge/pypi-ready-blue)

Cross-boundary contract intelligence for fullstack codebases.

`contract-graph` statically analyzes your repository to detect drift between backend contracts
(Pydantic/FastAPI) and frontend contracts (TypeScript interfaces/types) before runtime incidents happen.

## Quickstart

```bash
uv sync --extra dev
uv run contract-graph init --preset fullstack
uv run contract-graph analyze
uv run contract-graph check --fail-on high
```

Expected behavior:

- Exit code `0`: no findings above threshold.
- Exit code `1`: findings matched the configured fail threshold.
- Exit code `2`: configuration or runtime input error.

## Core Concept

`contract-graph` builds a directed graph from cross-boundary artifacts.

1. Parse: discover models, routes, interfaces, and config readers.
2. Discover: match provider contracts to consumer contracts.
3. Compare: detect field/type/optionality mismatches.
4. Policy: convert mismatches into CI-relevant findings.
5. Report: output terminal, JSON, or Markdown reports.

Detected mismatch families:

- Missing field in consumer.
- Missing field in provider.
- Type incompatibility.
- Optionality mismatch.
- Phantom type.

## Integration with drift

`contract-graph` and `drift` are complementary:

- `contract-graph` focuses on static cross-boundary contract drift (v1: Pydantic ↔ TypeScript).
- `drift` can consume structured findings for broader reliability workflows.

**CLI Integration:**

```bash
contract-graph analyze --format json | drift ingest
```

For complete integration guide, see [docs/drift-integration.md](docs/drift-integration.md).

**Stable Output Contract:**
All JSON output conforms to [`src/contract_graph/output_schema.json`](src/contract_graph/output_schema.json), ensuring reliable downstream tooling integration.

## Development

```bash
make install
make lint
make type-check
make test
make test-cov
```

Additional docs:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [DEVELOPER.md](DEVELOPER.md)
- [docs/MAINTAINER_RUNBOOK.md](docs/MAINTAINER_RUNBOOK.md)
- [docs/REPOSITORY_GOVERNANCE.md](docs/REPOSITORY_GOVERNANCE.md)
- [ROADMAP.md](ROADMAP.md)
- [SECURITY.md](SECURITY.md)

## License

MIT

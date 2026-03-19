# contract-graph

> Cross-boundary contract intelligence for fullstack projects.

**contract-graph** statically analyzes your codebase to detect drift between backend models (Pydantic/FastAPI) and frontend types (TypeScript interfaces). It builds a dependency graph of all cross-boundary contracts and surfaces mismatches *before* they hit production.

## Problem

In fullstack projects, backend schemas (Pydantic models, API routes) and frontend types (TypeScript interfaces, API calls) are defined independently. They drift apart silently:

- A field is added to the backend response but never consumed in the frontend
- A type changes from `int` to `string` but the TypeScript interface still says `number`
- A new frontend type has no matching backend model (phantom type)

These bugs pass CI, pass type-checkers, and only surface at runtime — usually in production.

## Solution

```bash
pip install contract-graph

# Initialize config
contract-graph init --preset fullstack

# Run analysis
contract-graph analyze

# CI gate (exits 1 on high+ severity findings)
contract-graph check --fail-on high
```

## Quick Start

### 1. Install

```bash
pip install contract-graph
```

### 2. Generate config

```bash
contract-graph init --preset fullstack
```

This creates `contract-graph.yaml`:

```yaml
discovery:
  api_type_sync:
    enabled: true
    provider_paths: [backend/, src/]
    consumer_paths: [frontend/src/, dashboard/src/]
    naming_convention: auto
policy:
  fail_on: high
scoring:
  weights:
    api_type_sync: 1.0
```

### 3. Analyze

```bash
contract-graph analyze
```

Output:
```
╭─ Contract Graph Report ─────────────────────────────────╮
│ Health Score: 72/100 (C)  │  Nodes: 14  │  Edges: 8     │
╰──────────────────────────────────────────────────────────╯

🟠 HIGH  Missing field in consumer: MatchResponse.match_mode
         Provider: backend/models.py → Consumer: frontend/types.ts
🟡 MEDIUM  Phantom type: TournamentBracket has no backend model
🔵 LOW  Extra field in consumer: PlayerStats.favoriteWeapon
```

### 4. CI Gate

```bash
contract-graph check --fail-on high
# Exit code 1 if any HIGH+ findings exist
```

### 5. Impact Analysis

```bash
contract-graph impact backend/models.py
# Shows what frontend types are affected by changes to this file
```

## Commands

| Command | Purpose |
|---------|---------|
| `analyze` | Full contract analysis with terminal/JSON output |
| `check` | CI gate — exit 1 if findings exceed severity threshold |
| `impact <file>` | Show change impact for a specific file |
| `init` | Generate `contract-graph.yaml` config template |

## How It Works

1. **Parse** — AST-based extraction of Pydantic models, FastAPI routes, TypeScript interfaces, YAML configs
2. **Discover** — Pluggable discoverers match providers (backend) to consumers (frontend) by name + fields
3. **Compare** — Field-by-field comparison detects missing fields, type mismatches, optionality drift
4. **Score** — Weighted scoring produces a 0-100 health score
5. **Report** — Terminal (Rich), JSON, or Markdown output

## Discoverers

| Discoverer | What it detects |
|------------|----------------|
| `api_type_sync` | Drift between Pydantic models and TypeScript interfaces |

More discoverers (config_usage, route_activation, schema_evolution) planned.

## Configuration

See `contract-graph init --preset fullstack` for a full example. Key options:

```yaml
discovery:
  api_type_sync:
    enabled: true
    provider_paths: [backend/]        # Where Pydantic models live
    consumer_paths: [frontend/src/]   # Where TypeScript types live
    naming_convention: auto           # auto | snake_to_camel | camel_to_snake
    custom_model_mapping:             # Manual overrides
      BackendName: FrontendName
    custom_type_mapping:
      datetime: string                # Custom type equivalences

policy:
  fail_on: high                       # CI gate threshold

scoring:
  weights:
    api_type_sync: 1.0
```

## License

MIT

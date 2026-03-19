# contract-graph

> Cross-boundary contract intelligence for fullstack projects.

**contract-graph** statically analyzes your codebase to detect drift between backend models (Pydantic/FastAPI) and frontend types (TypeScript interfaces). It builds a dependency graph of all cross-boundary contracts and surfaces mismatches _before_ they hit production.

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

| Command         | Purpose                                                |
| --------------- | ------------------------------------------------------ |
| `analyze`       | Full contract analysis with terminal/JSON output       |
| `check`         | CI gate — exit 1 if findings exceed severity threshold |
| `impact <file>` | Show change impact for a specific file                 |
| `init`          | Generate `contract-graph.yaml` config template         |

## How It Works

1. **Parse** — AST-based extraction of Pydantic models, FastAPI routes, TypeScript interfaces, YAML configs
2. **Discover** — Pluggable discoverers match providers (backend) to consumers (frontend) by name + fields
3. **Compare** — Field-by-field comparison detects missing fields, type mismatches, optionality drift
4. **Score** — Weighted scoring produces a 0-100 health score
5. **Report** — Terminal (Rich), JSON, or Markdown output

## Discoverers

| Discoverer      | What it detects                                         |
| --------------- | ------------------------------------------------------- |
| `api_type_sync` | Drift between Pydantic models and TypeScript interfaces |

More discoverers (config_usage, route_activation, schema_evolution) planned.

## Configuration

See `contract-graph init --preset fullstack` for a full example. Key options:

```yaml
discovery:
  api_type_sync:
    enabled: true
    provider_paths: [backend/] # Where Pydantic models live
    consumer_paths: [frontend/src/] # Where TypeScript types live
    naming_convention: auto # auto | snake_to_camel | camel_to_snake
    custom_model_mapping: # Manual overrides
      BackendName: FrontendName
    custom_type_mapping:
      datetime: string # Custom type equivalences

policy:
  fail_on: high # CI gate threshold

scoring:
  weights:
    api_type_sync: 1.0
```

## What contract-graph catches that nothing else does

`mypy`, `tsc`, and `eslint` each check one side of the stack in isolation. None of them can detect drift _between_ backend and frontend. Here's a concrete example:

```python
# backend/models.py
class UserProfile(BaseModel):
    user_id: UUID
    email: str
    premium_tier: bool        # ← changed from str to bool last sprint
    bio: Optional[str]        # ← nullable
    discount_code: str        # ← new field
```

```typescript
// frontend/types.ts — stale, nobody updated it
interface UserProfile {
  userId: string;
  email: string;
  premiumTier: string; // ← BUG: still string, backend is bool
  bio: string; // ← BUG: required, backend is Optional
  // discountCode missing  // ← BUG: field doesn't exist here
}
```

Now run the tools:

```bash
mypy backend/           # ✅ all good
tsc --noEmit            # ✅ all good
contract-graph check    # ❌ EXIT 1 — 3 findings
```

| Bug type                                  | `mypy`  | `tsc`   | `contract-graph` |
| ----------------------------------------- | ------- | ------- | ---------------- |
| Type mismatch (`bool` → `string`)         | ✅ pass | ✅ pass | ❌ **caught**    |
| Missing field (`discount_code`)           | ✅ pass | ✅ pass | ❌ **caught**    |
| Optionality drift (`Optional` → required) | ✅ pass | ✅ pass | ❌ **caught**    |
| Phantom type (no backend model)           | ✅ pass | ✅ pass | ❌ **caught**    |

All four drift categories are covered by the test suite in `tests/test_regression_demo.py` with a controlled fixture (`tests/fixtures/regression_demo/`). The same fixture includes `NotificationSettings` — a perfectly synced model — to prove zero false positives on clean contracts.

### Detected drift types

| Drift type                | Severity | Example                                                       |
| ------------------------- | -------- | ------------------------------------------------------------- |
| Missing field in consumer | MEDIUM   | Backend adds `discount_code`, frontend never updated          |
| Type incompatibility      | HIGH     | Backend changes `str` → `bool`, frontend still says `string`  |
| Phantom type              | MEDIUM   | Frontend has `PaymentMethod`, no backend model exists         |
| Optionality mismatch      | MEDIUM   | Backend says `Optional[str]`, frontend says required `string` |
| Extra field in consumer   | LOW      | Frontend has `favoriteWeapon`, backend doesn't know about it  |

### Scope & limitations

- **Currently detects:** Pydantic model ↔ TypeScript interface drift (field presence, type compatibility, optionality)
- **Not yet detected:** OpenAPI spec drift, enum value drift, nested object depth differences
- **Naming:** `auto` mode handles `snake_case` ↔ `camelCase` conversion; unconventional names need `custom_model_mapping`
- **False positives:** The control test (`NotificationSettings`) confirms zero false positives on synced models. Use `custom_type_mapping` for project-specific type equivalences.

## License

MIT

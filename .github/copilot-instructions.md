# GitHub Copilot – Workspace-Instruktionen: contract-graph

> **Modell:** Claude Sonnet 4.6
> **Portfolio-Ziel:** Jede Änderung an diesem Repo demonstriert Big-Tech-Engineering-Qualität für Staff-Engineer-Interviews bei Google, Apple und OpenAI.

---

## Projektkontext

**contract-graph** ist ein statisches Analyse-Tool, das Contract-Drift zwischen Backend-Schemas (Pydantic/FastAPI) und Frontend-Types (TypeScript-Interfaces) erkennt. Es baut einen Abhängigkeitsgraphen aller Cross-Boundary-Contracts und macht Mismatches sichtbar, bevor sie in Produktion gelangen.

**Domain:** Static Analysis · Graph Algorithms · AST Parsing · Developer Tooling · CLI
**Stack:** Python 3.11+, Pydantic v2, Click, NetworkX, Rich, tree-sitter (optional), Ruff, Pyright

---

## I. Design Before Code (Google Design Doc / Apple API Review)

**Pflicht vor jeder nicht-trivialen Änderung (> 50 LOC oder neue Abstraktion):**

### Design-Checkliste für static-analysis-Domain

1. **Problem Statement** – Welches konkrete Drift-Pattern erkennt das Feature? Beispiel mit Code.
2. **Non-Goals** – Was soll der Parser/Discoverer explizit NICHT erkennen?
3. **False Positive Budget** – Welche False-Positive-Rate ist akzeptabel? (Ziel: < 5% auf Benchmark-Corpus)
4. **AST Contract** – Welche Knoten im AST werden traversiert? Syntax-Tree-Diagram wenn möglich.
5. **Graph Schema Impact** – Werden neue `NodeType` oder `EdgeType` ergänzt? Backward-kompatibel?
6. **Complexity Analysis** – Was ist die Zeitkomplexität? `O(n)` Parser? `O(V+E)` Graph-Traversal?
7. **Failure Modes** – Was passiert bei ungültigem Python/TypeScript? Partial parse vs. hard fail?
8. **CLI Surface Impact** – Bricht die Änderung bestehende Flags oder YAML-Konfiguration?
9. **Rollout** – Neue Discoverer hinter `enabled: false` defaulten bis Eval-Scores bekannt sind.

> **Google-Regel**: Wenn ein Parser neue Syntax erkennt, muss ein Gegenbeispiel existieren, das ihn NICHT triggert.

---

## II. Testing Pyramid & Eval-First (Google + OpenAI Philosophy)

```
         /\
        /E2E\          ← contract-graph analyze auf echten OSS-Projekten
       /------\
      /Integrat\       ← Pipeline: parse → discover → graph → report
     /----------\
    / Unit Tests  \    ← Parser-Korrektheit, Graph-Algorithmen, Policy-Engine
   /--------------\
```

### Pflichtregeln

- **70/20/10-Ratio** – 70% Unit (Parser/Graph/Policy), 20% Integration (CLI-Pipeline), 10% E2E (reale Codebases)
- **Parser-Tests haben goldene Fixtures** – Jeder Parser-Test hat ein `fixtures/`-File das nicht verändert wird.
  ```python
  # Korrekt: Fixture-basierter Parser-Test
  def test_pydantic_parser_extracts_nested_models(fixtures_dir: Path):
      code = (fixtures_dir / "nested_model.py").read_text()
      result = PythonParser().parse(code)
      assert result.nodes == [NodeType.PYDANTIC_MODEL, ...]
  ```
- **Hermetic Tests only** – Kein Filesystem außer `tmp_path`. Kein Netzwerk.
- **Property-Tests für Parser** – Neben Happy-Path: leere Dateien, Syntax-Fehler, Unicode, 10k-LOC-Dateien
- **Test-Names als Spezifikation**:
  - ✅ `test_typescript_parser_ignores_type_alias_unions_without_api_annotation`
  - ❌ `test_parser()`

### OpenAI Eval-Mindset: Precision & Recall als First-Class Metrics

Jeder neue Discoverer **muss** eine Eval-Suite haben bevor er stabiled (`enabled: true`) wird:

```
tests/evals/<discoverer_name>/
  cases.jsonl         # {input: ..., expected_findings: [...]}
  eval_runner.py      # Automatisches Scoring
  results/
    baseline.json     # Versioniertes Ergebnis (Git-getrackt)
```

**Quantitative Gates:**
| Metrik | Minimum | Ziel |
|---------------------|----------|---------|
| Precision | 90% | 95% |
| Recall | 80% | 90% |
| False Positive Rate | < 10% | < 5% |
| P99 Parse Latency | < 500ms | < 200ms |

> **"No vibes-based ship"** (OpenAI-Prinzip): Kein Discoverer geht auf `enabled: true` ohne Eval-Ergebnisse.

### Performance-Benchmarks als Bürger erster Klasse

```python
# Jeder neue Parser bekommt einen Benchmark
@pytest.mark.benchmark
def test_python_parser_10k_loc_p99(benchmark, large_fixture_path):
    code = large_fixture_path.read_text()
    result = benchmark(PythonParser().parse, code)
    assert benchmark.stats["mean"] < 0.200  # 200ms Ziel für 10k LOC
```

Regressionen > 20% gegenüber Baseline blockieren Merges.

---

## III. API Contract-First Design (Apple API Minimalism + Google API Design Guide)

### Prinzipien für static-analysis-Tools

1. **CLI ist das primäre Interface** – Jeder Befehl folgt dem Prinzip: sane defaults, null Konfiguration für den einfachsten Fall.
   ```bash
   contract-graph analyze   # Soll ohne jede config funktionieren
   ```
2. **Konfiguration ist progressiv** – Einfachstes Use-Case: kein YAML. Fortgeschritten: volle Konfiguration.
3. **Kein Breaking Change in Minor versions** – YAML-Config-Keys und CLI-Flags folgen Semantic Versioning.
4. **Exit Codes sind API** – `0` = success/no findings above threshold, `1` = findings found, `2` = config error. Nie mischen.
5. **Output Formats sind verträge** – JSON-Report-Schema ist versioniert. SARIF-Output muss valides Schema sein.
6. **Fehler sind lesbar für Entwickler**:

   ```
   # Anti-Pattern:
   Error: NoneType has no attribute 'nodes'

   # Big-Tech Pattern:
   contract-graph: could not parse 'backend/models.py'
   Cause: Pydantic v1 syntax detected (use_enum_values=True on field).
   Fix: Upgrade to Pydantic v2 or set parser.pydantic_version: 1 in config.
   ```

### Graph Schema Stabilität (Google API Stability Rules)

`NodeType`, `EdgeType` und `FindingSeverity` sind öffentliche Contracts:

- **Additive changes**: immer erlaubt (`NodeType.PYDANTIC_MODEL_V2` ergänzen)
- **Renames**: niemals ohne Deprecation-Zyklus (min. 1 Minor Version)
- **Removals**: erst in Major Version, mit explizitem CHANGELOG-Eintrag

---

## IV. Code-Qualität (Google Readability Standards)

### Complexity-Budget für static-analysis-Code

```python
# Cyclomatic Complexity: max. 10 pro Funktion
# Function length: max. 50 LOC
# Nesting depth: max. 3 (dann Early Return oder Extraktion)

# Anti-Pattern (depth 4, spaghetti):
def parse_field(node):
    if node:
        if node.type == "field":
            if node.children:
                for child in node.children:
                    if child.type == "annotation":
                        return child.text

# Big-Tech Pattern (flat, early return):
def parse_field(node: ASTNode) -> str | None:
    if not node or node.type != "field":
        return None
    annotations = [c for c in node.children if c.type == "annotation"]
    return annotations[0].text if annotations else None
```

### Skalierbarkeits-Kommentare (Google Staff Engineer Signal)

```python
# O(V+E) für Graph-Traversal – bei >100k Nodes auf inkrementellen Cache umstellen (TASK-XX)
def find_affected_nodes(graph: ContractGraph, changed: str) -> set[str]:
    ...

# O(n*k) für Cross-Product-Matching – bei >500 Contracts auf Trie-Index migrieren
def match_providers_to_consumers(...) -> list[ContractEdge]:
    ...
```

### Defensive Coding an Systemgrenzen

- **Filesystem-Inputs**: Immer mit `encoding="utf-8", errors="replace"` lesen – kein Crash bei exotischen Dateien.
- **AST-Parsing**: Jede `tree-sitter`-Query muss `try/except` wrappen (malformed Syntax darf Tool nicht crashen).
- **Config-Validierung**: Pydantic v2 `model_validator` at boundary, nicht tief im Code.
- **Optional Dependencies**: `tree-sitter` ist optional – alle Parser-Pfade müssen mit `ImportError` umgehen können.

---

## V. Observability (Google SRE / Three Pillars)

```python
# Jedes analyze-Kommando loggt strukturiert:
# {
#   "event": "analysis.complete",
#   "duration_ms": 145,
#   "nodes_discovered": 34,
#   "edges_discovered": 21,
#   "findings": {"high": 2, "medium": 5, "low": 1},
#   "parsers_used": ["python", "typescript"],
#   "cache_hit_rate": 0.72
# }
```

**Pflicht für jede neue Analyse-Komponente:**

- Parse-Dauer als Metrik (Histogramm, nicht nur Counter)
- Cache-Hit-Rate sichtbar machen
- Fehlerhafte Dateien zählen (nicht silently ignorieren)

---

## VI. Open-Source-Spezifika (Google Open Source / Apple Developer Experience)

### Versionierung und Backward Compatibility

- **Semantic Versioning strikt**: `0.x.y` → Breaking OK. Ab `1.0.0`: Minor-Versions dürfen nie Breaking sein.
- **CHANGELOG.md** bei jedem Release mit: `### Added`, `### Changed`, `### Fixed`, `### Breaking Changes`
- **Deprecation Warnings** über Python `warnings.warn(DeprecationWarning)` bei alten Config-Keys

### PyPI-Qualitäts-Signale (Recruiter sehen das!)

```toml
# pyproject.toml – vollständig ausgefüllt ist ein Qualitätssignal:
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Quality Assurance",
    ...
]
```

### GitHub Actions als CI-Blueprint

Jede PR muss folgende Gates passieren:

```yaml
# .github/workflows/test.yml – Pflicht-Steps:
- ruff check . # Linting (0 Warnings)
- pyright contract_graph/ # Type Checking (strict)
- pytest tests/ --cov=contract_graph # Coverage ≥ 85%
- pytest tests/ -m benchmark # Performance Regression Guard
```

---

## VII. Privacy & Security (Apple Privacy-First + Google Security)

- **Kein Netzwerk-Egress** – Das Tool analysiert lokalen Code und sendet keine Daten nach außen. Das ist ein explizites Feature, klar dokumentiert.
- **Keine Secrets extrahieren** – Parser dürfen keine String-Literale loggen (könnten API-Keys sein).
- **Pfade anonymisieren** in Reports wenn `--anonymize` Flag gesetzt.
- **SARIF-Output** ist sicheres Format für CI-Systeme (keine Code-Inhalte, nur Locations).

---

## VIII. Portfolio-Signale für Big-Tech Interviews

### Was Google Staff Engineers in diesem Repo suchen

- **Graph-Algorithmus-Verständnis**: Kommentare wie `# DFS O(V+E) – cycle detection via grey/black colouring`
- **Skalierbarkeits-Awareness**: Inkrementeller Cache für große Codebases
- **Testbarkeit als Design-Kriterium**: Alle Parser über `parse(source: str) → ParseResult` testbar ohne Filesystem
- **Abstraktion-Disziplin**: `DiscovererRegistry` ist clean, keine God-Classes

### Was Apple Engineers in diesem Repo suchen

- **Zero-Config UX**: `contract-graph analyze` ohne jede Konfiguration soll sinnvolle Ausgabe liefern
- **Fehler-Messages die erziehen**: Jede Fehlermeldung erklärt Das Problem + Die Ursache + Den Fix
- **Minimale CLI Surface**: Keine Flags die nicht 90%+ der Nutzer brauchen
- **"It just works"**: tree-sitter optional, graceful fallback auf regex-Parser

### Was OpenAI Engineers in diesem Repo suchen

- **Eval-First**: Precision/Recall-Metriken versioniert in `tests/evals/`
- **Qualitative Verbesserungen quantifiziert**: "Parser accuracy improved from 87% → 94% on TypeScript generics (evals/ts-generics/results/)"
- **Transparenz über Tool-Grenzen**: Klare LIMITATIONS.md oder Code-Kommentare über Nicht-unterstützte Patterns
- **Reproduzierbare Ergebnisse**: `--seed` für deterministische Graph-Traversal-Reihenfolge

---

## IX. Entwicklungs-Workflow

1. **Neue Discoverer**: Von `BaseDiscoverer` ableiten. `discover()` idempotent. Default `enabled: false`.
2. **Neue Parser**: Interface: `parse(source: str, path: Path) → ParseResult`. Kein Filesystem-Zugriff im Parser selbst.
3. **Neue Graph-Algorithmen**: Complexity-Kommentar Pflicht. Benchmark-Test Pflicht.
4. **Schema-Änderungen** (NodeType/EdgeType): Additive only in Minor. CHANGELOG-Eintrag.
5. **CLI-Änderungen**: Neue Flags nur wenn sie Sinn für 80% der Nutzer machen. Docs im selben PR.
6. **Eval-Ergebnisse**: Nach jeder signifikanten Änderung an Parsing-Logik Eval-Suite neu ausführen und Baseline updaten.

---

## X. Code-Review-Checkliste (Google Code Review Guide)

Vor jedem Commit / PR selbst validieren:

```
□ Parser crasht nie bei malformed Input (try/except an AST-Grenzen)?
□ Neue NodeType/EdgeType backward-kompatibel?
□ Exit-Codes korrekt (0/1/2 semantics eingehalten)?
□ Fixture-Files für neue Parser-Tests vorhanden?
□ Complexity-Kommentar bei neuen Graph-Algorithmen?
□ Optional-Dependencies mit graceful ImportError-Fallback?
□ CLI-Help-Text vollständig und verständlich?
□ Performance-Regression nicht > 20% gegenüber Baseline?
□ Keine String-Literale aus Code-Content in Logs?
□ CHANGELOG.md aktualisiert (wenn user-facing)?
```

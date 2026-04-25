"""TypeScript parser — extracts interfaces, types, and API calls via regex (tree-sitter optional)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from contract_graph.graph.model import FieldInfo

logger = logging.getLogger(__name__)

# ── Data Structures ────────────────────────────────────────────────


@dataclass
class TSInterfaceInfo:
    """Parsed TypeScript interface or type alias."""

    name: str
    file_path: Path
    fields: dict[str, FieldInfo]
    kind: str  # "interface" or "type"
    line_start: int
    line_end: int
    extends: list[str]


@dataclass
class TSApiCallInfo:
    """Parsed API call from TypeScript code."""

    url: str
    method: str  # GET, POST, etc.
    response_type: str | None
    file_path: Path
    line: int


# ── Regex Patterns ─────────────────────────────────────────────────

# Matches: export interface Foo { ... } or interface Foo<T> extends Bar { ... }
_INTERFACE_PATTERN = re.compile(
    r"(?:export\s+)?interface\s+(\w+)"  # interface name
    r"(?:\s*<[^>]*>)?"  # optional generic type params, e.g. <T, U>
    r"(?:\s+extends\s+([\w\s,<>]+?))?"
    r"\s*\{",  # opening brace
    re.MULTILINE,
)

# Matches: export type Foo = { ... } or export type Foo<T> = { ... }
_TYPE_PATTERN = re.compile(
    r"(?:export\s+)?type\s+(\w+)(?:\s*<[^>]*>)?\s*=\s*\{",
    re.MULTILINE,
)

# Matches a single field line: fieldName: Type; or fieldName?: Type;
_FIELD_PATTERN = re.compile(
    r"^\s*(?:readonly\s+)?(\w+)(\?)?:\s*(.+?);?\s*$",
    re.MULTILINE,
)

# Matches API calls: fetch("/api/..."), api.get<T>("/api/..."), axios.post("/api/...")
_API_CALL_PATTERN = re.compile(
    r"""(?:fetch|api|axios|client|http)"""  # caller
    r"""\.?(get|post|put|delete|patch)?"""  # optional method
    r"""(?:<(\w+)>)?"""  # optional generic type
    r"""\(\s*[`"']([^`"']+)[`"']""",  # URL string
    re.IGNORECASE,
)


# ── Parsing Logic ──────────────────────────────────────────────────


def _find_matching_brace(text: str, start: int) -> int:
    """Find the position of the matching closing brace."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text)


def _parse_ts_fields(body: str) -> dict[str, FieldInfo]:
    """Parse fields from an interface/type body."""
    fields: dict[str, FieldInfo] = {}
    for match in _FIELD_PATTERN.finditer(body):
        name = match.group(1)
        is_optional = match.group(2) == "?"
        type_str = match.group(3).strip().rstrip(";").strip()

        # Skip methods/functions
        if "(" in type_str and "=>" in type_str:
            continue

        fields[name] = FieldInfo(
            name=name,
            type_str=type_str,
            is_optional=is_optional,
        )
    return fields


def _count_newlines(text: str, end: int) -> int:
    """Count newlines up to position, returning 1-based line number."""
    return text[:end].count("\n") + 1


def parse_ts_interfaces(file_path: Path) -> list[TSInterfaceInfo]:
    """Parse TypeScript file for interface and type definitions."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        logger.warning("Skipping %s: %s", file_path, exc)
        return []
    results: list[TSInterfaceInfo] = []

    # Parse interfaces
    for match in _INTERFACE_PATTERN.finditer(source):
        name = match.group(1)
        extends_raw = match.group(2)
        extends = [e.strip() for e in extends_raw.split(",")] if extends_raw else []

        brace_start = match.end() - 1
        brace_end = _find_matching_brace(source, brace_start)
        body = source[brace_start + 1 : brace_end]

        line_start = _count_newlines(source, match.start())
        line_end = _count_newlines(source, brace_end)

        fields = _parse_ts_fields(body)
        results.append(
            TSInterfaceInfo(
                name=name,
                file_path=file_path,
                fields=fields,
                kind="interface",
                line_start=line_start,
                line_end=line_end,
                extends=extends,
            )
        )

    # Parse type aliases (only object types with braces)
    for match in _TYPE_PATTERN.finditer(source):
        name = match.group(1)
        brace_start = match.end() - 1
        brace_end = _find_matching_brace(source, brace_start)
        body = source[brace_start + 1 : brace_end]

        line_start = _count_newlines(source, match.start())
        line_end = _count_newlines(source, brace_end)

        fields = _parse_ts_fields(body)
        results.append(
            TSInterfaceInfo(
                name=name,
                file_path=file_path,
                fields=fields,
                kind="type",
                line_start=line_start,
                line_end=line_end,
                extends=[],
            )
        )

    return results


def parse_ts_api_calls(file_path: Path) -> list[TSApiCallInfo]:
    """Parse TypeScript file for API calls (fetch, axios, etc.)."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    results: list[TSApiCallInfo] = []

    for match in _API_CALL_PATTERN.finditer(source):
        method_str = match.group(1) or "GET"
        response_type = match.group(2)
        url = match.group(3)

        # Only include API-like URLs
        if not url.startswith(("/api", "/v1", "/v2", "http")):
            continue

        line = _count_newlines(source, match.start())
        results.append(
            TSApiCallInfo(
                url=url,
                method=method_str.upper(),
                response_type=response_type,
                file_path=file_path,
                line=line,
            )
        )

    return results

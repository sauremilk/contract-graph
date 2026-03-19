"""API Type Sync Discoverer — matches Pydantic models to TypeScript interfaces."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from contract_graph.discovery.base import BaseDiscoverer, DiscovererRegistry
from contract_graph.graph.model import (
    ContractEdge,
    ContractGraph,
    ContractNode,
    EdgeKind,
    FieldInfo,
    FieldMismatch,
    MismatchKind,
    NodeKind,
    Severity,
)
from contract_graph.parsing.python_parser import PydanticModelInfo, parse_pydantic_models
from contract_graph.parsing.typescript_parser import TSInterfaceInfo, parse_ts_interfaces


# ── Type Compatibility ─────────────────────────────────────────────

# Python type → set of compatible TypeScript types
_DEFAULT_TYPE_MAP: dict[str, set[str]] = {
    "str": {"string"},
    "int": {"number"},
    "float": {"number"},
    "bool": {"boolean"},
    "datetime": {"string", "Date"},
    "date": {"string", "Date"},
    "UUID": {"string"},
    "uuid": {"string"},
    "Any": {"any", "unknown"},
    "None": {"null", "undefined", "void"},
    "NoneType": {"null", "undefined", "void"},
    "bytes": {"string", "Blob", "ArrayBuffer"},
    "Decimal": {"number", "string"},
}


def _normalize_python_type(type_str: str) -> tuple[str, bool]:
    """Normalize a Python type annotation. Returns (base_type, is_optional)."""
    s = type_str.strip()
    is_optional = False

    # Handle Optional[X]
    m = re.match(r"Optional\[(.+)\]", s)
    if m:
        s = m.group(1).strip()
        is_optional = True

    # Handle X | None
    if " | None" in s:
        s = s.replace(" | None", "").strip()
        is_optional = True
    if "None | " in s:
        s = s.replace("None | ", "").strip()
        is_optional = True

    # Handle list[X] → extract X
    m = re.match(r"list\[(.+)\]", s, re.IGNORECASE)
    if m:
        return f"list[{m.group(1).strip()}]", is_optional

    # Handle dict[K, V]
    m = re.match(r"dict\[(.+),\s*(.+)\]", s, re.IGNORECASE)
    if m:
        return f"dict[{m.group(1).strip()}, {m.group(2).strip()}]", is_optional

    return s, is_optional


def _normalize_ts_type(type_str: str) -> tuple[str, bool]:
    """Normalize a TypeScript type. Returns (base_type, is_optional)."""
    s = type_str.strip()
    is_optional = False

    # Handle T | null | undefined
    parts = [p.strip() for p in s.split("|")]
    non_null = [p for p in parts if p not in ("null", "undefined")]
    if len(non_null) < len(parts):
        is_optional = True
    s = " | ".join(non_null) if non_null else s

    return s, is_optional


def _types_compatible(
    py_type: str,
    ts_type: str,
    custom_map: dict[str, set[str]] | None = None,
) -> bool:
    """Check if a Python type is compatible with a TypeScript type."""
    type_map = {**_DEFAULT_TYPE_MAP, **(custom_map or {})}

    py_base, _ = _normalize_python_type(py_type)
    ts_base, _ = _normalize_ts_type(ts_type)

    # Direct match
    if py_base.lower() == ts_base.lower():
        return True

    # list[X] → X[] or Array<X>
    list_m = re.match(r"list\[(.+)\]", py_base, re.IGNORECASE)
    if list_m:
        inner = list_m.group(1)
        if ts_base.endswith("[]"):
            return _types_compatible(inner, ts_base[:-2], custom_map)
        arr_m = re.match(r"Array<(.+)>", ts_base)
        if arr_m:
            return _types_compatible(inner, arr_m.group(1), custom_map)

    # dict[K, V] → Record<K, V>
    dict_m = re.match(r"dict\[(.+),\s*(.+)\]", py_base, re.IGNORECASE)
    if dict_m:
        rec_m = re.match(r"Record<(.+),\s*(.+)>", ts_base)
        if rec_m:
            return _types_compatible(dict_m.group(1), rec_m.group(1), custom_map) and _types_compatible(
                dict_m.group(2), rec_m.group(2), custom_map
            )

    # Check mapping table
    for py_key, ts_set in type_map.items():
        if py_base.lower() == py_key.lower():
            if ts_base.lower() in {t.lower() for t in ts_set}:
                return True

    return False


# ── Name Matching ──────────────────────────────────────────────────


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    s = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
    return s


def _field_names_match(py_name: str, ts_name: str, naming: str = "auto") -> bool:
    """Check if a Python field name matches a TypeScript field name."""
    if py_name == ts_name:
        return True
    if naming in ("auto", "snake_to_camel"):
        if _snake_to_camel(py_name) == ts_name:
            return True
    if naming in ("auto", "camel_to_snake"):
        if _camel_to_snake(ts_name) == py_name:
            return True
    return False


def _model_names_match(
    py_name: str,
    ts_name: str,
    custom_mappings: list[dict[str, str]] | None = None,
) -> tuple[bool, float]:
    """Check if a Pydantic model name matches a TS interface name.

    Returns (matches, confidence).
    """
    # Custom mapping first
    if custom_mappings:
        for mapping in custom_mappings:
            if mapping.get("provider") == py_name and mapping.get("consumer") == ts_name:
                return True, 1.0

    # Exact match
    if py_name == ts_name:
        return True, 1.0

    # Case-insensitive
    if py_name.lower() == ts_name.lower():
        return True, 0.95

    # Common suffix patterns: UserResponse ↔ UserResponseDTO, UserOut ↔ User
    suffixes_to_strip = ["DTO", "Out", "In", "Create", "Update", "Response", "Request", "Schema"]
    py_stripped = py_name
    ts_stripped = ts_name
    for suffix in suffixes_to_strip:
        if py_name.endswith(suffix):
            py_stripped = py_name[: -len(suffix)]
        if ts_name.endswith(suffix):
            ts_stripped = ts_name[: -len(suffix)]

    if py_stripped == ts_stripped and py_stripped != py_name:
        return True, 0.8

    return False, 0.0


# ── Discoverer ─────────────────────────────────────────────────────


@DiscovererRegistry.register
class ApiTypeSyncDiscoverer(BaseDiscoverer):
    """Discovers Pydantic ↔ TypeScript type sync contracts.

    Scans configured provider paths for Pydantic models and consumer paths
    for TypeScript interfaces/types, then matches them by name and compares
    field schemas for compatibility.
    """

    name = "api_type_sync"

    def discover(
        self,
        graph: ContractGraph,
        config: dict[str, Any],
        root: str,
    ) -> tuple[list[ContractNode], list[ContractEdge]]:
        root_path = Path(root)
        nodes: list[ContractNode] = []
        edges: list[ContractEdge] = []

        # Parse config
        providers_cfg = config.get("providers", [])
        consumers_cfg = config.get("consumers", [])
        field_naming = config.get("field_naming", {})
        naming_mode = "auto"
        if field_naming.get("provider") == "snake_case" and field_naming.get("consumer") == "camelCase":
            naming_mode = "snake_to_camel"
        custom_mappings = config.get("custom_mappings", [])
        custom_bases = frozenset(config.get("base_classes", ["BaseModel", "SQLModel"]))

        # Collect custom type map
        custom_type_map: dict[str, set[str]] | None = None
        tc = config.get("type_compatibility")
        if tc and isinstance(tc, dict):
            custom_type_map = {}
            for py_t, ts_ts in tc.items():
                if isinstance(ts_ts, list):
                    custom_type_map[py_t] = set(ts_ts)

        # ── Scan Providers (Python) ──
        py_models: list[PydanticModelInfo] = []
        for pcfg in providers_cfg:
            pattern = pcfg.get("path", pcfg) if isinstance(pcfg, dict) else pcfg
            bases = frozenset(pcfg.get("base_classes", custom_bases)) if isinstance(pcfg, dict) else custom_bases
            for py_file in root_path.glob(pattern):
                if py_file.is_file():
                    py_models.extend(parse_pydantic_models(py_file, bases))

        # ── Scan Consumers (TypeScript) ──
        ts_interfaces: list[TSInterfaceInfo] = []
        for ccfg in consumers_cfg:
            pattern = ccfg.get("path", ccfg) if isinstance(ccfg, dict) else ccfg
            for ts_file in root_path.glob(pattern):
                if ts_file.is_file():
                    ts_interfaces.extend(parse_ts_interfaces(ts_file))

        # ── Create Nodes ──
        py_node_map: dict[str, ContractNode] = {}
        for model in py_models:
            rel = model.file_path.relative_to(root_path).as_posix()
            node_id = f"{rel}::{model.name}"
            node = ContractNode(
                id=node_id,
                kind=NodeKind.PYDANTIC_MODEL,
                file_path=model.file_path,
                name=model.name,
                fields=model.fields,
                line_start=model.line_start,
                line_end=model.line_end,
            )
            nodes.append(node)
            py_node_map[model.name] = node

        ts_node_map: dict[str, ContractNode] = {}
        for iface in ts_interfaces:
            rel = iface.file_path.relative_to(root_path).as_posix()
            kind = NodeKind.TS_INTERFACE if iface.kind == "interface" else NodeKind.TS_TYPE
            node_id = f"{rel}::{iface.name}"
            node = ContractNode(
                id=node_id,
                kind=kind,
                file_path=iface.file_path,
                name=iface.name,
                fields=iface.fields,
                line_start=iface.line_start,
                line_end=iface.line_end,
            )
            nodes.append(node)
            ts_node_map[iface.name] = node

        # ── Match & Compare ──
        for py_name, py_node in py_node_map.items():
            for ts_name, ts_node in ts_node_map.items():
                matched, confidence = _model_names_match(py_name, ts_name, custom_mappings)
                if not matched:
                    continue

                mismatches = self._compare_fields(py_node, ts_node, naming_mode, custom_type_map)
                total_fields = max(len(py_node.fields), len(ts_node.fields), 1)
                matched_count = total_fields - len(mismatches)
                coverage = matched_count / total_fields

                severity = self._compute_severity(mismatches)

                edges.append(
                    ContractEdge(
                        source=py_node.id,
                        target=ts_node.id,
                        kind=EdgeKind.API_TYPE_SYNC,
                        confidence=confidence,
                        field_coverage=coverage,
                        mismatches=mismatches,
                        severity=severity,
                    )
                )

        return nodes, edges

    def _compare_fields(
        self,
        provider: ContractNode,
        consumer: ContractNode,
        naming_mode: str,
        custom_type_map: dict[str, set[str]] | None,
    ) -> list[FieldMismatch]:
        """Compare fields between provider (Python) and consumer (TypeScript)."""
        mismatches: list[FieldMismatch] = []

        # Map consumer fields by potential provider names
        consumer_by_provider_name: dict[str, FieldInfo] = {}
        for ts_name, ts_field in consumer.fields.items():
            consumer_by_provider_name[ts_name] = ts_field
            # Also index by snake_case equivalent
            snake = _camel_to_snake(ts_name)
            if snake != ts_name:
                consumer_by_provider_name[snake] = ts_field

        for py_name, py_field in provider.fields.items():
            # Find matching consumer field
            ts_field: FieldInfo | None = None

            if py_name in consumer_by_provider_name:
                ts_field = consumer_by_provider_name[py_name]
            else:
                # Try camelCase
                camel = _snake_to_camel(py_name)
                ts_field = consumer_by_provider_name.get(camel)

            if ts_field is None:
                mismatches.append(
                    FieldMismatch(
                        field_name=py_name,
                        provider_type=py_field.type_str,
                        consumer_type=None,
                        mismatch_kind=MismatchKind.MISSING_IN_CONSUMER,
                    )
                )
                continue

            # Check type compatibility
            if not _types_compatible(py_field.type_str, ts_field.type_str, custom_type_map):
                mismatches.append(
                    FieldMismatch(
                        field_name=py_name,
                        provider_type=py_field.type_str,
                        consumer_type=ts_field.type_str,
                        mismatch_kind=MismatchKind.TYPE_INCOMPATIBLE,
                    )
                )

            # Check optionality
            py_optional = py_field.is_optional
            ts_optional = ts_field.is_optional
            if py_optional and not ts_optional:
                mismatches.append(
                    FieldMismatch(
                        field_name=py_name,
                        provider_type=f"Optional[{py_field.type_str}]",
                        consumer_type=ts_field.type_str,
                        mismatch_kind=MismatchKind.OPTIONALITY_MISMATCH,
                    )
                )

        # Check for fields in consumer but not in provider
        provider_names = set(provider.fields.keys())
        provider_camel_names = {_snake_to_camel(n) for n in provider_names}
        all_provider = provider_names | provider_camel_names

        for ts_name, ts_field in consumer.fields.items():
            if ts_name not in all_provider and _camel_to_snake(ts_name) not in provider_names:
                mismatches.append(
                    FieldMismatch(
                        field_name=ts_name,
                        provider_type=None,
                        consumer_type=ts_field.type_str,
                        mismatch_kind=MismatchKind.MISSING_IN_PROVIDER,
                    )
                )

        return mismatches

    @staticmethod
    def _compute_severity(mismatches: list[FieldMismatch]) -> Severity:
        """Determine severity based on mismatch types."""
        if not mismatches:
            return Severity.INFO

        kinds = {m.mismatch_kind for m in mismatches}
        missing_count = sum(1 for m in mismatches if m.mismatch_kind == MismatchKind.MISSING_IN_CONSUMER)

        if MismatchKind.TYPE_INCOMPATIBLE in kinds:
            return Severity.HIGH
        if missing_count >= 3:
            return Severity.HIGH
        if MismatchKind.MISSING_IN_CONSUMER in kinds:
            return Severity.MEDIUM
        if MismatchKind.OPTIONALITY_MISMATCH in kinds:
            return Severity.MEDIUM
        return Severity.LOW

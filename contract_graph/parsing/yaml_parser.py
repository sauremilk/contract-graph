"""YAML parser — extracts config key hierarchies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ConfigKeyInfo:
    """A config key defined in a YAML file."""

    key: str  # Dotted path: "pipeline.parallel_t1"
    value_type: str  # "bool", "int", "str", "list", "dict", "null"
    file_path: Path
    line: int  # approximate


def _flatten_yaml(data: dict, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively flatten a YAML dict into dotted key paths."""
    result: list[tuple[str, str]] = []
    for k, v in data.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            result.extend(_flatten_yaml(v, key))
        else:
            vtype = type(v).__name__ if v is not None else "null"
            result.append((key, vtype))
    return result


def parse_yaml_config(file_path: Path) -> list[ConfigKeyInfo]:
    """Parse a YAML config file and return all defined keys."""
    source = file_path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(source)
    except yaml.YAMLError:
        return []

    if not isinstance(data, dict):
        return []

    keys = _flatten_yaml(data)
    return [
        ConfigKeyInfo(
            key=key,
            value_type=vtype,
            file_path=file_path,
            line=0,  # YAML doesn't give line numbers easily without ruamel
        )
        for key, vtype in keys
    ]

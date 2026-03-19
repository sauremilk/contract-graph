"""Config loader and validation for contract-graph.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ConfigError(Exception):
    """Raised when a config file is explicitly provided but cannot be loaded."""


class FieldNamingConfig(BaseModel):
    provider: str = "snake_case"
    consumer: str = "camelCase"


class ProviderConfig(BaseModel):
    path: str
    base_classes: list[str] = Field(default_factory=lambda: ["BaseModel", "SQLModel"])


class ConsumerConfig(BaseModel):
    path: str
    patterns: list[str] = Field(default_factory=lambda: ["interface", "type"])


class CustomMapping(BaseModel):
    provider: str
    consumer: str


class ApiTypeSyncConfig(BaseModel):
    enabled: bool = True
    providers: list[ProviderConfig | str] = Field(default_factory=list)
    consumers: list[ConsumerConfig | str] = Field(default_factory=list)
    field_naming: FieldNamingConfig = Field(default_factory=FieldNamingConfig)
    custom_mappings: list[CustomMapping] = Field(default_factory=list)
    type_compatibility: dict[str, list[str]] = Field(default_factory=dict)


class ConfigUsageConfig(BaseModel):
    enabled: bool = False
    definitions: list[str] = Field(default_factory=list)
    readers: list[str] = Field(default_factory=list)


class RouteActivationConfig(BaseModel):
    enabled: bool = False
    backend_routes: list[str] = Field(default_factory=list)
    frontend_calls: list[str] = Field(default_factory=list)


class DiscoveryConfig(BaseModel):
    api_type_sync: ApiTypeSyncConfig = Field(default_factory=ApiTypeSyncConfig)
    config_usage: ConfigUsageConfig = Field(default_factory=ConfigUsageConfig)
    route_activation: RouteActivationConfig = Field(default_factory=RouteActivationConfig)


class PolicyConfig(BaseModel):
    name: str
    enabled: bool = True
    severity: str = "medium"


class ScoringWeights(BaseModel):
    api_type_sync: float = 0.35
    route_activation: float = 0.25
    config_usage: float = 0.15
    schema_evolution: float = 0.15
    instruction_coherence: float = 0.10


class ScoringConfig(BaseModel):
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    severity_gate: str = "high"


class ContractGraphConfig(BaseModel):
    """Root config model for contract-graph.yaml."""

    version: str = "1.0"
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(
        default_factory=lambda: [
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/dist/**",
        ]
    )
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    policies: list[PolicyConfig] = Field(default_factory=list)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


def load_config(config_path: Path | str | None = None) -> ContractGraphConfig:
    """Load config from YAML file. Falls back to defaults if no file found.

    Raises ConfigError if an explicitly provided config file is corrupt or unreadable.
    """
    explicitly_provided = config_path is not None

    if config_path is None:
        # Try common names
        for name in (
            "contract-graph.yaml",
            "contract-graph.yml",
            ".contract-graph.yaml",
        ):
            p = Path(name)
            if p.exists():
                config_path = p
                break

    if config_path is None:
        return ContractGraphConfig()

    path = Path(config_path)
    if not path.exists():
        if explicitly_provided:
            raise ConfigError(f"Config file not found: {path}")
        return ContractGraphConfig()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError) as exc:
        if explicitly_provided:
            raise ConfigError(f"Failed to parse {path}: {exc}") from exc
        return ContractGraphConfig()
    if not isinstance(raw, dict):
        if explicitly_provided:
            raise ConfigError(f"Config file {path} does not contain a YAML mapping")
        return ContractGraphConfig()

    return ContractGraphConfig.model_validate(raw)


def generate_default_config(preset: str = "fullstack") -> dict[str, Any]:
    """Generate a default config dict for a given preset."""
    base: dict[str, Any] = {
        "version": "1.0",
        "include": [],
        "exclude": [
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/dist/**",
            "**/build/**",
        ],
        "discovery": {
            "api_type_sync": {
                "enabled": True,
                "providers": [],
                "consumers": [],
                "field_naming": {"provider": "snake_case", "consumer": "camelCase"},
                "custom_mappings": [],
                "type_compatibility": {
                    "str": ["string"],
                    "int": ["number"],
                    "float": ["number"],
                    "bool": ["boolean"],
                    "datetime": ["string", "Date"],
                    "UUID": ["string"],
                },
            },
            "config_usage": {"enabled": False},
            "route_activation": {"enabled": False},
        },
        "policies": [
            {
                "name": "no_missing_consumer_fields",
                "enabled": True,
                "severity": "medium",
            },
            {"name": "no_type_incompatibility", "enabled": True, "severity": "high"},
            {"name": "no_phantom_types", "enabled": True, "severity": "medium"},
        ],
        "scoring": {
            "weights": {
                "api_type_sync": 0.35,
                "route_activation": 0.25,
                "config_usage": 0.15,
                "schema_evolution": 0.15,
                "instruction_coherence": 0.10,
            },
            "severity_gate": "high",
        },
    }

    if preset == "fullstack":
        base["include"] = [
            "backend/**/*.py",
            "dashboard/src/**/*.ts",
            "dashboard/src/**/*.tsx",
            "config/**/*.yaml",
        ]
        base["discovery"]["api_type_sync"]["providers"] = [
            {
                "path": "backend/api/models/**/*.py",
                "base_classes": ["BaseModel", "SQLModel"],
            }
        ]
        base["discovery"]["api_type_sync"]["consumers"] = [
            {"path": "dashboard/src/shared/types/**/*.ts"},
            {"path": "dashboard/src/features/**/types.ts"},
        ]
    elif preset == "backend-only":
        base["include"] = ["backend/**/*.py", "config/**/*.yaml"]
        base["discovery"]["api_type_sync"]["enabled"] = False
    elif preset == "agent-system":
        base["include"] = [
            ".github/**/*.md",
            "backend/**/*.py",
            "dashboard/src/**/*.ts",
        ]
        base["discovery"]["api_type_sync"]["providers"] = [{"path": "backend/api/models/**/*.py"}]
        base["discovery"]["api_type_sync"]["consumers"] = [{"path": "dashboard/src/**/*.ts"}]

    return base

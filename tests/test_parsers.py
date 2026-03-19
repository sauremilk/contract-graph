"""Tests for Python, TypeScript and YAML parsers."""

from __future__ import annotations

import textwrap
from pathlib import Path

from contract_graph.parsing.python_parser import (
    parse_pydantic_models,
    parse_fastapi_routes,
)
from contract_graph.parsing.typescript_parser import (
    parse_ts_interfaces,
    parse_ts_api_calls,
)
from contract_graph.parsing.yaml_parser import parse_yaml_config


class TestPydanticParser:
    def test_parse_fixture_models(self, fullstack_basic: Path):
        models = parse_pydantic_models(fullstack_basic / "backend" / "models.py")
        names = {m.name for m in models}
        assert "MatchResponse" in names
        assert "PlayerStats" in names
        assert "SessionConfig" in names

    def test_fields_extracted(self, fullstack_basic: Path):
        models = parse_pydantic_models(fullstack_basic / "backend" / "models.py")
        match_model = next(m for m in models if m.name == "MatchResponse")
        field_names = set(match_model.fields.keys())
        assert "id" in field_names
        assert "player_name" in field_names
        assert "kills" in field_names

    def test_field_types(self, fullstack_basic: Path):
        models = parse_pydantic_models(fullstack_basic / "backend" / "models.py")
        stats = next(m for m in models if m.name == "PlayerStats")
        assert stats.fields["player_id"].type_str == "UUID"
        assert stats.fields["total_matches"].type_str == "int"

    def test_parse_from_source(self, tmp_path: Path):
        src = textwrap.dedent("""\
            from pydantic import BaseModel

            class Foo(BaseModel):
                bar: str
                baz: int = 0
        """)
        f = tmp_path / "test_model.py"
        f.write_text(src)
        models = parse_pydantic_models(f)
        assert len(models) == 1
        assert models[0].name == "Foo"
        assert len(models[0].fields) == 2

    def test_non_pydantic_class_ignored(self, tmp_path: Path):
        src = textwrap.dedent("""\
            class Plain:
                x: int
        """)
        f = tmp_path / "plain.py"
        f.write_text(src)
        models = parse_pydantic_models(f)
        assert len(models) == 0


class TestFastAPIParser:
    def test_parse_fixture_routes(self, fullstack_basic: Path):
        routes = parse_fastapi_routes(fullstack_basic / "backend" / "routes.py")
        paths = {r.path for r in routes}
        assert "/matches/{match_id}" in paths
        assert "/players/{player_id}/stats" in paths

    def test_route_methods(self, fullstack_basic: Path):
        routes = parse_fastapi_routes(fullstack_basic / "backend" / "routes.py")
        route_map = {r.path: r for r in routes}
        assert route_map["/matches/{match_id}"].method == "GET"
        assert route_map["/sessions/config"].method == "POST"


class TestTSParser:
    def test_parse_fixture_interfaces(self, fullstack_basic: Path):
        interfaces = parse_ts_interfaces(fullstack_basic / "frontend" / "types.ts")
        names = {i.name for i in interfaces}
        assert "MatchResponse" in names
        assert "PlayerStats" in names
        assert "TournamentBracket" in names

    def test_interface_fields(self, fullstack_basic: Path):
        interfaces = parse_ts_interfaces(fullstack_basic / "frontend" / "types.ts")
        match_iface = next(i for i in interfaces if i.name == "MatchResponse")
        field_names = set(match_iface.fields.keys())
        assert "id" in field_names
        assert "playerName" in field_names
        assert "score" in field_names

    def test_optional_fields(self, fullstack_basic: Path):
        interfaces = parse_ts_interfaces(fullstack_basic / "frontend" / "types.ts")
        stats = next(i for i in interfaces if i.name == "PlayerStats")
        assert stats.fields["lastPlayed"].is_optional is True
        assert stats.fields["displayName"].is_optional is False

    def test_api_calls_parsing(self, tmp_path: Path):
        src = textwrap.dedent("""\
            const data = await fetch('/api/matches');
            const res = axios.get('/api/players/123');
        """)
        f = tmp_path / "api.ts"
        f.write_text(src)
        calls = parse_ts_api_calls(f)
        urls = {c.url for c in calls}
        assert "/api/matches" in urls
        assert "/api/players/123" in urls


class TestYAMLParser:
    def test_parse_fixture_config(self, fullstack_basic: Path):
        keys = parse_yaml_config(fullstack_basic / "config" / "config.yaml")
        key_names = {k.key for k in keys}
        assert "app.name" in key_names
        assert "database.host" in key_names
        assert "features.overlay" in key_names

    def test_flat_keys(self, tmp_path: Path):
        src = "a:\n  b:\n    c: 1\n  d: 2\n"
        f = tmp_path / "test.yaml"
        f.write_text(src)
        keys = parse_yaml_config(f)
        key_names = {k.key for k in keys}
        assert "a.b.c" in key_names
        assert "a.d" in key_names

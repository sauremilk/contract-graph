"""Python AST parser — extracts Pydantic models, FastAPI routes, SQLAlchemy models, config readers."""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contract_graph.graph.model import FieldInfo

logger = logging.getLogger(__name__)

# ── Data Structures ────────────────────────────────────────────────


@dataclass
class PydanticModelInfo:
    """Parsed Pydantic BaseModel or SQLModel."""

    name: str
    file_path: Path
    fields: dict[str, FieldInfo]
    base_classes: list[str]
    line_start: int
    line_end: int


@dataclass
class FastAPIRouteInfo:
    """Parsed FastAPI route decorator."""

    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str  # "/api/v1/users"
    handler_name: str
    response_model: str | None
    file_path: Path
    line_start: int
    line_end: int
    is_active: bool = True


@dataclass
class ConfigReaderInfo:
    """A config key read from code."""

    key: str  # "pipeline.parallel_t1"
    file_path: Path
    line: int
    access_pattern: str  # 'subscript', 'attribute', 'get'


# ── AST Visitors ───────────────────────────────────────────────────

# Known Pydantic / SQLModel base classes
_PYDANTIC_BASES = frozenset({"BaseModel", "SQLModel", "BaseSettings"})


def _resolve_annotation(node: ast.expr) -> str:
    """Best-effort annotation-to-string conversion."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Attribute):
        return f"{_resolve_annotation(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        base = _resolve_annotation(node.value)
        sl = _resolve_annotation(node.slice)
        return f"{base}[{sl}]"
    if isinstance(node, ast.Tuple):
        parts = ", ".join(_resolve_annotation(e) for e in node.elts)
        return parts
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _resolve_annotation(node.left)
        right = _resolve_annotation(node.right)
        return f"{left} | {right}"
    if isinstance(node, ast.List):
        parts = ", ".join(_resolve_annotation(e) for e in node.elts)
        return f"[{parts}]"
    return "Any"


def _is_optional(annotation_str: str) -> bool:
    """Check if an annotation string represents an optional type."""
    lowered = annotation_str.lower()
    return "optional[" in lowered or re.search(r"\bnone\b", lowered) is not None


def _unwrap_annotated(type_str: str) -> str:
    """Extract base type T from Annotated[T, ...]. Returns type_str unchanged if not Annotated."""
    m = re.match(r"Annotated\[(.+)\]", type_str)
    if not m:
        return type_str
    inner = m.group(1)
    # Split at the first top-level comma to get just T
    depth = 0
    for i, ch in enumerate(inner):
        if ch in ("[", "("):
            depth += 1
        elif ch in ("]", ")"):
            depth -= 1
        elif ch == "," and depth == 0:
            return inner[:i].strip()
    return inner.strip()


class _PydanticVisitor(ast.NodeVisitor):
    """Discovers Pydantic BaseModel subclasses and extracts field schemas."""

    def __init__(self, file_path: Path, target_bases: frozenset[str]) -> None:
        self.file_path = file_path
        self.target_bases = target_bases
        self.models: list[PydanticModelInfo] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        base_names = [_resolve_annotation(b) for b in node.bases]
        # Support dotted names like pydantic.BaseModel → check last component too
        base_last_parts = [b.rsplit(".", 1)[-1] for b in base_names]
        if not any(
            b in self.target_bases or lp in self.target_bases for b, lp in zip(base_names, base_last_parts, strict=True)
        ):
            self.generic_visit(node)
            return

        fields: dict[str, FieldInfo] = {}
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fname = stmt.target.id
                if fname.startswith("_"):
                    continue
                type_str = _resolve_annotation(stmt.annotation) if stmt.annotation else "Any"
                type_str = _unwrap_annotated(type_str)
                has_default = stmt.value is not None
                optional = _is_optional(type_str)
                fields[fname] = FieldInfo(
                    name=fname,
                    type_str=type_str,
                    is_optional=optional,
                    has_default=has_default,
                )

            # Handle @computed_field decorated properties
            if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
                for dec in stmt.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Name):
                            dec_name = dec.func.id
                        elif isinstance(dec.func, ast.Attribute):
                            dec_name = dec.func.attr
                    if dec_name == "computed_field" and stmt.returns:
                        fname = stmt.name
                        if not fname.startswith("_"):
                            type_str = _resolve_annotation(stmt.returns)
                            type_str = _unwrap_annotated(type_str)
                            fields[fname] = FieldInfo(
                                name=fname,
                                type_str=type_str,
                                is_optional=_is_optional(type_str),
                                has_default=True,
                            )
                        break

        self.models.append(
            PydanticModelInfo(
                name=node.name,
                file_path=self.file_path,
                fields=fields,
                base_classes=base_names,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            )
        )
        self.generic_visit(node)


_HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "head", "options"})


class _RouteVisitor(ast.NodeVisitor):
    """Discovers FastAPI @router.get/post/... decorated functions."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.routes: list[FastAPIRouteInfo] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_decorators(node)
        self.generic_visit(node)

    def _check_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func if isinstance(dec, ast.Call) else dec
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in _HTTP_METHODS:
                continue

            # Extract path argument
            path = ""
            if dec.args:
                first = dec.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    path = first.value

            # Extract response_model keyword
            response_model = None
            for kw in dec.keywords:
                if kw.arg == "response_model":
                    response_model = _resolve_annotation(kw.value)

            self.routes.append(
                FastAPIRouteInfo(
                    method=func.attr.upper(),
                    path=path,
                    handler_name=node.name,
                    response_model=response_model,
                    file_path=self.file_path,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                )
            )


class _ConfigReaderVisitor(ast.NodeVisitor):
    """Discovers config key reads: config["key"], settings.key, config.get("key")."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.reads: list[ConfigReaderInfo] = []

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # config["key"] or config['key']
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            self.reads.append(
                ConfigReaderInfo(
                    key=node.slice.value,
                    file_path=self.file_path,
                    line=node.lineno,
                    access_pattern="subscript",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # config.get("key") or settings.get("key")
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            self.reads.append(
                ConfigReaderInfo(
                    key=node.args[0].value,
                    file_path=self.file_path,
                    line=node.lineno,
                    access_pattern="get",
                )
            )
        self.generic_visit(node)


# ── Public API ─────────────────────────────────────────────────────


def parse_python_file(
    file_path: Path,
    extract_models: bool = True,
    extract_routes: bool = True,
    extract_config_reads: bool = True,
    custom_bases: frozenset[str] | None = None,
) -> dict[str, list[Any]]:
    """Parse a Python file and extract Pydantic models, routes, and config reads.

    Returns a dict with keys: 'models', 'routes', 'config_reads'.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        logger.warning("Skipping %s: %s", file_path, exc)
        return {"models": [], "routes": [], "config_reads": [], "skipped": [str(file_path)]}
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        logger.warning("Skipping %s: SyntaxError at line %s", file_path, exc.lineno)
        return {"models": [], "routes": [], "config_reads": [], "skipped": [str(file_path)]}

    result: dict[str, list[Any]] = {"models": [], "routes": [], "config_reads": []}
    bases = custom_bases if custom_bases else _PYDANTIC_BASES

    if extract_models:
        visitor = _PydanticVisitor(file_path, bases)
        visitor.visit(tree)
        result["models"] = visitor.models

    if extract_routes:
        rv = _RouteVisitor(file_path)
        rv.visit(tree)
        result["routes"] = rv.routes

    if extract_config_reads:
        cv = _ConfigReaderVisitor(file_path)
        cv.visit(tree)
        result["config_reads"] = cv.reads

    return result


def parse_pydantic_models(file_path: Path, custom_bases: frozenset[str] | None = None) -> list[PydanticModelInfo]:
    """Convenience: extract only Pydantic models from a file."""
    return parse_python_file(
        file_path,
        extract_routes=False,
        extract_config_reads=False,
        custom_bases=custom_bases,
    )["models"]


def parse_fastapi_routes(file_path: Path) -> list[FastAPIRouteInfo]:
    """Convenience: extract only FastAPI routes from a file."""
    return parse_python_file(file_path, extract_models=False, extract_config_reads=False)["routes"]

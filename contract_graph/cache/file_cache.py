"""File-based parse cache using SHA-256 hashes."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any


class FileCache:
    """SHA-256 keyed parse cache to skip unchanged files.

    Stores parsed results in `.contract-graph-cache/` as JSON files keyed by file hash.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._dir = cache_dir or Path(".contract-graph-cache")
        self._dir.mkdir(parents=True, exist_ok=True)

    def _file_hash(self, file_path: Path) -> str:
        try:
            content = file_path.read_bytes()
        except OSError:
            return "unreadable"
        return hashlib.sha256(content).hexdigest()[:16]

    def _cache_path(self, file_hash: str, category: str) -> Path:
        return self._dir / f"{file_hash}_{category}.json"

    def get(self, file_path: Path, category: str) -> Any | None:
        """Get cached result for a file, or None if cache miss."""
        if not file_path.exists():
            return None
        fhash = self._file_hash(file_path)
        cp = self._cache_path(fhash, category)
        if cp.exists():
            try:
                return json.loads(cp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def put(self, file_path: Path, category: str, data: Any) -> None:
        """Store a result in the cache (atomic write via temp file)."""
        fhash = self._file_hash(file_path)
        cp = self._cache_path(fhash, category)
        try:
            fd, tmp = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp")
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
            Path(tmp).replace(cp)
        except OSError:
            pass  # cache write failure is non-fatal

    def clear(self) -> int:
        """Remove all cached files. Returns count of removed files."""
        count = 0
        for f in self._dir.glob("*.json"):
            f.unlink()
            count += 1
        return count

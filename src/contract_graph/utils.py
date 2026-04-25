"""Shared utility functions for contract-graph."""

from __future__ import annotations

import hashlib
from pathlib import Path


def file_content_hash(path: Path) -> str:
    """Return a 32-character SHA-256 hex digest of the file content."""
    try:
        content = path.read_bytes()
    except OSError:
        return "unreadable"
    return hashlib.sha256(content).hexdigest()[:32]

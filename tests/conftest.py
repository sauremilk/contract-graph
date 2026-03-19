"""Shared test fixtures for contract-graph."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FULLSTACK_BASIC = FIXTURES_DIR / "fullstack_basic"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def fullstack_basic() -> Path:
    return FULLSTACK_BASIC

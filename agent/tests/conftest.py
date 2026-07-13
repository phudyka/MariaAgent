"""Fixtures partagées : agent/ dans sys.path + DB seedée en répertoire temporaire."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

import db  # noqa: E402
import seed_db  # noqa: E402


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """DB seedée depuis les CSV mock, isolée dans tmp_path."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "maria.db")
    seed_db.seed()
    return db

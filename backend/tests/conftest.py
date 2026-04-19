"""Shared fixtures: load backend/.env before anything imports main."""

from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app)

"""Helpers for Mongo-backed tests (avoid importing `tests` as a top-level package name)."""

from __future__ import annotations

import os

import pytest


def require_mongo_uri() -> None:
    if not os.getenv("MONGODB_URI"):
        pytest.skip("MONGODB_URI not set (check backend/.env)")

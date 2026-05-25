"""Shared pytest configuration for backend tests."""

from __future__ import annotations

import os
import sys

import pytest

# Headless Qt and skip network update checks during tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("HAPAG_SKIP_BACKGROUND_UPDATE", "1")

# Ensure backend package root is importable
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)


@pytest.fixture(scope="session")
def qapp():
    """Single QApplication for widget tests in this session."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

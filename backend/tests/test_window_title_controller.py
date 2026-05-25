"""Unit tests for WindowTitleController."""

from __future__ import annotations

import sys
import types

import pytest

from ui.controllers.window_title_controller import WindowTitleController


@pytest.fixture
def cloud_mode(monkeypatch):
    app_settings_mod = types.ModuleType("core.app_settings")
    app_settings_mod.get_mode = lambda: "cloud"
    monkeypatch.setitem(sys.modules, "core.app_settings", app_settings_mod)


class DummyWindow:
    def __init__(self):
        self.title = ""

    def setWindowTitle(self, title):
        self.title = title


def test_update_title_includes_mode_and_user(cloud_mode):
    win = DummyWindow()
    ctrl = WindowTitleController(win)
    ctrl.update_title("Test User")

    assert "HAPAG Form 5A Comparator" in win.title
    assert "☁ CLOUD" in win.title
    assert "Test User" in win.title

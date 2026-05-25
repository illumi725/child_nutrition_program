"""Unit tests for NavigationController."""

from __future__ import annotations

import sys
import types

import pytest

from ui.controllers.navigation_controller import NavigationController


@pytest.fixture
def nav_env(monkeypatch):
    auth_mod = types.ModuleType("ui.auth_guard")
    auth_mod.user_has_permission = (
        lambda user, p: p != "bulk_transfer" or user.get("can_transfer", False)
    )
    auth_mod.require_permission = lambda parent, user, p: user.get("can_transfer", False)
    monkeypatch.setitem(sys.modules, "ui.auth_guard", auth_mod)

    current_theme = {"value": "light"}

    app_settings_mod = types.ModuleType("core.app_settings")
    app_settings_mod.get_theme = lambda: current_theme["value"]
    app_settings_mod.set_theme = lambda value: current_theme.update(value=value)
    monkeypatch.setitem(sys.modules, "core.app_settings", app_settings_mod)

    apply_theme_called = {"called": False, "theme": None}

    theme_mod = types.ModuleType("ui.theme")

    def apply_theme(app, theme):
        apply_theme_called["called"] = True
        apply_theme_called["theme"] = theme

    theme_mod.apply_theme = apply_theme
    monkeypatch.setitem(sys.modules, "ui.theme", theme_mod)

    return auth_mod, apply_theme_called


class DummyButton:
    def __init__(self):
        self.enabled = True
        self.text = ""
        self.tooltip = ""

    def setEnabled(self, value):
        self.enabled = value

    def setText(self, text):
        self.text = text

    def setToolTip(self, tip):
        self.tooltip = tip


class DummyMainWindow:
    def __init__(self, can_transfer=True):
        self.current_user = {"can_transfer": can_transfer}
        self.btn_bulk_transfer = DummyButton()
        self.btn_bulk_sync = DummyButton()
        self.btn_bulk_sync_fuzzy = DummyButton()
        self.btn_bulk_sync_potential = DummyButton()
        self.btn_theme_toggle = DummyButton()
        self._update_window_title_called = False
        self._start_auto_sync_timer_called = False

    def _update_window_title(self, user_display):
        self._update_window_title_called = True

    def _start_auto_sync_timer(self):
        self._start_auto_sync_timer_called = True


def test_apply_action_permissions(nav_env):
    win = DummyMainWindow(can_transfer=True)
    ctrl = NavigationController(win)
    ctrl.apply_action_permissions()

    assert win.btn_bulk_transfer.enabled is True
    assert win.btn_bulk_transfer.tooltip == ""
    assert win.btn_bulk_sync.enabled is True


def test_toggle_theme(nav_env, monkeypatch):
    _, apply_theme_called = nav_env
    win = DummyMainWindow()
    ctrl = NavigationController(win)

    import PySide6.QtWidgets as QtWidgets

    monkeypatch.setattr(
        QtWidgets.QApplication,
        "instance",
        staticmethod(lambda: None),
    )
    ctrl.toggle_theme()

    assert apply_theme_called["called"] is True
    assert apply_theme_called["theme"] == "dark"
    assert win.btn_theme_toggle.text == "☀️ Light"


def test_open_bulk_transfer_permission(nav_env, monkeypatch):
    auth_mod, _ = nav_env
    created_instances = []

    bulk_mod = types.ModuleType("ui.bulk_transfer_window")

    class DummyBulkTransferWindow:
        def __init__(self, parent):
            self.parent = parent
            self.exec_called = False
            created_instances.append(self)

        def exec(self):
            self.exec_called = True

    bulk_mod.BulkTransferWindow = DummyBulkTransferWindow
    monkeypatch.setitem(sys.modules, "ui.bulk_transfer_window", bulk_mod)

    win = DummyMainWindow()
    ctrl = NavigationController(win)

    auth_mod.require_permission = lambda parent, user, p: False
    ctrl.open_bulk_transfer()
    assert len(created_instances) == 0

    auth_mod.require_permission = lambda parent, user, p: True
    ctrl.open_bulk_transfer()
    assert len(created_instances) == 1
    assert created_instances[0].exec_called is True

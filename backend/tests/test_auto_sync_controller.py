"""Unit tests for AutoSyncController."""

from __future__ import annotations

import sys
import types

import pytest

from ui.controllers.auto_sync_controller import AutoSyncController


class _FakeSignal:
    def __init__(self):
        self._cb = None

    def connect(self, cb):
        self._cb = cb

    def emit(self, *args, **kwargs):
        if self._cb:
            self._cb(*args, **kwargs)


class FakeSyncWorker:
    MODE_SYNC = "sync"

    def __init__(self, mode=None, parent=None):
        self.mode = mode
        self.parent = parent
        self.finished = _FakeSignal()
        self.error = _FakeSignal()
        self.started = False

    def start(self):
        self.started = True
        self.finished.emit(True, "completed")


class FakeTimer:
    def __init__(self, parent=None):
        self.parent = parent
        self.interval = None
        self.connected_callback = None
        self.started = False
        self.timeout = self

    def setInterval(self, interval):
        self.interval = interval

    def connect(self, callback):
        self.connected_callback = callback

    def start(self):
        self.started = True


class DummyMainWindow:
    def __init__(self):
        self.logs = []

    def log_message(self, msg):
        self.logs.append(msg)


@pytest.fixture
def auto_sync_env(monkeypatch):
    core_sync = types.ModuleType("core.sync_engine")
    core_sync.SyncWorker = FakeSyncWorker
    monkeypatch.setitem(sys.modules, "core.sync_engine", core_sync)

    app_settings_mod = types.ModuleType("core.app_settings")
    app_settings_mod.get_mode = lambda: "local"
    app_settings_mod.get_auto_sync_enabled = lambda: True
    app_settings_mod.get_auto_sync_interval = lambda: 1
    monkeypatch.setitem(sys.modules, "core.app_settings", app_settings_mod)

    qtcore_mod = types.ModuleType("PySide6.QtCore")
    qtcore_mod.QTimer = FakeTimer
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qtcore_mod)


def test_start_auto_sync_timer(auto_sync_env):
    win = DummyMainWindow()
    ctrl = AutoSyncController(win)
    ctrl.start_auto_sync_timer()

    assert ctrl._timer is not None
    assert ctrl._timer.interval == 60000
    assert ctrl._timer.started is True


def test_run_background_sync(auto_sync_env):
    win = DummyMainWindow()
    ctrl = AutoSyncController(win)
    ctrl.run_background_sync()

    assert any("Auto-sync started" in m for m in win.logs)
    assert any("completed" in m for m in win.logs)

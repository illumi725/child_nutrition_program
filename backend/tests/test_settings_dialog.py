"""Unit tests for SettingsDialog sync worker wiring."""

from __future__ import annotations

import sys
import types

import pytest


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
    MODE_FULL = "full"

    def __init__(self, mode=None, parent=None):
        self.mode = mode
        self.parent = parent
        self.progress = _FakeSignal()
        self.finished = _FakeSignal()
        self.error = _FakeSignal()
        self.started = False

    def isRunning(self):
        return False

    def start(self):
        self.started = True
        self.progress.emit(50, "halfway")
        self.finished.emit(True, "done")


@pytest.fixture
def settings_dialog_env(monkeypatch):
    core_sync = types.ModuleType("core.sync_engine")
    core_sync.SyncWorker = FakeSyncWorker
    monkeypatch.setitem(sys.modules, "core.sync_engine", core_sync)

    fake_app_settings = types.ModuleType("core.app_settings")
    fake_app_settings.get_mode = lambda: "local"
    fake_app_settings.get_auto_sync_enabled = lambda: True
    fake_app_settings.get_auto_sync_interval = lambda: 15
    fake_app_settings.get_last_synced = lambda: "Never"
    monkeypatch.setitem(sys.modules, "core.app_settings", fake_app_settings)


def test_start_sync_worker_starts_fake_worker(settings_dialog_env, qapp, monkeypatch):
    import ui.components.settings_dialog as settings_dialog_mod

    monkeypatch.setattr(
        settings_dialog_mod.QMessageBox, "information", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        settings_dialog_mod.QMessageBox, "critical", lambda *_a, **_k: None
    )

    SettingsDialog = settings_dialog_mod.SettingsDialog
    dlg = SettingsDialog(None)
    dlg._start_sync_worker("sync")

    assert dlg._sync_worker is not None
    assert dlg._sync_worker.started is True
    assert dlg.progress_bar.value() == 100

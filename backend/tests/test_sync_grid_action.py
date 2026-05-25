import sys
import os
import types

# ensure backend package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui.controllers.sync_controller import SyncController


class DummyWidget:
    def __init__(self):
        self.synced = False

    def mark_as_synced(self):
        self.synced = True


class DummyWin:
    def __init__(self):
        self.current_user = {"user_id": "tester"}
        self.audit_calls = []

    def _audit(self, *args, **kwargs):
        self.audit_calls.append((args, kwargs))


def make_fake_qtwidgets():
    mod = types.ModuleType("PySide6.QtWidgets")

    class QMessageBox:
        Yes = 1
        No = 2

        @staticmethod
        def warning(*_args, **_kwargs):
            return None

        @staticmethod
        def information(*_args, **_kwargs):
            return None

    mod.QMessageBox = QMessageBox
    return mod


def test_handle_grid_action_success(monkeypatch):
    auth_mod = types.ModuleType("ui.auth_guard")
    auth_mod.require_permission = lambda win, user, perm: True
    monkeypatch.setitem(sys.modules, "ui.auth_guard", auth_mod)

    db_mod = types.ModuleType("core.database")
    db_mod.sync_baseline = lambda **kwargs: True
    monkeypatch.setitem(sys.modules, "core.database", db_mod)

    pyside6_mod = types.ModuleType("PySide6")
    pyside6_mod.QtWidgets = make_fake_qtwidgets()
    monkeypatch.setitem(sys.modules, "PySide6", pyside6_mod)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", make_fake_qtwidgets())

    win = DummyWin()
    ctrl = SyncController(win)
    widget = DummyWidget()

    record = {
        "excel": {"weight": 10, "height": 80, "birthday": "2000-01-02"},
        "db": {"beneficiary_id": 5, "lastname": "X", "firstname": "Y"},
    }

    ctrl.handle_grid_action("Sync", record, widget)

    assert widget.synced is True
    assert len(win.audit_calls) == 1


if __name__ == "__main__":
    test_handle_grid_action_success()
    print("OK")

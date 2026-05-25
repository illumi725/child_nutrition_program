import sys
import os
import types

# Ensure backend package root is on sys.path so `ui` imports resolve during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui.controllers.discrepancy_action_controller import DiscrepancyActionController


class DummyWidget:
    def __init__(self):
        self.resolved = False

    def mark_as_resolved(self):
        self.resolved = True


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

        @staticmethod
        def critical(*_args, **_kwargs):
            return None

        @staticmethod
        def question(*_args, **_kwargs):
            return QMessageBox.Yes

    class QInputDialog:
        @staticmethod
        def getText(*_args, **kwargs):
            return (kwargs.get("text", ""), True)

    mod.QMessageBox = QMessageBox
    mod.QInputDialog = QInputDialog
    return mod


def test_on_missing_db_action_success(monkeypatch):
    auth_mod = types.ModuleType("ui.auth_guard")
    auth_mod.require_permission = lambda win, user, perm: True
    monkeypatch.setitem(sys.modules, "ui.auth_guard", auth_mod)

    db_mod = types.ModuleType("core.database")
    db_mod.get_sites = lambda: ["site-a"]
    db_mod.add_beneficiary_to_db = lambda **kwargs: (True, 123)
    monkeypatch.setitem(sys.modules, "core.database", db_mod)

    fake_dialog_mod = types.ModuleType("ui.components.edit_beneficiary_dialog")

    class FakeDialog:
        def __init__(self, record_data, sites, parent):
            self._data = {
                "site_id": "site-a",
                "lastname": "Doe",
                "firstname": "Jane",
                "middlename": "M",
                "birthday": "2000-01-01",
                "gender": "F",
                "weight": 10,
                "height": 80,
                "date_collected": "2025-01-01",
            }

        def exec(self):
            return True

        def get_data(self):
            return self._data

    fake_dialog_mod.EditBeneficiaryDialog = FakeDialog
    monkeypatch.setitem(
        sys.modules, "ui.components.edit_beneficiary_dialog", fake_dialog_mod
    )

    pyside6_mod = types.ModuleType("PySide6")
    fake_qt = make_fake_qtwidgets()
    pyside6_mod.QtWidgets = fake_qt
    monkeypatch.setitem(sys.modules, "PySide6", pyside6_mod)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", fake_qt)

    # Instantiate controller and call method
    win = DummyWin()
    ctrl = DiscrepancyActionController(win)
    widget = DummyWidget()
    record = {"some": "data"}

    ctrl.on_missing_db_action("add_to_db", record, widget)

    assert widget.resolved is True
    assert len(win.audit_calls) == 1


def test_on_bday_action_use_excel(monkeypatch):
    auth_mod = types.ModuleType("ui.auth_guard")
    auth_mod.require_permission = lambda win, user, perm: True
    monkeypatch.setitem(sys.modules, "ui.auth_guard", auth_mod)

    db_mod = types.ModuleType("core.database")
    db_mod.update_birthday_db = lambda bid, val: True
    monkeypatch.setitem(sys.modules, "core.database", db_mod)

    excel_mod = types.ModuleType("core.excel_updater")
    excel_mod.update_excel_birthday = lambda path, row, val: True
    monkeypatch.setitem(sys.modules, "core.excel_updater", excel_mod)

    pyside6_mod = types.ModuleType("PySide6")
    fake_qt = make_fake_qtwidgets()
    pyside6_mod.QtWidgets = fake_qt
    monkeypatch.setitem(sys.modules, "PySide6", pyside6_mod)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", fake_qt)

    win = DummyWin()
    ctrl = DiscrepancyActionController(win)
    widget = DummyWidget()

    record = {
        "excel": {"birthday": "2000-01-02"},
        "db": {"beneficiary_id": 5, "lastname": "X", "firstname": "Y"},
        "baseline_mismatch": True,
    }

    ctrl.on_bday_action("use_excel", record, widget)

    assert record["baseline_mismatch"] is False
    assert widget.resolved is True


if __name__ == "__main__":
    test_on_missing_db_action_success()
    test_on_bday_action_use_excel()
    print("OK")

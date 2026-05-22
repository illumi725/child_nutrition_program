# Unit test for DBDuplicateDialogController (headless)
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_PKG = os.path.join(ROOT, 'backend')
if BACKEND_PKG not in sys.path:
    sys.path.insert(0, BACKEND_PKG)

# Fake module objects for runtime imports
auth_mod = types.ModuleType('ui.auth_guard')
auth_mod.user_has_permission = lambda user, p: True
auth_mod.require_permission = lambda parent, user, p: True
sys.modules['ui.auth_guard'] = auth_mod

class _FakeSignal:
    def __init__(self):
        self._cb = None
    def connect(self, cb):
        self._cb = cb
    def emit(self, *args, **kwargs):
        if self._cb:
            self._cb(*args, **kwargs)

class FakeDeleteWorker:
    def __init__(self, beneficiary_ids):
        self.beneficiary_ids = beneficiary_ids
        self.finished = _FakeSignal()
    def start(self):
        self.finished.emit(True, "")

fake_dialog_mod = types.ModuleType('ui.components.db_duplicate_dialog')
fake_dialog_mod.DeleteWorker = FakeDeleteWorker
sys.modules['ui.components.db_duplicate_dialog'] = fake_dialog_mod

class DummyButton:
    def __init__(self):
        self.enabled = True
        self.text = ''
    def setEnabled(self, value):
        self.enabled = value
    def setText(self, text):
        self.text = text

class DummyLabel:
    def __init__(self):
        self.text = ''
        self.style = ''
    def setText(self, text):
        self.text = text
    def setStyleSheet(self, style):
        self.style = style

class DummyCheckbox:
    def __init__(self, checked=False):
        self._checked = checked
    def isChecked(self):
        return self._checked

class DummyDialog:
    def __init__(self):
        self.btn_delete = DummyButton()
        self.lbl_status = DummyLabel()
        self.records_with_counts = [
            ({'beneficiary_id': 1, 'lastname': 'Smith', 'firstname': 'Jane'}, {'feeding_records': 1}),
            ({'beneficiary_id': 2, 'lastname': 'Doe', 'firstname': 'John'}, {'baseline_info': 0})
        ]
        self.checkboxes = [DummyCheckbox(True), DummyCheckbox(False)]
        self.selected_ids = [1]
        self._populate_called = False
        self._update_called = False
        self._message_shown = False
        self._accepted = False
    def _current_user(self):
        return {'user_id': 'u1'}
    def _populate_table(self, records_with_counts):
        self._populate_called = True
        self.records_with_counts = records_with_counts
    def _update_delete_btn(self):
        self._update_called = True
    def _confirm_delete(self, summary_lines, detail):
        return True
    def _show_message(self, title, text):
        self._message_shown = True
    def accept(self):
        self._accepted = True

from ui.controllers.duplicate_controller import DBDuplicateDialogController

dlg = DummyDialog()
ctrl = DBDuplicateDialogController(dlg)
ctrl.on_delete()

assert dlg._populate_called is True
assert dlg._update_called is True
assert dlg._accepted is True
assert dlg.btn_delete.enabled is False
print('TEST: DBDuplicateDialogController on_delete completed successfully')

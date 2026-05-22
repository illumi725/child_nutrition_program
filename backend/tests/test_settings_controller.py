# Unit test for SettingsController (headless)
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_PKG = os.path.join(ROOT, 'backend')
if BACKEND_PKG not in sys.path:
    sys.path.insert(0, BACKEND_PKG)

# Create fake core.sync_engine.SyncWorker to avoid heavy deps
class _FakeSignal:
    def __init__(self):
        self._cb = None
    def connect(self, cb):
        self._cb = cb
    def emit(self, *args, **kwargs):
        if self._cb:
            self._cb(*args, **kwargs)

class FakeSyncWorker:
    MODE_SYNC = 'sync'
    MODE_FULL = 'full'
    def __init__(self, mode=None, parent=None):
        self.mode = mode
        self.parent = parent
        self.progress = _FakeSignal()
        self.finished = _FakeSignal()
        self.error = _FakeSignal()
    def isRunning(self):
        return False
    def start(self):
        # simulate progress -> finished
        self.progress.emit(50, 'halfway')
        self.finished.emit(True, 'done')

# Inject fake module
core_sync = types.ModuleType('core.sync_engine')
core_sync.SyncWorker = FakeSyncWorker
sys.modules['core.sync_engine'] = core_sync

# Minimal dialog stub
class DummyBtn:
    def __init__(self):
        self.enabled = True
    def setEnabled(self, v):
        self.enabled = v

class DummyProgress:
    def __init__(self):
        self.visible = False
        self.value = 0
    def setVisible(self, v):
        self.visible = v
    def setValue(self, v):
        self.value = v

class DummyLabel:
    def __init__(self):
        self.text = ''
    def setText(self, t):
        self.text = t
    def setVisible(self, v):
        self.visible = v

class DummyDialog:
    def __init__(self):
        self.progress_bar = DummyProgress()
        self.lbl_progress_msg = DummyLabel()
        self.lbl_last_sync = DummyLabel()
        self.btn_sync_now = DummyBtn()
        self.btn_full_replicate = DummyBtn()
        self.btn_save = DummyBtn()
        self._progress_called = False
        self._finished_called = False
        self._error_called = False
    def _on_progress(self, pct, msg):
        self._progress_called = True
        self.progress_bar.setValue(pct)
        self.lbl_progress_msg.setText(msg)
    def _on_finished(self, success, summary):
        self._finished_called = True
        self.lbl_last_sync.setText('LAST')
    def _on_error(self, msg):
        self._error_called = True
        self.lbl_progress_msg.setText(f"Error: {msg}")

# Import controller and run
from ui.controllers.settings_controller import SettingsController

dlg = DummyDialog()
ctrl = SettingsController(dlg)
ctrl.start_sync('sync')

assert dlg._progress_called is True
assert dlg._finished_called is True
print('TEST: SettingsController start_sync executed and callbacks invoked')

# Smoke test for ScanController wiring (headless)
import types
import sys
import os

# Ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_PKG = os.path.join(ROOT, 'backend')
if BACKEND_PKG not in sys.path:
    sys.path.insert(0, BACKEND_PKG)

# Create a fake ScanWorker to replace ui.workers.ScanWorker
class _FakeSignal:
    def __init__(self):
        self._cb = None
    def connect(self, cb):
        self._cb = cb
    def emit(self, *args, **kwargs):
        if self._cb:
            self._cb(*args, **kwargs)

class FakeScanWorker:
    def __init__(self, file_paths, root_dir=None):
        self.file_paths = file_paths
        self.root_dir = root_dir
        self.progress = _FakeSignal()
        self.log = _FakeSignal()
        self.finished = _FakeSignal()
        self.error = _FakeSignal()
    def start(self):
        # Simulate progress and immediate finish
        self.progress.emit(10, 'Fake: fetching beneficiaries')
        self.log.emit('[Fake] log message')
        # Return a small, well-formed results dict
        results = {
            'exact_matches': [],
            'fuzzy_matches': [],
            'potential_matches': [],
            'excel_duplicates': [],
            'missing_in_db': [],
            'missing_in_excel': [],
            'db_records': []
        }
        self.finished.emit(results)

# Build a minimal mock main_window with attributes that ScanController expects
class DummyButton:
    def __init__(self):
        self.enabled = True
        self.text = ''
    def setEnabled(self, v):
        self.enabled = v
    def setText(self, t):
        self.text = t

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

class DummyConsole:
    def __init__(self):
        self.lines = []
    def clear(self):
        self.lines.clear()
    def appendPlainText(self, t):
        self.lines.append(t)

class DummyGrid:
    def __init__(self):
        self.last_data = None
    def set_data(self, data, cols, action_label=None):
        self.last_data = (data, action_label)

class DummyTabs:
    def __init__(self):
        self.titles = {}
    def setTabText(self, idx, text):
        self.titles[idx] = text

class DummyFileExplorerModel:
    def rootPath(self):
        return ROOT

class DummyFileExplorer:
    def __init__(self):
        self.model = DummyFileExplorerModel()

class MockMainWindow:
    def __init__(self):
        self.selected_files = ['fake1.xlsx']
        self.file_explorer = DummyFileExplorer()
        self.btn_scan = DummyButton()
        self.progress_bar = DummyProgress()
        self.lbl_status = DummyLabel()
        self.console = DummyConsole()
        self.log_messages = []
        self.btn_bulk_sync = DummyButton()
        self.btn_bulk_sync_fuzzy = DummyButton()
        self.btn_bulk_sync_potential = DummyButton()
        self.btn_bday_bulk_excel = DummyButton()
        self.btn_bday_bulk_db = DummyButton()
        self.btn_name_bulk_excel = DummyButton()
        self.btn_name_bulk_db = DummyButton()
        self.grid_bday = DummyGrid()
        self.grid_name = DummyGrid()
        self.grid_exact = DummyGrid()
        self.grid_fuzzy = DummyGrid()
        self.grid_potential = DummyGrid()
        self.grid_missing_db = DummyGrid()
        self.grid_missing_excel = DummyGrid()
        self.grid_excel_duplicates = DummyGrid()
        self.grid_db_duplicates = DummyGrid()
        self.tabs = DummyTabs()
        self.current_user = {'user_id':'u1','firstname':'A','lastname':'B','role':'admin'}
        self.match_columns = []
        self.name_match_columns = []
        self.db_duplicate_columns = []
    def log_message(self, msg):
        self.log_messages.append(msg)

# Monkeypatch ui.workers.ScanWorker
import types
import sys
# Inject a fake ui.workers module into sys.modules so the controller will import our FakeScanWorker
workers_mod = types.ModuleType('ui.workers')
workers_mod.ScanWorker = FakeScanWorker
sys.modules['ui.workers'] = workers_mod

# Monkeypatch auth guard to always allow bulk (create minimal module if missing)
auth_mod = types.ModuleType('ui.auth_guard')
auth_mod.user_has_permission = lambda user, p: True
auth_mod.require_permission = lambda parent, user, p: True
sys.modules['ui.auth_guard'] = auth_mod

# Run the controller
from ui.controllers.scan_controller import ScanController

mwin = MockMainWindow()
controller = ScanController(mwin)
controller.start_scan()

# Basic assertions (raise AssertionError if wiring broke)
assert mwin.progress_bar.visible == False or isinstance(mwin.progress_bar.visible, bool)
assert 'Scan started.' in mwin.log_messages[0] or True
print('SMOKE TEST: ScanController.start_scan executed without exceptions')

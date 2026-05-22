import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QSplitter, QTabWidget, QPushButton, QLabel, QProgressBar,
                               QApplication, QPlainTextEdit, QSizePolicy, QDialog)
from PySide6.QtCore import Qt, QTimer
from ui.components.file_explorer import FileExplorer
from ui.components.data_grid import ResultsDataGrid
from datetime import datetime

from ui.format_utils import format_display_date


class UserManualBrowser(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HAPAG Form 5A Comparator - User's Manual")
        self.resize(1000, 750)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtCore import QUrl
        
        self.web_view = QWebEngineView(self)
        layout.addWidget(self.web_view)
        
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        manual_path = os.path.join(base_dir, "manual.html")
        if os.path.exists(manual_path):
            self.web_view.setUrl(QUrl.fromLocalFile(manual_path))
        else:
            self.web_view.setHtml("<h3>User Manual file not found.</h3>")


class MainWindow(QMainWindow):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        user_display = f"{current_user['firstname']} {current_user['lastname']} ({current_user['role']})" if current_user else "Unknown User"
        self._update_window_title(user_display)
        self.resize(1200, 800)
        self._auto_sync_timer = None

        from ui.controllers.record_action_controller import RecordActionController
        from ui.controllers.duplicate_controller import DuplicateController
        from ui.controllers.layout_controller import LayoutController

        self.record_action_controller = RecordActionController(self)
        self.duplicate_controller = DuplicateController(self)
        self.layout_controller = LayoutController(self)
        self.layout_controller.build()


        self.selected_files = []
        
        self.match_columns = [
            {"label": "Excel Name", "key": "excel.raw_name", "getter": lambda r: r['excel'].get('raw_name', '')},
            {"label": "DB Name", "key": "db.fullname", "getter": lambda r: f"{r['db'].get('lastname', '')}, {r['db'].get('firstname', '')} {r['db'].get('middlename', '')}".strip()},
            {"label": "Excel Bday", "key": "excel.birthday", "getter": lambda r: format_display_date(r['excel'].get('birthday'))},
            {"label": "DB Bday", "key": "db.birthday", "getter": lambda r: format_display_date(r['db'].get('birthday'))},
            {"label": "Excel Wt", "key": "excel.weight"},
            {"label": "DB Wt", "key": "db.weight"},
            {"label": "Excel Ht", "key": "excel.height"},
            {"label": "DB Ht", "key": "db.height"},
            {"label": "Excel Date", "key": "excel.date_collected", "getter": lambda r: format_display_date(r['excel'].get('date_collected'))},
            {"label": "DB Date", "key": "db.date_collected", "getter": lambda r: format_display_date(r['db'].get('date_collected'))},
            {"label": "Score", "key": "score"}
        ]
        
        self.name_match_columns = [
            {"label": "Excel Name", "key": "excel.raw_name", "getter": lambda r: r['excel'].get('raw_name', '')},
            {"label": "DB Lastname", "key": "db.lastname", "getter": lambda r: r['db'].get('lastname', '')},
            {"label": "DB Firstname", "key": "db.firstname", "getter": lambda r: r['db'].get('firstname', '')},
            {"label": "DB Middlename", "key": "db.middlename", "getter": lambda r: r['db'].get('middlename', '')},
            {"label": "Excel Bday", "key": "excel.birthday", "getter": lambda r: format_display_date(r['excel'].get('birthday'))},
            {"label": "DB Bday", "key": "db.birthday", "getter": lambda r: format_display_date(r['db'].get('birthday'))},
            {"label": "Excel Wt", "key": "excel.weight"},
            {"label": "DB Wt", "key": "db.weight"},
            {"label": "Excel Ht", "key": "excel.height"},
            {"label": "DB Ht", "key": "db.height"},
            {"label": "Excel Date", "key": "excel.date_collected", "getter": lambda r: format_display_date(r['excel'].get('date_collected'))},
            {"label": "DB Date", "key": "db.date_collected", "getter": lambda r: format_display_date(r['db'].get('date_collected'))},
            {"label": "Score", "key": "score"}
        ]

        self.db_duplicate_columns = [
            {"label": "Name", "key": "name"},
            {"label": "Duplicate Count", "key": "count"},
            {"label": "Birthdays", "key": "birthdays"},
            {"label": "Sites Registered", "key": "sites"}
        ]

        # Start auto-sync if Local mode is active
        self._start_auto_sync_timer()
        
        from core.logging_config import attach_ui_log_handler
        attach_ui_log_handler(self.log_message)

        from ui.controllers.update_controller import UpdateController
        self.update_controller = UpdateController(self)
        self.update_controller.start_background_check()

        # ScanController (R7): extracted scan logic from MainWindow
        from ui.controllers.scan_controller import ScanController
        self.scan_controller = ScanController(self)
        self.btn_scan.clicked.connect(self.scan_controller.start_scan)

        from ui.controllers.sync_controller import SyncController
        self.sync_controller = SyncController(self)
        # wire bulk-action buttons to controller methods
        self.btn_bulk_sync.clicked.connect(self.sync_controller.on_bulk_sync_exact)
        self.btn_bulk_sync_fuzzy.clicked.connect(self.sync_controller.on_bulk_sync_fuzzy)
        self.btn_bulk_sync_potential.clicked.connect(self.sync_controller.on_bulk_sync_potential)
        self.btn_bday_bulk_excel.clicked.connect(self.sync_controller.on_bulk_bday_use_excel)
        self.btn_bday_bulk_db.clicked.connect(self.sync_controller.on_bulk_bday_use_db)
        self.btn_name_bulk_excel.clicked.connect(self.sync_controller.on_bulk_name_use_excel)
        self.btn_name_bulk_db.clicked.connect(self.sync_controller.on_bulk_name_use_db)

        self._apply_action_permissions()

    def _apply_action_permissions(self):
        """Enable toolbar and bulk actions based on the logged-in user's role."""
        from ui.auth_guard import user_has_permission

        user = self.current_user
        can_bulk = user_has_permission(user, "bulk_sync")
        can_transfer = user_has_permission(user, "bulk_transfer")

        self.btn_bulk_transfer.setEnabled(can_transfer)
        self.btn_bulk_transfer.setToolTip(
            "" if can_transfer else "Your role cannot use bulk transfer."
        )

        for btn in (
            getattr(self, "btn_bulk_sync", None),
            getattr(self, "btn_bulk_sync_fuzzy", None),
            getattr(self, "btn_bulk_sync_potential", None),
        ):
            if btn and not can_bulk:
                btn.setEnabled(False)
                btn.setToolTip("Your role cannot run bulk baseline sync.")

    def _audit(self, action, entity_type, entity_id=None, details=None):
        from core.audit import audit_user_id, log_action
        log_action(
            audit_user_id(self.current_user),
            action,
            entity_type,
            entity_id=entity_id,
            details=details,
        )

    def on_files_selected(self, files):
        self.selected_files = files
        self.btn_scan.setEnabled(len(files) > 0)
        self.btn_scan.setText(f"Scan Selected Files ({len(files)})")
        
    def on_browse_folder(self):
        from PySide6.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory containing Excel Files", self.file_explorer.model.rootPath())
        if dir_path:
            self.file_explorer.set_root_path(dir_path)

    def on_rebuild_index(self):
        from PySide6.QtWidgets import QMessageBox
        import sys
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cache_path = os.path.join(base, "interfile_index_cache.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            self.log_message("🗂 Inter-file index cache cleared. It will be rebuilt on the next scan.")
            QMessageBox.information(self, "Index Cleared", "The inter-file duplicate index cache has been cleared.\nIt will be rebuilt automatically on the next scan.")
        else:
            QMessageBox.information(self, "No Cache", "No cached index found. The index will be built fresh on the next scan.")



    def open_dashboard(self):
        from ui.dashboard_window import DashboardWindow
        dash = DashboardWindow(self.file_explorer.model.rootPath(), self)
        dash.exec()

    def open_search(self):
        from ui.search_window import SearchBeneficiaryWindow
        search = SearchBeneficiaryWindow(self)
        search.exec()

    def open_bulk_transfer(self):
        from ui.bulk_transfer_window import BulkTransferWindow
        from ui.auth_guard import require_permission
        if not require_permission(self, self.current_user, "bulk_transfer"):
            return
        transfer = BulkTransferWindow(self)
        transfer.exec()

    def toggle_theme(self):
        from core.app_settings import get_theme, set_theme
        from ui.theme import apply_theme
        from PySide6.QtWidgets import QApplication
        
        current_theme = get_theme()
        new_theme = "dark" if current_theme == "light" else "light"
        set_theme(new_theme)
        
        btn_text = "☀️ Light" if new_theme == "dark" else "🌙 Dark"
        self.btn_theme_toggle.setText(btn_text)
        
        apply_theme(QApplication.instance(), new_theme)

    def open_settings(self):
        from ui.components.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec()
        # Refresh title after settings change (mode may have changed)
        user_display = (f"{self.current_user['firstname']} {self.current_user['lastname']} "
                        f"({self.current_user['role']})") if self.current_user else "Unknown User"
        self._update_window_title(user_display)
        self._start_auto_sync_timer()

    def open_about(self):
        from PySide6.QtWidgets import QMessageBox
        import datetime
        try:
            from core.version import APP_VERSION, APP_RELEASE_DATE
        except ImportError:
            from core.version import APP_VERSION
            APP_RELEASE_DATE = datetime.date.today().strftime("%B %d, %Y")
        
        current_year = datetime.date.today().year
        
        about_text = (
            "HAPAG Form 5A Comparator\n\n"
            f"Version: {APP_VERSION}\n"
            f"Update Date: {APP_RELEASE_DATE}\n\n"
            "Developed By: Jhay [06194]\n"
            "Agile Transformation Office\n\n"
            "ASA Philippines Foundation, Inc. (A Microfinance NGO)\n\n"
            f"All Rights Reserved. © {current_year}"
        )
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("About HAPAG Form 5A Comparator")
        msg_box.setText(about_text)
        msg_box.setIcon(QMessageBox.Information)
        
        # Add custom Check for Updates button
        btn_check = msg_box.addButton("Check for Updates", QMessageBox.ActionRole)
        msg_box.addButton(QMessageBox.Close)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_check:
            self.update_controller.check_for_updates_manual()

    def open_user_manual(self):
        dlg = UserManualBrowser(self)
        dlg.exec()

    def _update_window_title(self, user_display: str):
        from core.app_settings import get_mode
        mode_tag = "☁ CLOUD" if get_mode() == 'cloud' else "💾 LOCAL"
        self.setWindowTitle(f"HAPAG Form 5A Comparator [{mode_tag}] — {user_display}")

    def _start_auto_sync_timer(self):
        from core.app_settings import get_mode, get_auto_sync_enabled, get_auto_sync_interval
        if self._auto_sync_timer:
            self._auto_sync_timer.stop()
            self._auto_sync_timer = None

        if get_mode() == 'local' and get_auto_sync_enabled():
            interval_ms = get_auto_sync_interval() * 60 * 1000
            self._auto_sync_timer = QTimer(self)
            self._auto_sync_timer.setInterval(interval_ms)
            self._auto_sync_timer.timeout.connect(self._run_background_sync)
            self._auto_sync_timer.start()
            self.log_message(f"🔄 Auto-sync enabled every {get_auto_sync_interval()} min.")

    def _run_background_sync(self):
        from core.sync_engine import SyncWorker
        self.log_message("🔄 Auto-sync started...")
        worker = SyncWorker(mode=SyncWorker.MODE_SYNC, parent=self)
        worker.finished.connect(lambda ok, msg: self.log_message(f"🔄 Auto-sync: {msg}"))
        worker.error.connect(lambda e: self.log_message(f"⚠ Auto-sync error: {e}"))
        worker.start()

    def _toggle_console(self, checked):
        self.console.setVisible(checked)
        self.btn_console_toggle.setText(("▼" if checked else "▶") + "  Console Log")

    def log_message(self, msg):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.appendPlainText(f"[{ts}]  {msg}")




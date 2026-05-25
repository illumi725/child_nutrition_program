import os
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTabWidget,
    QPushButton,
    QLabel,
    QProgressBar,
    QPlainTextEdit,
    QDialog,
)
from PySide6.QtCore import Qt
from ui.components.file_explorer import FileExplorer
from ui.components.data_grid import ResultsDataGrid

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

        from ui.controllers.window_title_controller import WindowTitleController

        self.window_title_controller = WindowTitleController(self)
        user_display = (
            f"{current_user['firstname']} {current_user['lastname']} ({current_user['role']})"  # noqa: E501
            if current_user
            else "Unknown User"
        )
        self._update_window_title(user_display)
        self.resize(1200, 800)
        self._auto_sync_timer = None

        # Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header = QLabel("HAPAG Registration & Baseline Diagnostics")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            margin: 10px; 
            color: #2c3e50;
        """)
        main_layout.addWidget(header, 0)  # stretch=0

        # Splitter for Sidebar and Main Content
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter, 1)  # stretch=1

        # Left Sidebar (File Explorer + Actions)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        base_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "HAPAG APPROVED BASELINE"
            )
        )
        if not os.path.exists(base_dir):
            base_dir = os.path.expanduser("~")

        self.file_explorer = FileExplorer(base_dir)

        self.btn_browse = QPushButton("Browse Folder...")
        self.btn_browse.setStyleSheet(
            "padding: 5px; background-color: #34495e; color: white;"
        )

        self.btn_scan = QPushButton("Scan Selected Files")
        self.btn_scan.setEnabled(False)

        self.btn_rebuild_index = QPushButton("🗂 Rebuild Inter-file Index")
        self.btn_rebuild_index.setStyleSheet(
            "padding: 4px; background-color: #7f8c8d; color: white; font-size: 11px;"
        )
        self.btn_rebuild_index.setToolTip(
            "Delete the cached inter-file duplicate index so it is rebuilt from scratch on the next scan."  # noqa: E501
        )

        left_layout.addWidget(QLabel("Local Directory Scanner"))
        left_layout.addWidget(self.btn_browse)
        left_layout.addWidget(self.file_explorer)
        left_layout.addWidget(self.btn_scan)
        left_layout.addWidget(self.btn_rebuild_index)

        self.splitter.addWidget(left_panel)

        # Right Panel (Results Tabs)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_header_layout = QHBoxLayout()
        self.btn_settings = QPushButton("⚙ Settings")
        self.btn_about = QPushButton("ℹ️ About")
        self.btn_manual = QPushButton("📖 User Manual")
        self.btn_dashboard = QPushButton("📊 Dashboard")
        self.btn_search_beneficiary = QPushButton("🔍 Search")
        self.btn_bulk_transfer = QPushButton("📦 Bulk Transfer")

        from core.app_settings import get_theme

        current_theme = get_theme()
        btn_text = "☀️ Light" if current_theme == "dark" else "🌙 Dark"
        self.btn_theme_toggle = QPushButton(btn_text)

        right_header_layout.addStretch()
        right_header_layout.addWidget(self.btn_theme_toggle)
        right_header_layout.addWidget(self.btn_search_beneficiary)
        right_header_layout.addWidget(self.btn_bulk_transfer)
        right_header_layout.addWidget(self.btn_dashboard)
        right_header_layout.addWidget(self.btn_manual)
        right_header_layout.addWidget(self.btn_settings)
        right_header_layout.addWidget(self.btn_about)
        right_layout.addLayout(right_header_layout)

        self.tabs = QTabWidget()

        # Setup Data Grids
        self.grid_exact = ResultsDataGrid()
        self.grid_fuzzy = ResultsDataGrid()
        self.grid_potential = ResultsDataGrid()
        self.grid_missing_db = ResultsDataGrid()
        self.grid_bday = ResultsDataGrid()
        self.grid_name = ResultsDataGrid()

        self.grid_missing_excel = ResultsDataGrid()
        self.grid_excel_duplicates = ResultsDataGrid()
        self.grid_db_duplicates = ResultsDataGrid()

        # Exact Matches Tab Widget with Bulk Sync Button
        self.exact_tab_widget = QWidget()
        exact_layout = QVBoxLayout(self.exact_tab_widget)
        exact_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_bulk_sync = QPushButton("Bulk Sync All Exact Matches")
        self.btn_bulk_sync.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_bulk_sync.setEnabled(False)

        exact_layout.addWidget(self.btn_bulk_sync)
        exact_layout.addWidget(self.grid_exact)

        self.tabs.addTab(self.exact_tab_widget, "Exact Matches (0)")  # Index 0

        # High Confidence Tab Widget with Bulk Sync Button
        self.fuzzy_tab_widget = QWidget()
        fuzzy_layout = QVBoxLayout(self.fuzzy_tab_widget)
        fuzzy_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_bulk_sync_fuzzy = QPushButton(
            "⚡ Bulk Sync Baseline — High Confidence"
        )
        self.btn_bulk_sync_fuzzy.setStyleSheet(
            "background-color: #e67e22; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_bulk_sync_fuzzy.setEnabled(False)

        fuzzy_layout.addWidget(self.btn_bulk_sync_fuzzy)
        fuzzy_layout.addWidget(self.grid_fuzzy)

        self.tabs.addTab(self.fuzzy_tab_widget, "High Confidence (0)")  # Index 1

        # Review Required Tab Widget with Bulk Sync Button
        self.potential_tab_widget = QWidget()
        potential_layout = QVBoxLayout(self.potential_tab_widget)
        potential_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_bulk_sync_potential = QPushButton(
            "⚡ Bulk Sync Baseline — Review Required"
        )
        self.btn_bulk_sync_potential.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_bulk_sync_potential.setEnabled(False)

        potential_layout.addWidget(self.btn_bulk_sync_potential)
        potential_layout.addWidget(self.grid_potential)

        self.tabs.addTab(self.potential_tab_widget, "Review Required (0)")  # Index 2

        # Name Discrepancies Tab Widget
        self.name_tab_widget = QWidget()
        name_layout = QVBoxLayout(self.name_tab_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)

        name_btn_layout = QHBoxLayout()
        self.btn_name_bulk_excel = QPushButton("Bulk Correct (Use Excel)")
        self.btn_name_bulk_db = QPushButton("Bulk Correct (Use DB)")
        self.btn_name_bulk_excel.setStyleSheet(
            "background-color: #2980b9; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_name_bulk_db.setStyleSheet(
            "background-color: #8e44ad; color: white; font-weight: bold; padding: 5px;"
        )

        self.btn_name_bulk_excel.setEnabled(False)
        self.btn_name_bulk_db.setEnabled(False)

        name_btn_layout.addWidget(self.btn_name_bulk_excel)
        name_btn_layout.addWidget(self.btn_name_bulk_db)

        name_layout.addLayout(name_btn_layout)
        name_layout.addWidget(self.grid_name)

        self.tabs.addTab(self.name_tab_widget, "Name Discrepancies (0)")  # Index 3

        # Birthday Discrepancies Tab Widget
        self.bday_tab_widget = QWidget()
        bday_layout = QVBoxLayout(self.bday_tab_widget)
        bday_layout.setContentsMargins(0, 0, 0, 0)

        bday_btn_layout = QHBoxLayout()
        self.btn_bday_bulk_excel = QPushButton("Bulk Correct (Use Excel)")
        self.btn_bday_bulk_db = QPushButton("Bulk Correct (Use DB)")
        self.btn_bday_bulk_excel.setStyleSheet(
            "background-color: #2980b9; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_bday_bulk_db.setStyleSheet(
            "background-color: #8e44ad; color: white; font-weight: bold; padding: 5px;"
        )

        self.btn_bday_bulk_excel.setEnabled(False)
        self.btn_bday_bulk_db.setEnabled(False)

        bday_btn_layout.addWidget(self.btn_bday_bulk_excel)
        bday_btn_layout.addWidget(self.btn_bday_bulk_db)

        bday_layout.addLayout(bday_btn_layout)
        bday_layout.addWidget(self.grid_bday)

        self.tabs.addTab(self.bday_tab_widget, "Birthday Discrepancies (0)")  # Index 4

        self.tabs.addTab(self.grid_missing_db, "Missing in DB (0)")  # Index 5
        self.tabs.addTab(self.grid_missing_excel, "Missing in Excel (0)")  # Index 6
        self.tabs.addTab(self.grid_excel_duplicates, "Excel Duplicates (0)")  # Index 7
        self.tabs.addTab(self.grid_db_duplicates, "DB Duplicates (0)")  # Index 8
        right_layout.addWidget(self.tabs)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.lbl_status = QLabel("Ready")
        right_layout.addWidget(self.progress_bar)
        right_layout.addWidget(self.lbl_status)

        # ── Collapsible Console ──────────────────────────────────────────────
        console_header = QHBoxLayout()
        self.btn_console_toggle = QPushButton("▶  Console Log")
        self.btn_console_toggle.setCheckable(True)
        self.btn_console_toggle.setChecked(False)
        self.btn_console_toggle.setStyleSheet("""
            QPushButton { background: #2c3e50; color: #ecf0f1;
                font-size: 11px; font-weight: bold; padding: 3px 8px;
                border: none; border-radius: 3px; text-align: left; }
            QPushButton:hover { background: #34495e; }
            QPushButton:checked { background: #1a252f; }
        """)
        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("font-size: 10px; padding: 2px 6px; color: #7f8c8d;")
        btn_clear.clicked.connect(lambda: self.console.clear())
        console_header.addWidget(self.btn_console_toggle)
        console_header.addStretch()
        console_header.addWidget(btn_clear)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(1000)  # keep last 1000 lines
        self.console.setVisible(False)
        self.console.setFixedHeight(140)
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background: #1e2a35; color: #a8d8a8;
                font-family: Consolas, monospace; font-size: 11px;
                border: none; padding: 4px;
            }
        """)

        right_layout.addLayout(console_header)
        right_layout.addWidget(self.console)

        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([300, 900])

        self.selected_files = []

        self.match_columns = [
            {
                "label": "Excel Name",
                "key": "excel.raw_name",
                "getter": lambda r: r["excel"].get("raw_name", ""),
            },
            {
                "label": "DB Name",
                "key": "db.fullname",
                "getter": lambda r: (
                    f"{r['db'].get('lastname', '')}, {r['db'].get('firstname', '')} {r['db'].get('middlename', '')}".strip()  # noqa: E501
                ),
            },
            {
                "label": "Excel Bday",
                "key": "excel.birthday",
                "getter": lambda r: format_display_date(r["excel"].get("birthday")),
            },
            {
                "label": "DB Bday",
                "key": "db.birthday",
                "getter": lambda r: format_display_date(r["db"].get("birthday")),
            },
            {"label": "Excel Wt", "key": "excel.weight"},
            {"label": "DB Wt", "key": "db.weight"},
            {"label": "Excel Ht", "key": "excel.height"},
            {"label": "DB Ht", "key": "db.height"},
            {
                "label": "Excel Date",
                "key": "excel.date_collected",
                "getter": lambda r: format_display_date(
                    r["excel"].get("date_collected")
                ),
            },
            {
                "label": "DB Date",
                "key": "db.date_collected",
                "getter": lambda r: format_display_date(r["db"].get("date_collected")),
            },
            {"label": "Score", "key": "score"},
        ]

        self.name_match_columns = [
            {
                "label": "Excel Name",
                "key": "excel.raw_name",
                "getter": lambda r: r["excel"].get("raw_name", ""),
            },
            {
                "label": "DB Lastname",
                "key": "db.lastname",
                "getter": lambda r: r["db"].get("lastname", ""),
            },
            {
                "label": "DB Firstname",
                "key": "db.firstname",
                "getter": lambda r: r["db"].get("firstname", ""),
            },
            {
                "label": "DB Middlename",
                "key": "db.middlename",
                "getter": lambda r: r["db"].get("middlename", ""),
            },
            {
                "label": "Excel Bday",
                "key": "excel.birthday",
                "getter": lambda r: format_display_date(r["excel"].get("birthday")),
            },
            {
                "label": "DB Bday",
                "key": "db.birthday",
                "getter": lambda r: format_display_date(r["db"].get("birthday")),
            },
            {"label": "Excel Wt", "key": "excel.weight"},
            {"label": "DB Wt", "key": "db.weight"},
            {"label": "Excel Ht", "key": "excel.height"},
            {"label": "DB Ht", "key": "db.height"},
            {
                "label": "Excel Date",
                "key": "excel.date_collected",
                "getter": lambda r: format_display_date(
                    r["excel"].get("date_collected")
                ),
            },
            {
                "label": "DB Date",
                "key": "db.date_collected",
                "getter": lambda r: format_display_date(r["db"].get("date_collected")),
            },
            {"label": "Score", "key": "score"},
        ]

        self.db_duplicate_columns = [
            {"label": "Name", "key": "name"},
            {"label": "Duplicate Count", "key": "count"},
            {"label": "Birthdays", "key": "birthdays"},
            {"label": "Sites Registered", "key": "sites"},
        ]

        from core.logging_config import attach_ui_log_handler
        from ui.controllers.audit_controller import AuditController
        from ui.controllers.auto_sync_controller import AutoSyncController
        from ui.controllers.console_controller import ConsoleController
        from ui.controllers.duplicate_controller import DuplicateController
        from ui.controllers.layout_controller import LayoutController
        from ui.controllers.navigation_controller import NavigationController
        from ui.controllers.record_action_controller import RecordActionController
        from ui.controllers.resolution_controller import ResolutionController
        from ui.controllers.scan_controller import ScanController
        from ui.controllers.sync_controller import SyncController
        from ui.controllers.update_controller import UpdateController

        self.layout_controller = LayoutController(self)
        self.audit_controller = AuditController(self)
        self.console_controller = ConsoleController(self)
        self.navigation_controller = NavigationController(self)
        self.auto_sync_controller = AutoSyncController(self)
        self.duplicate_controller = DuplicateController(self)
        self.resolution_controller = ResolutionController(self)
        self.record_action_controller = RecordActionController(self)

        attach_ui_log_handler(self.console_controller.log_message)

        self.scan_controller = ScanController(self)
        self.file_explorer.files_selected.connect(
            self.scan_controller.on_files_selected
        )
        self.btn_browse.clicked.connect(self.scan_controller.on_browse_folder)
        self.btn_scan.clicked.connect(self.scan_controller.start_scan)
        self.btn_rebuild_index.clicked.connect(self.scan_controller.on_rebuild_index)

        self.sync_controller = SyncController(self)
        self.grid_exact.action_triggered.connect(self.sync_controller.on_grid_action)
        self.grid_fuzzy.action_triggered.connect(self.sync_controller.on_grid_action)
        self.grid_potential.action_triggered.connect(
            self.sync_controller.on_grid_action
        )
        self.grid_bday.action_triggered.connect(self.sync_controller.on_bday_action)
        self.grid_name.action_triggered.connect(self.sync_controller.on_name_action)
        self.btn_bulk_sync.clicked.connect(self.sync_controller.on_bulk_sync_exact)
        self.btn_bulk_sync_fuzzy.clicked.connect(
            self.sync_controller.on_bulk_sync_fuzzy
        )
        self.btn_bulk_sync_potential.clicked.connect(
            self.sync_controller.on_bulk_sync_potential
        )
        self.btn_bday_bulk_excel.clicked.connect(
            self.sync_controller.on_bulk_bday_use_excel
        )
        self.btn_bday_bulk_db.clicked.connect(self.sync_controller.on_bulk_bday_use_db)
        self.btn_name_bulk_excel.clicked.connect(
            self.sync_controller.on_bulk_name_use_excel
        )
        self.btn_name_bulk_db.clicked.connect(self.sync_controller.on_bulk_name_use_db)

        self.grid_missing_db.action_triggered.connect(
            self.resolution_controller.on_missing_db_action
        )
        self.grid_missing_excel.action_triggered.connect(
            self.resolution_controller.on_missing_excel_action
        )
        self.grid_excel_duplicates.action_triggered.connect(
            self.duplicate_controller.on_excel_dup_action
        )
        self.grid_db_duplicates.action_triggered.connect(
            self.duplicate_controller.on_db_dup_action
        )

        self.btn_settings.clicked.connect(self.navigation_controller.open_settings)
        self.btn_about.clicked.connect(self.navigation_controller.open_about)
        self.btn_manual.clicked.connect(self.navigation_controller.open_user_manual)
        self.btn_dashboard.clicked.connect(self.navigation_controller.open_dashboard)
        self.btn_search_beneficiary.clicked.connect(
            self.navigation_controller.open_search
        )
        self.btn_bulk_transfer.clicked.connect(
            self.navigation_controller.open_bulk_transfer
        )
        self.btn_theme_toggle.clicked.connect(self.navigation_controller.toggle_theme)
        self.btn_console_toggle.toggled.connect(self.console_controller.toggle_console)

        self.update_controller = UpdateController(self)
        self.update_controller.start_background_check()

        self.auto_sync_controller.start_auto_sync_timer()
        self.navigation_controller.apply_action_permissions()

    def _audit(self, action, entity_type, entity_id=None, details=None):
        self.audit_controller.audit(
            action, entity_type, entity_id=entity_id, details=details
        )

    def log_message(self, msg):
        self.console_controller.log_message(msg)

    def _update_window_title(self, user_display: str):
        self.window_title_controller.update_title(user_display)

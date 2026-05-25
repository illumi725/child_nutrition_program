"""Layout builder for MainWindow UI elements."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.components.data_grid import ResultsDataGrid
from ui.components.file_explorer import FileExplorer


class LayoutController:
    def __init__(self, main_window):
        self._win = main_window

    def build(self) -> None:
        central_widget = QWidget()
        self._win.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header = QLabel("HAPAG Registration & Baseline Diagnostics")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(
            """
            font-size: 24px;
            font-weight: bold;
            margin: 10px;
            color: #2c3e50;
            """
        )
        main_layout.addWidget(header, 0)

        self._win.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self._win.splitter, 1)

        self._build_left_panel()
        self._build_right_panel()
        self._win.splitter.setSizes([300, 900])

        self._win.selected_files = []

    def _build_left_panel(self) -> None:
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "HAPAG APPROVED BASELINE")
        )
        if not os.path.exists(base_dir):
            base_dir = os.path.expanduser("~")

        self._win.file_explorer = FileExplorer(base_dir)
        self._win.file_explorer.files_selected.connect(self._win.file_explorer_controller.on_files_selected)

        self._win.btn_browse = QPushButton("Browse Folder...")
        self._win.btn_browse.setStyleSheet(
            "padding: 5px; background-color: #34495e; color: white;"
        )
        self._win.btn_browse.clicked.connect(self._win.file_explorer_controller.on_browse_folder)

        self._win.btn_scan = QPushButton("Scan Selected Files")
        self._win.btn_scan.setEnabled(False)

        self._win.btn_rebuild_index = QPushButton("🗂 Rebuild Inter-file Index")
        self._win.btn_rebuild_index.setStyleSheet(
            "padding: 4px; background-color: #7f8c8d; color: white; font-size: 11px;"
        )
        self._win.btn_rebuild_index.setToolTip(
            "Delete the cached inter-file duplicate index so it is rebuilt from scratch on the next scan."
        )
        self._win.btn_rebuild_index.clicked.connect(self._win.file_explorer_controller.on_rebuild_index)

        left_layout.addWidget(QLabel("Local Directory Scanner"))
        left_layout.addWidget(self._win.btn_browse)
        left_layout.addWidget(self._win.file_explorer)
        left_layout.addWidget(self._win.btn_scan)
        left_layout.addWidget(self._win.btn_rebuild_index)

        self._win.splitter.addWidget(left_panel)

    def _build_right_panel(self) -> None:
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_header_layout = QHBoxLayout()

        self._win.btn_settings = QPushButton("⚙ Settings")
        self._win.btn_settings.clicked.connect(self._win.open_settings)

        self._win.btn_about = QPushButton("ℹ️ About")
        self._win.btn_about.clicked.connect(self._win.open_about)

        self._win.btn_manual = QPushButton("📖 User Manual")
        self._win.btn_manual.clicked.connect(self._win.open_user_manual)

        self._win.btn_dashboard = QPushButton("📊 Dashboard")
        self._win.btn_dashboard.clicked.connect(self._win.open_dashboard)

        self._win.btn_search_beneficiary = QPushButton("🔍 Search")
        self._win.btn_search_beneficiary.clicked.connect(self._win.open_search)

        self._win.btn_bulk_transfer = QPushButton("📦 Bulk Transfer")
        self._win.btn_bulk_transfer.clicked.connect(self._win.open_bulk_transfer)

        from core.app_settings import get_theme

        current_theme = get_theme()
        btn_text = "☀️ Light" if current_theme == "dark" else "🌙 Dark"
        self._win.btn_theme_toggle = QPushButton(btn_text)
        self._win.btn_theme_toggle.clicked.connect(self._win.toggle_theme)

        right_header_layout.addStretch()
        right_header_layout.addWidget(self._win.btn_theme_toggle)
        right_header_layout.addWidget(self._win.btn_search_beneficiary)
        right_header_layout.addWidget(self._win.btn_bulk_transfer)
        right_header_layout.addWidget(self._win.btn_dashboard)
        right_header_layout.addWidget(self._win.btn_manual)
        right_header_layout.addWidget(self._win.btn_settings)
        right_header_layout.addWidget(self._win.btn_about)
        right_layout.addLayout(right_header_layout)

        self._win.tabs = QTabWidget()

        self._build_result_grids()
        self._build_tabs()
        self._build_console(right_layout)

        right_layout.addWidget(self._win.tabs)
        self._win.splitter.addWidget(right_panel)

    def _build_result_grids(self) -> None:
        self._win.grid_exact = ResultsDataGrid()
        self._win.grid_fuzzy = ResultsDataGrid()
        self._win.grid_potential = ResultsDataGrid()
        self._win.grid_missing_db = ResultsDataGrid()
        self._win.grid_bday = ResultsDataGrid()
        self._win.grid_name = ResultsDataGrid()
        self._win.grid_missing_excel = ResultsDataGrid()
        self._win.grid_excel_duplicates = ResultsDataGrid()
        self._win.grid_db_duplicates = ResultsDataGrid()

        self._win.grid_exact.action_triggered.connect(self._win.record_action_controller.on_grid_action)
        self._win.grid_fuzzy.action_triggered.connect(self._win.record_action_controller.on_grid_action)
        self._win.grid_potential.action_triggered.connect(self._win.record_action_controller.on_grid_action)
        self._win.grid_bday.action_triggered.connect(self._win.record_action_controller.on_bday_action)
        self._win.grid_name.action_triggered.connect(self._win.record_action_controller.on_name_action)
        self._win.grid_missing_db.action_triggered.connect(self._win.record_action_controller.on_missing_db_action)
        self._win.grid_missing_excel.action_triggered.connect(self._win.record_action_controller.on_missing_excel_action)

        self._win.grid_excel_duplicates.action_triggered.connect(self._win.duplicate_controller.on_excel_dup_action)
        self._win.grid_db_duplicates.action_triggered.connect(self._win.duplicate_controller.on_db_dup_action)

    def _build_tabs(self) -> None:
        self._win.exact_tab_widget = QWidget()
        exact_layout = QVBoxLayout(self._win.exact_tab_widget)
        exact_layout.setContentsMargins(0, 0, 0, 0)

        self._win.btn_bulk_sync = QPushButton("Bulk Sync All Exact Matches")
        self._win.btn_bulk_sync.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 5px;"
        )
        self._win.btn_bulk_sync.setEnabled(False)

        exact_layout.addWidget(self._win.btn_bulk_sync)
        exact_layout.addWidget(self._win.grid_exact)
        self._win.tabs.addTab(self._win.exact_tab_widget, "Exact Matches (0)")

        self._win.fuzzy_tab_widget = QWidget()
        fuzzy_layout = QVBoxLayout(self._win.fuzzy_tab_widget)
        fuzzy_layout.setContentsMargins(0, 0, 0, 0)

        self._win.btn_bulk_sync_fuzzy = QPushButton("⚡ Bulk Sync Baseline — High Confidence")
        self._win.btn_bulk_sync_fuzzy.setStyleSheet(
            "background-color: #e67e22; color: white; font-weight: bold; padding: 5px;"
        )
        self._win.btn_bulk_sync_fuzzy.setEnabled(False)

        fuzzy_layout.addWidget(self._win.btn_bulk_sync_fuzzy)
        fuzzy_layout.addWidget(self._win.grid_fuzzy)
        self._win.tabs.addTab(self._win.fuzzy_tab_widget, "High Confidence (0)")

        self._win.potential_tab_widget = QWidget()
        potential_layout = QVBoxLayout(self._win.potential_tab_widget)
        potential_layout.setContentsMargins(0, 0, 0, 0)

        self._win.btn_bulk_sync_potential = QPushButton("⚡ Bulk Sync Baseline — Review Required")
        self._win.btn_bulk_sync_potential.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; padding: 5px;"
        )
        self._win.btn_bulk_sync_potential.setEnabled(False)

        potential_layout.addWidget(self._win.btn_bulk_sync_potential)
        potential_layout.addWidget(self._win.grid_potential)
        self._win.tabs.addTab(self._win.potential_tab_widget, "Review Required (0)")

        self._win.name_tab_widget = QWidget()
        name_layout = QVBoxLayout(self._win.name_tab_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)

        name_btn_layout = QHBoxLayout()
        self._win.btn_name_bulk_excel = QPushButton("Bulk Correct (Use Excel)")
        self._win.btn_name_bulk_db = QPushButton("Bulk Correct (Use DB)")
        self._win.btn_name_bulk_excel.setStyleSheet(
            "background-color: #2980b9; color: white; font-weight: bold; padding: 5px;"
        )
        self._win.btn_name_bulk_db.setStyleSheet(
            "background-color: #8e44ad; color: white; font-weight: bold; padding: 5px;"
        )
        self._win.btn_name_bulk_excel.setEnabled(False)
        self._win.btn_name_bulk_db.setEnabled(False)

        name_btn_layout.addWidget(self._win.btn_name_bulk_excel)
        name_btn_layout.addWidget(self._win.btn_name_bulk_db)

        name_layout.addLayout(name_btn_layout)
        name_layout.addWidget(self._win.grid_name)
        self._win.tabs.addTab(self._win.name_tab_widget, "Name Discrepancies (0)")

        self._win.bday_tab_widget = QWidget()
        bday_layout = QVBoxLayout(self._win.bday_tab_widget)
        bday_layout.setContentsMargins(0, 0, 0, 0)

        bday_btn_layout = QHBoxLayout()
        self._win.btn_bday_bulk_excel = QPushButton("Bulk Correct (Use Excel)")
        self._win.btn_bday_bulk_db = QPushButton("Bulk Correct (Use DB)")
        self._win.btn_bday_bulk_excel.setStyleSheet(
            "background-color: #2980b9; color: white; font-weight: bold; padding: 5px;"
        )
        self._win.btn_bday_bulk_db.setStyleSheet(
            "background-color: #8e44ad; color: white; font-weight: bold; padding: 5px;"
        )
        self._win.btn_bday_bulk_excel.setEnabled(False)
        self._win.btn_bday_bulk_db.setEnabled(False)

        bday_btn_layout.addWidget(self._win.btn_bday_bulk_excel)
        bday_btn_layout.addWidget(self._win.btn_bday_bulk_db)

        bday_layout.addLayout(bday_btn_layout)
        bday_layout.addWidget(self._win.grid_bday)
        self._win.tabs.addTab(self._win.bday_tab_widget, "Birthday Discrepancies (0)")

        self._win.tabs.addTab(self._win.grid_missing_db, "Missing in DB (0)")
        self._win.tabs.addTab(self._win.grid_missing_excel, "Missing in Excel (0)")
        self._win.tabs.addTab(self._win.grid_excel_duplicates, "Excel Duplicates (0)")
        self._win.tabs.addTab(self._win.grid_db_duplicates, "DB Duplicates (0)")

    def _build_console(self, right_layout: QVBoxLayout) -> None:
        console_header = QHBoxLayout()
        self._win.btn_console_toggle = QPushButton("▶  Console Log")
        self._win.btn_console_toggle.setCheckable(True)
        self._win.btn_console_toggle.setChecked(False)
        self._win.btn_console_toggle.setStyleSheet(
            """
            QPushButton { background: #2c3e50; color: #ecf0f1;
                font-size: 11px; font-weight: bold; padding: 3px 8px;
                border: none; border-radius: 3px; text-align: left; }
            QPushButton:hover { background: #34495e; }
            QPushButton:checked { background: #1a252f; }
            """
        )
        self._win.btn_console_toggle.toggled.connect(self._win.console_controller.toggle_console)

        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("font-size: 10px; padding: 2px 6px; color: #7f8c8d;")
        btn_clear.clicked.connect(lambda: self._win.console.clear())

        console_header.addWidget(self._win.btn_console_toggle)
        console_header.addStretch()
        console_header.addWidget(btn_clear)

        self._win.console = QPlainTextEdit()
        self._win.console.setReadOnly(True)
        self._win.console.setMaximumBlockCount(1000)
        self._win.console.setVisible(False)
        self._win.console.setFixedHeight(140)
        self._win.console.setStyleSheet(
            """
            QPlainTextEdit {
                background: #1e2a35; color: #a8d8a8;
                font-family: Consolas, monospace; font-size: 11px;
                border: none; padding: 4px;
            }
            """
        )

        self._win.progress_bar = QProgressBar()
        self._win.progress_bar.setVisible(False)
        self._win.lbl_status = QLabel("Ready")

        right_layout.addWidget(self._win.progress_bar)
        right_layout.addWidget(self._win.lbl_status)
        right_layout.addLayout(console_header)
        right_layout.addWidget(self._win.console)

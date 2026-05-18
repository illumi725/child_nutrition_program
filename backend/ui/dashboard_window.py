import json
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QGridLayout, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from ui.workers import GlobalStatsWorker


# ─── Detail List Dialog ──────────────────────────────────────────────────────

class RecordListDialog(QDialog):
    def __init__(self, title, records, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(860, 500)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        screen = self.screen().availableGeometry()
        self.move((screen.width() - self.width()) // 2,
                  (screen.height() - self.height()) // 2)

        layout = QVBoxLayout(self)

        lbl = QLabel(f"{title}  —  {len(records)} record(s)")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 4px;")
        layout.addWidget(lbl)

        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([c["label"] for c in columns])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget { border: 1px solid #ecf0f1; font-size: 13px; }
            QHeaderView::section {
                background-color: #2c3e50; color: white;
                padding: 6px; font-weight: bold; border: none;
            }
            QTableWidget::item:selected { background-color: #d6eaf8; color: #2c3e50; }
        """)

        table.setRowCount(len(records))
        for row_i, rec in enumerate(records):
            for col_i, col in enumerate(columns):
                getter = col.get("getter")
                val = getter(rec) if getter else rec.get(col["key"], "")
                item = QTableWidgetItem(str(val) if val is not None else "—")
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_i, col_i, item)

        layout.addWidget(table)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


# ─── Clickable Stat Card ─────────────────────────────────────────────────────

class StatCard(QFrame):
    clicked = Signal()

    def __init__(self, title, color):
        super().__init__()
        self.color = color
        self._records = []
        self._columns = []
        self._title = title
        self._open_db_manager = False   # set True for DB duplicates card

        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 8px;
            }}
            QFrame:hover {{
                background-color: #f0f4ff;
                border: 2.5px solid {color};
            }}
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QVBoxLayout(self)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #7f8c8d; font-size: 13px; font-weight: bold; border: none;")
        lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_value = QLabel("-")
        self.lbl_value.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold; border: none;")
        self.lbl_value.setAlignment(Qt.AlignCenter)

        self.lbl_hint = QLabel("Click to view list")
        self.lbl_hint.setStyleSheet("color: #bdc3c7; font-size: 10px; border: none;")
        self.lbl_hint.setAlignment(Qt.AlignCenter)

        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_hint)

    def set_value(self, val, records=None, columns=None):
        self.lbl_value.setText(str(val))
        if records is not None:
            self._records = records
        if columns is not None:
            self._columns = columns

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._records:
            self.clicked.emit()
            if self._open_db_manager:
                # Group records by (lastname, firstname) and show manager picker
                from ui.components.db_duplicate_dialog import DBDuplicateDialog
                from collections import defaultdict
                groups = defaultdict(list)
                for r in self._records:
                    key = (str(r.get('lastname', '')).upper(), str(r.get('firstname', '')).upper())
                    groups[key].append(r)
                dup_groups = [g for g in groups.values() if len(g) > 1]
                if not dup_groups:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(self.window(), "No Duplicates", "No groups with more than one record found.")
                    return
                # Show a picker dialog listing each duplicate group
                picker = DupGroupPickerDialog(dup_groups, self.window())
                picker.exec()
            else:
                dialog = RecordListDialog(self._title, self._records, self._columns, self.window())
                dialog.exec()
        super().mousePressEvent(event)

    def set_db_manager_mode(self, enabled: bool):
        """Enable special mode: clicking opens DBDuplicateDialog instead of generic list."""
        self._open_db_manager = enabled



# ─── Duplicate Group Picker ───────────────────────────────────────────────────

class DupGroupPickerDialog(QDialog):
    """Lists all duplicate name groups; double-click a group to open DBDuplicateDialog."""

    def __init__(self, dup_groups, parent=None):
        super().__init__(parent)
        self.dup_groups = dup_groups
        self.setWindowTitle("DB Duplicate Groups")
        self.resize(600, 400)
        screen = self.screen().availableGeometry()
        self.move((screen.width() - self.width()) // 2,
                  (screen.height() - self.height()) // 2)

        layout = QVBoxLayout(self)

        lbl = QLabel(f"Found {len(dup_groups)} duplicate name group(s). Double-click a group to manage it.")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #c0392b; margin-bottom: 4px;")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Count", "IDs", "Sites"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #ecf0f1; font-size: 12px; }
            QHeaderView::section {
                background-color: #2c3e50; color: white;
                padding: 6px; font-weight: bold; border: none;
            }
            QTableWidget::item:selected { background-color: #fadbd8; }
        """)
        self.table.setRowCount(len(dup_groups))
        for i, group in enumerate(dup_groups):
            r0 = group[0]
            name = f"{r0.get('lastname', '')}, {r0.get('firstname', '')}"
            ids  = ", ".join(str(r.get('beneficiary_id', '')) for r in group)
            sites = ", ".join(set(str(r.get('site_name', '—')) for r in group))
            for col, val in enumerate([name, str(len(group)), ids, sites]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, col, item)

        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _on_double_click(self, index):
        row = index.row()
        if row < len(self.dup_groups):
            from ui.components.db_duplicate_dialog import DBDuplicateDialog
            dlg = DBDuplicateDialog(self.dup_groups[row], parent=self)
            dlg.exec()


# ─── Column Definitions ───────────────────────────────────────────────────────

DB_COLS = [
    {"label": "ID",          "key": "beneficiary_id"},
    {"label": "Last Name",   "key": "lastname"},
    {"label": "First Name",  "key": "firstname"},
    {"label": "Middle Name", "key": "middlename"},
    {"label": "Birthday",    "key": "birthday"},
    {"label": "Gender",      "key": "gender"},
    {"label": "Site",        "key": "site_name"},
]

EXCEL_COLS = [
    {"label": "Name",     "key": "raw_name"},
    {"label": "Birthday", "key": "birthday"},
    {"label": "Gender",   "key": "gender"},
    {"label": "Weight",   "key": "weight"},
    {"label": "Height",   "key": "height"},
    {"label": "File",     "key": "file_path",
     "getter": lambda r: os.path.basename(r.get("file_path", ""))},
]


# ─── Dashboard Window ─────────────────────────────────────────────────────────

class DashboardWindow(QDialog):
    def __init__(self, base_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Global Statistics")
        self.setFixedSize(720, 510)
        self.base_dir = base_dir
        self.setup_ui()

        screen = self.screen().availableGeometry()
        self.move((screen.width() - self.width()) // 2,
                  (screen.height() - self.height()) // 2)

        # Try to load from cache first
        if not self._load_cache():
            self.start_worker()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Global System Diagnostics")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self.lbl_status = QLabel(f"Loading…")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.card_db_total   = StatCard("Total DB Beneficiaries",      "#2980b9")
        self.card_ex_total   = StatCard("Total Excel Beneficiaries",   "#27ae60")
        self.card_missing_db = StatCard("Missing in DB (Excel Only)",  "#e74c3c")
        self.card_missing_ex = StatCard("Missing in Excel (DB Only)",  "#f39c12")
        self.card_db_dupes   = StatCard("DB Duplicates",               "#8e44ad")
        self.card_ex_dupes   = StatCard("Excel Duplicates",            "#c0392b")

        grid.addWidget(self.card_db_total,   0, 0)
        grid.addWidget(self.card_ex_total,   0, 1)
        grid.addWidget(self.card_missing_db, 1, 0)
        grid.addWidget(self.card_missing_ex, 1, 1)
        grid.addWidget(self.card_db_dupes,   2, 0)
        grid.addWidget(self.card_ex_dupes,   2, 1)

        layout.addLayout(grid)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄  Refresh Stats")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #2980b9; color: white;
                font-weight: bold; padding: 7px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #3498db; }
            QPushButton:disabled { background-color: #95a5a6; }
        """)
        self.btn_refresh.clicked.connect(self.start_worker)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("padding: 7px; border-radius: 5px;")
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _load_cache(self):
        try:
            if not os.path.exists(GlobalStatsWorker.CACHE_PATH):
                return False
            with open(GlobalStatsWorker.CACHE_PATH, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            self._apply_stats(stats, from_cache=True)
            return True
        except Exception as e:
            print(f"[CACHE-LOAD] {e}")
            return False

    def _apply_stats(self, stats, from_cache=False):
        scanned_at = stats.get("scanned_at", "Unknown")
        files = stats.get("files_scanned", "?")
        base  = stats.get("base_dir", self.base_dir)
        if from_cache:
            self.lbl_status.setText(
                f"📂  Loaded from cache  |  Last scanned: {scanned_at}  |  {files} file(s)  |  {base}"
            )
        else:
            self.lbl_status.setText(
                f"✅  Scan complete  |  {scanned_at}  |  {files} file(s)  |  {base}"
            )

        self.card_db_total.set_value(stats['total_db'],    records=stats.get('db_records', []),           columns=DB_COLS)
        self.card_ex_total.set_value(stats['total_excel'], records=stats.get('excel_records', []),        columns=EXCEL_COLS)
        self.card_missing_db.set_value(stats['missing_in_db'],  records=stats.get('missing_in_db_list', []),  columns=EXCEL_COLS)
        self.card_missing_ex.set_value(stats['missing_in_excel'], records=stats.get('missing_in_excel_list', []), columns=DB_COLS)
        self.card_db_dupes.set_value(
            stats['db_duplicates'],
            records=stats.get('db_duplicates_list', []),
            columns=DB_COLS
        )
        self.card_db_dupes.set_db_manager_mode(True)  # opens DBDuplicateDialog on click
        self.card_ex_dupes.set_value(stats['excel_duplicates'],records=stats.get('excel_duplicates_list', []),columns=EXCEL_COLS)

    # ── Worker ────────────────────────────────────────────────────────────────

    def start_worker(self):
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Scanning…")
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.lbl_status.setText(f"Scanning: {self.base_dir}")

        self.worker = GlobalStatsWorker(self.base_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, val, msg):
        self.progress.setValue(val)
        self.lbl_status.setText(msg)

    def on_finished(self, stats):
        self.progress.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("🔄  Refresh Stats")
        self._apply_stats(stats, from_cache=False)

    def on_error(self, err):
        self.progress.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("🔄  Refresh Stats")
        self.lbl_status.setText(f"❌  Error: {err}")
        self.lbl_status.setStyleSheet("color: red; font-size: 11px;")

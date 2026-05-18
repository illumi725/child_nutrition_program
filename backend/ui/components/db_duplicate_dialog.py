from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFrame, QScrollArea, QWidget, QButtonGroup, QRadioButton
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from datetime import datetime

def format_display_date(date_val):
    if not date_val: return ""
    date_str = str(date_val).strip()
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except:
        return date_str


class FetchCountsWorker(QThread):
    finished = Signal(list)  # list of (record, counts_dict)
    error = Signal(str)

    def __init__(self, records):
        super().__init__()
        self.records = records

    def run(self):
        try:
            from core.database import get_beneficiary_related_counts
            result = []
            for r in self.records:
                counts = get_beneficiary_related_counts(r['beneficiary_id'])
                result.append((r, counts))
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DeleteWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, beneficiary_id):
        super().__init__()
        self.beneficiary_id = beneficiary_id

    def run(self):
        from core.database import delete_beneficiary_cascade
        ok, err = delete_beneficiary_cascade(self.beneficiary_id)
        self.finished.emit(ok, err or "")


class DBDuplicateDialog(QDialog):
    """Shows all duplicate DB records for a given name, with related counts, and lets the user delete one."""

    def __init__(self, duplicate_records, parent=None):
        super().__init__(parent)
        self.duplicate_records = duplicate_records
        self.records_with_counts = []
        self.selected_id = None

        self.setWindowTitle("Manage DB Duplicate Beneficiaries")
        self.setMinimumSize(900, 520)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        screen = self.screen().availableGeometry()
        self.move((screen.width() - self.width()) // 2,
                  (screen.height() - self.height()) // 2)

        self.setup_ui()
        self.load_counts()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        lbl = QLabel("⚠  Duplicate Beneficiary Records Found")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #c0392b;")
        layout.addWidget(lbl)

        sub = QLabel(
            "Review the records below. Each row shows how many related records exist.\n"
            "Select the record you want to DELETE, then click [Delete Selected]."
        )
        sub.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(sub)

        self.lbl_status = QLabel("Loading related record counts...")
        self.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Select", "ID", "Last Name", "First Name", "Birthday",
            "Gender", "Site",
            "Feedings", "Baseline", "Ht/Wt", "Parents / Absences"
        ])
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
            QTableWidget::item:selected { background-color: #fadbd8; color: #2c3e50; }
        """)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_delete = QPushButton("🗑  Delete Selected Record (with all related data)")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #c0392b; color: white;
                font-weight: bold; padding: 8px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #e74c3c; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.btn_delete.clicked.connect(self.on_delete)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("padding: 8px; border-radius: 5px;")
        btn_close.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def load_counts(self):
        self.lbl_status.setText("Fetching related record counts from database...")
        self.worker = FetchCountsWorker(self.duplicate_records)
        self.worker.finished.connect(self._populate_table)
        self.worker.error.connect(lambda e: self.lbl_status.setText(f"Error: {e}"))
        self.worker.start()

    def _populate_table(self, records_with_counts):
        self.records_with_counts = records_with_counts
        self.table.setRowCount(len(records_with_counts))

        for row_i, (rec, counts) in enumerate(records_with_counts):
            feeding = counts.get('feeding_records', 0)
            baseline = counts.get('baseline_info', 0)
            hw = counts.get('height_weight_records', 0)
            parents = counts.get('parent_links', 0)
            absences = counts.get('absence_records', 0)

            vals = [
                "",  # placeholder for select col
                str(rec.get('beneficiary_id', '')),
                rec.get('lastname', ''),
                rec.get('firstname', ''),
                format_display_date(rec.get('birthday', '')),
                rec.get('gender', ''),
                rec.get('site_name', '') or '—',
                str(feeding),
                str(baseline),
                str(hw),
                f"{parents} parents / {absences} absences",
            ]

            for col_i, val in enumerate(vals):
                if col_i == 0:
                    continue
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                # Highlight rows with more data in green (= likely the keeper)
                total = (feeding if isinstance(feeding, int) else 0) + \
                        (baseline if isinstance(baseline, int) else 0)
                if total > 0:
                    item.setBackground(QColor("#eafaf1"))
                    item.setForeground(QColor("black"))
                self.table.setItem(row_i, col_i, item)

        self.lbl_status.setText(
            f"✅  Loaded {len(records_with_counts)} duplicate record(s). "
            "Rows highlighted in green have related data — consider keeping those."
        )

    def _on_selection_changed(self):
        rows = set(i.row() for i in self.table.selectedItems())
        if len(rows) == 1:
            row = list(rows)[0]
            if row < len(self.records_with_counts):
                rec, _ = self.records_with_counts[row]
                self.selected_id = rec['beneficiary_id']
                self.btn_delete.setEnabled(True)
                name = f"{rec.get('lastname')}, {rec.get('firstname')}"
                self.btn_delete.setText(f"🗑  Delete: {name} (ID: {self.selected_id})")
        else:
            self.selected_id = None
            self.btn_delete.setEnabled(False)
            self.btn_delete.setText("🗑  Delete Selected Record (with all related data)")

    def on_delete(self):
        if not self.selected_id:
            return

        # Find the record to show in confirmation
        rec = next((r for r, _ in self.records_with_counts if r['beneficiary_id'] == self.selected_id), {})
        counts = next((c for r, c in self.records_with_counts if r['beneficiary_id'] == self.selected_id), {})

        detail = "\n".join([f"  • {k}: {v} records" for k, v in counts.items()])
        confirm = QMessageBox.warning(
            self,
            "Confirm Hard Delete",
            f"You are about to PERMANENTLY DELETE:\n\n"
            f"  {rec.get('lastname')}, {rec.get('firstname')} (ID: {self.selected_id})\n\n"
            f"Related records that will also be deleted:\n{detail}\n\n"
            f"⚠  This action CANNOT be undone. Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        self.btn_delete.setEnabled(False)
        self.btn_delete.setText("Deleting...")
        self.lbl_status.setText("Deleting record and all related data...")

        self.del_worker = DeleteWorker(self.selected_id)
        self.del_worker.finished.connect(self._on_delete_done)
        self.del_worker.start()

    def _on_delete_done(self, success, err):
        if success:
            self.lbl_status.setText(f"✅  Record ID {self.selected_id} and all related data deleted successfully.")
            # Remove from internal list and refresh table
            self.records_with_counts = [
                (r, c) for r, c in self.records_with_counts
                if r['beneficiary_id'] != self.selected_id
            ]
            self.selected_id = None
            self._populate_table(self.records_with_counts)
            self.btn_delete.setEnabled(False)
            self.btn_delete.setText("🗑  Delete Selected Record (with all related data)")

            if len(self.records_with_counts) <= 1:
                QMessageBox.information(self, "Done", "Duplicate resolved! Only one record remains.")
                self.accept()
        else:
            self.lbl_status.setText(f"❌  Error: {err}")
            self.btn_delete.setEnabled(True)
            self.btn_delete.setText("🗑  Delete Selected Record (with all related data)")
            QMessageBox.critical(self, "Delete Failed", f"Could not delete record:\n{err}")

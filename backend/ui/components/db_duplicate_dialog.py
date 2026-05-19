from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFrame, QScrollArea, QWidget, QButtonGroup, QRadioButton,
    QCheckBox
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
            results = []
            for rec in self.records:
                b_id = rec.get('beneficiary_id')
                counts = get_beneficiary_related_counts(b_id)
                results.append((rec, counts))
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class DeleteWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, beneficiary_ids):
        super().__init__()
        self.beneficiary_ids = beneficiary_ids

    def run(self):
        from core.database import delete_beneficiary_cascade
        errors = []
        for b_id in self.beneficiary_ids:
            ok, err = delete_beneficiary_cascade(b_id)
            if not ok:
                errors.append(f"ID {b_id}: {err}")
        if errors:
            self.finished.emit(False, "\n".join(errors))
        else:
            self.finished.emit(True, "")


class DBDuplicateDialog(QDialog):
    """Shows all duplicate DB records for a given name, with related counts, and lets the user delete them."""

    def __init__(self, duplicate_records, parent=None):
        super().__init__(parent)
        self.duplicate_records = duplicate_records
        self.records_with_counts = []
        self.selected_ids = []
        self.checkboxes = []

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
            "Tick the row(s) you want to permanently DELETE from the Database, then click [Delete Selected]."
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
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ecf0f1;
                font-size: 12px;
                background-color: white;
                color: #2c3e50;
                alternate-background-color: #f8f9fa;
            }
            QHeaderView::section {
                background-color: #2c3e50; color: white;
                padding: 6px; font-weight: bold; border: none;
            }
            QTableWidget::item:selected { background-color: #fadbd8; color: #2c3e50; }
        """)
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
        self.checkboxes = []

        for row_i, (rec, counts) in enumerate(records_with_counts):
            feeding = counts.get('feeding_records', 0)
            baseline = counts.get('baseline_info', 0)
            hw = counts.get('height_weight_records', 0)
            parents = counts.get('parent_links', 0)
            absences = counts.get('absence_records', 0)

            # Create centered checkbox widget for column 0
            chk = QCheckBox()
            chk.stateChanged.connect(self._update_delete_btn)
            self.checkboxes.append(chk)
            self.table.setCellWidget(row_i, 0, self._centered_widget(chk))

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

            # Determine if row should be highlighted in green
            total = (feeding if isinstance(feeding, int) else 0) + \
                    (baseline if isinstance(baseline, int) else 0)
            is_green = total > 0

            for col_i, val in enumerate(vals):
                if col_i == 0:
                    continue
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if is_green:
                    item.setBackground(QColor("#eafaf1"))
                    item.setForeground(QColor("black"))
                self.table.setItem(row_i, col_i, item)

            # Add blank item for column 0 to support background green highlighting
            bg_item = QTableWidgetItem("")
            if is_green:
                bg_item.setBackground(QColor("#eafaf1"))
            self.table.setItem(row_i, 0, bg_item)

        self.lbl_status.setText(
            f"✅  Loaded {len(records_with_counts)} duplicate record(s). "
            "Rows highlighted in green have related data — consider keeping those."
        )
        self._update_delete_btn()

    def _centered_widget(self, widget):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    def _update_delete_btn(self):
        checked_indices = [i for i, chk in enumerate(self.checkboxes) if chk.isChecked()]
        num_checked = len(checked_indices)
        total_rows = len(self.checkboxes)

        if num_checked == 0:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setText("🗑  Delete Selected Record (with all related data)")
            self.lbl_status.setText("Select duplicate records to delete.")
            self.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")
            self.selected_ids = []
        elif num_checked == total_rows:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setText("🗑  Delete Selected Record (with all related data)")
            self.lbl_status.setText("⚠ You cannot delete ALL occurrences. At least one record must be retained.")
            self.lbl_status.setStyleSheet("color: #c0392b; font-size: 11px; font-weight: bold;")
            self.selected_ids = []
        else:
            self.btn_delete.setEnabled(True)
            self.selected_ids = [self.records_with_counts[i][0]['beneficiary_id'] for i in checked_indices]
            
            if num_checked == 1:
                rec, _ = self.records_with_counts[checked_indices[0]]
                name = f"{rec.get('lastname')}, {rec.get('firstname')}"
                self.btn_delete.setText(f"🗑  Delete: {name} (ID: {rec['beneficiary_id']})")
            else:
                self.btn_delete.setText(f"🗑  Delete {num_checked} Selected Records")
                
            self.lbl_status.setText("Select duplicate records to delete.")
            self.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")

    def on_delete(self):
        if not self.selected_ids:
            return

        recs_to_delete = []
        for b_id in self.selected_ids:
            rec = next((r for r, _ in self.records_with_counts if r['beneficiary_id'] == b_id), {})
            counts = next((c for r, c in self.records_with_counts if r['beneficiary_id'] == b_id), {})
            recs_to_delete.append((rec, counts))

        summary_lines = []
        total_counts = {}
        for rec, counts in recs_to_delete:
            summary_lines.append(f"  • {rec.get('lastname')}, {rec.get('firstname')} (ID: {rec['beneficiary_id']})")
            for k, v in counts.items():
                if isinstance(v, int):
                    total_counts[k] = total_counts.get(k, 0) + v

        detail = "\n".join([f"  • {k}: {v} records" for k, v in total_counts.items() if v > 0])
        if not detail:
            detail = "  • No related counts found"

        confirm = QMessageBox.warning(
            self,
            "Confirm Hard Delete",
            f"You are about to PERMANENTLY DELETE {len(recs_to_delete)} record(s) from Database:\n\n" +
            "\n".join(summary_lines) + f"\n\nTotal related records that will also be deleted:\n{detail}\n\n"
            f"⚠  This action CANNOT be undone. Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        self.btn_delete.setEnabled(False)
        self.btn_delete.setText("Deleting...")
        self.lbl_status.setText("Deleting records and all related data...")

        self.del_worker = DeleteWorker(self.selected_ids)
        self.del_worker.finished.connect(self._on_delete_done)
        self.del_worker.start()

    def _on_delete_done(self, success, err):
        if success:
            self.lbl_status.setText(f"✅  Selected record(s) and all related data deleted successfully.")
            # Remove from internal list and refresh table
            self.records_with_counts = [
                (r, c) for r, c in self.records_with_counts
                if r['beneficiary_id'] not in self.selected_ids
            ]
            self.selected_ids = []
            self._populate_table(self.records_with_counts)
            self._update_delete_btn()

            if len(self.records_with_counts) <= 1:
                QMessageBox.information(self, "Done", "Duplicate resolved! Only one record remains.")
                self.accept()
        else:
            self.lbl_status.setText(f"❌  Error: {err}")
            self._update_delete_btn()
            QMessageBox.critical(self, "Delete Failed", f"Could not delete record(s):\n{err}")

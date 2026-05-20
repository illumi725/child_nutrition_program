import os
import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QCheckBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


def format_display_date(date_val):
    if not date_val: return ""
    date_str = str(date_val).strip()
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except:
        return date_str


def _interfile_cache_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "interfile_index_cache.json")
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "interfile_index_cache.json")
    )


class ExcelDuplicateDialog(QDialog):
    """
    Shows all occurrences of a duplicated name across Excel files.
    Lets the user select which row(s) to permanently delete.
    After deletion, the inter-file index cache is cleared.
    """

    def __init__(self, dup_entry, parent=None):
        """
        dup_entry: the dict from excel_duplicates list:
            { 'name', 'birthday', 'type', 'files', 'rows': [excel_record, ...] }
        Each excel_record must have: raw_name, birthday, weight, height, file_path, row_number
        """
        super().__init__(parent)
        self.dup_entry = dup_entry
        self.rows = dup_entry.get('rows', [])

        self.setWindowTitle(f"Manage Excel Duplicate — {dup_entry.get('name', '')}")
        self.setMinimumSize(720, 420)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        self.setup_ui()
        self.populate_table()

        # Center Dialog perfectly relative to parent window or screen
        if parent:
            parent_geo = parent.geometry()
            self.move(
                parent_geo.left() + (parent_geo.width() - self.width()) // 2,
                parent_geo.top() + (parent_geo.height() - self.height()) // 2
            )
        else:
            screen = self.screen().availableGeometry()
            self.move(
                screen.x() + (screen.width() - self.width()) // 2,
                screen.y() + (screen.height() - self.height()) // 2
            )

    def setup_ui(self):
        layout = QVBoxLayout(self)

        lbl = QLabel(f"📋  Excel Duplicate: {self.dup_entry.get('name', '')}")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #c0392b;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        sub = QLabel(
            f"Type: {self.dup_entry.get('type', '')}  |  Found in: {self.dup_entry.get('files', '')}\n"
            "Tick the row(s) you want to permanently DELETE from the Excel file, then click [Delete Selected Rows]."
        )
        sub.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        self.lbl_status = QLabel("Select duplicate rows to delete.")
        self.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Delete?", "Name", "Birthday", "Weight", "Height", "Row #", "File"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

        self.table.setWordWrap(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setVisible(False)
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

        self.checkboxes = []

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_delete = QPushButton("🗑  Delete Selected Rows from Excel")
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

    def populate_table(self):
        self.table.setRowCount(len(self.rows))
        self.checkboxes = []

        for row_i, rec in enumerate(self.rows):
            # Checkbox
            chk = QCheckBox()
            chk.stateChanged.connect(self._update_delete_btn)
            self.checkboxes.append(chk)
            self.table.setCellWidget(row_i, 0, self._centered_widget(chk))

            vals = [
                rec.get('raw_name', ''),
                format_display_date(rec.get('birthday', '')),
                str(rec.get('weight', '—')),
                str(rec.get('height', '—')),
                str(rec.get('row_number', '?')),
                os.path.basename(rec.get('file_path', '')),
            ]
            for col_i, val in enumerate(vals, start=1):
                item = QTableWidgetItem(val)
                if col_i == 1:  # Name column
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                elif col_i == 6:  # File column
                    # Left-align file name and add tooltip for full visibility
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    item.setToolTip(rec.get('file_path', ''))
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_i, col_i, item)
        self.table.resizeColumnsToContents()

    def _centered_widget(self, widget):
        container = __import__('PySide6.QtWidgets', fromlist=['QWidget']).QWidget()
        layout = __import__('PySide6.QtWidgets', fromlist=['QHBoxLayout']).QHBoxLayout(container)
        layout.addWidget(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    def _update_delete_btn(self):
        num_checked = sum(1 for chk in self.checkboxes if chk.isChecked())
        total_rows = len(self.checkboxes)

        if num_checked == 0:
            self.btn_delete.setEnabled(False)
            self.lbl_status.setText("Select duplicate rows to delete.")
            self.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")
        elif num_checked == total_rows:
            self.btn_delete.setEnabled(False)
            self.lbl_status.setText("⚠ You cannot delete ALL occurrences. At least one row must be retained.")
            self.lbl_status.setStyleSheet("color: #c0392b; font-size: 11px; font-weight: bold;")
        else:
            self.btn_delete.setEnabled(True)
            self.lbl_status.setText("Select duplicate rows to delete.")
            self.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")

    def on_delete(self):
        selected_indices = [i for i, chk in enumerate(self.checkboxes) if chk.isChecked()]
        if not selected_indices:
            return

        selected_rows = [self.rows[i] for i in selected_indices]
        summary = "\n".join(
            f"  Row {r.get('row_number')} in {os.path.basename(r.get('file_path', ''))}"
            for r in selected_rows
        )
        confirm = QMessageBox.warning(
            self,
            "Confirm Row Deletion",
            f"You are about to PERMANENTLY DELETE {len(selected_rows)} row(s) from Excel:\n\n"
            f"{summary}\n\n"
            "⚠  This will also clear the inter-file index cache.\n"
            "The rows will be removed and remaining rows will shift up.\n\n"
            "Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        from core.excel_updater import delete_excel_row

        # Group by file and sort row numbers DESCENDING so deleting lower rows
        # doesn't shift the row numbers of rows we haven't deleted yet
        from collections import defaultdict
        by_file = defaultdict(list)
        for rec in selected_rows:
            by_file[rec.get('file_path', '')].append(rec)

        errors = []
        deleted = 0
        for file_path, recs in by_file.items():
            # Sort descending so bottom rows deleted first
            for rec in sorted(recs, key=lambda r: r.get('row_number', 0), reverse=True):
                ok, err = delete_excel_row(file_path, rec.get('row_number'))
                if ok:
                    deleted += 1
                else:
                    errors.append(f"{os.path.basename(file_path)} row {rec.get('row_number')}: {err}")

        # Clear inter-file index cache
        try:
            cache = _interfile_cache_path()
            if os.path.exists(cache):
                os.remove(cache)
        except Exception as e:
            errors.append(f"Cache clear failed: {e}")


        # Refresh table — remove deleted rows
        deleted_file_rows = {(r.get('file_path'), r.get('row_number')) for r in selected_rows}
        self.rows = [r for r in self.rows if (r.get('file_path'), r.get('row_number')) not in deleted_file_rows]
        self.checkboxes = []
        self.populate_table()

        if errors:
            self.lbl_status.setText(f"⚠  {deleted} row(s) deleted. {len(errors)} error(s) occurred.")
            QMessageBox.warning(self, "Partial Success", "Some rows could not be deleted:\n" + "\n".join(errors))
        else:
            self.lbl_status.setText(
                f"✅  {deleted} row(s) deleted. Inter-file index cache cleared — will rebuild on next scan."
            )

        # ── Cross-Delete Workflow: Check Database ─────────────────────────────
        # Extract name from "LASTNAME, FIRSTNAME"
        name_parts = self.dup_entry.get('name', '').split(', ', 1)
        if len(name_parts) == 2:
            ln, fn = name_parts[0], name_parts[1]
            from core.database import find_beneficiaries_by_name
            db_matches = find_beneficiaries_by_name(ln, fn)

            if db_matches:
                db_confirm = QMessageBox.question(
                    self,
                    "Database Records Found",
                    f"Successfully deleted from Excel.\n\n"
                    f"We also found {len(db_matches)} record(s) for '{fn} {ln}' in the Database.\n\n"
                    f"Would you like to review and delete them from the Database as well?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if db_confirm == QMessageBox.Yes:
                    from ui.components.db_duplicate_dialog import DBDuplicateDialog
                    db_dlg = DBDuplicateDialog(db_matches, parent=self)
                    db_dlg.exec()

        if len(self.rows) <= 1:
            QMessageBox.information(self, "Done", "Duplicate resolved! Only one occurrence remains.")
            self.accept()


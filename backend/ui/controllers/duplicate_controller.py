"""Controller for Excel and DB duplicate management extracted from MainWindow (R7).
"""
from __future__ import annotations

from typing import Any


class DuplicateController:
    def __init__(self, main_window):
        self._win = main_window

    def on_excel_dup_action(self, action: str, record: dict, widget: Any):
        """Called when the 'Manage' button is clicked on an Excel Duplicates row."""
        from ui.components.excel_duplicate_dialog import ExcelDuplicateDialog

        dlg = ExcelDuplicateDialog(record, parent=self._win)
        dlg.exec()

    def on_db_dup_action(self, action: str, record: dict, widget: Any):
        """Called when the 'Manage' button is clicked on a DB Duplicates row."""
        if action == "manage":
            self.open_db_duplicate_manager(record["records"])

    def open_db_duplicate_manager(self, duplicate_records: list):
        """Open the DB Duplicate Manager for a set of duplicate beneficiary records."""
        from ui.components.db_duplicate_dialog import DBDuplicateDialog

        dlg = DBDuplicateDialog(duplicate_records, parent=self._win)
        dlg.exec()


class DBDuplicateDialogController:
    def __init__(self, dialog):
        self._dlg = dialog

    def load_counts(self):
        self._dlg.lbl_status.setText("Fetching related record counts from database...")
        self._dlg.worker = self._create_fetch_counts_worker(self._dlg.duplicate_records)
        self._dlg.worker.finished.connect(self._dlg._populate_table)
        self._dlg.worker.error.connect(lambda e: self._dlg.lbl_status.setText(f"Error: {e}"))
        self._dlg.worker.start()

    def _create_fetch_counts_worker(self, records):
        from ui.components.db_duplicate_dialog import FetchCountsWorker
        return FetchCountsWorker(records)

    def apply_delete_permission(self):
        from ui.auth_guard import user_has_permission

        if not user_has_permission(self._dlg._current_user(), "delete_beneficiary"):
            self._dlg.btn_delete.setVisible(False)
            self._dlg.btn_delete.setEnabled(False)

    def update_delete_button(self):
        checked_indices = [i for i, chk in enumerate(self._dlg.checkboxes) if chk.isChecked()]
        num_checked = len(checked_indices)
        total_rows = len(self._dlg.checkboxes)

        if num_checked == 0:
            self._dlg.btn_delete.setEnabled(False)
            self._dlg.btn_delete.setText("🗑  Delete Selected Record (with all related data)")
            self._dlg.lbl_status.setText("Select duplicate records to delete.")
            self._dlg.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")
            self._dlg.selected_ids = []
            return

        if num_checked == total_rows:
            self._dlg.btn_delete.setEnabled(False)
            self._dlg.btn_delete.setText("🗑  Delete Selected Record (with all related data)")
            self._dlg.lbl_status.setText("⚠ You cannot delete ALL occurrences. At least one record must be retained.")
            self._dlg.lbl_status.setStyleSheet("color: #c0392b; font-size: 11px; font-weight: bold;")
            self._dlg.selected_ids = []
            return

        self._dlg.selected_ids = [self._dlg.records_with_counts[i][0]["beneficiary_id"] for i in checked_indices]
        self._dlg.btn_delete.setEnabled(True)

        if num_checked == 1:
            rec, _ = self._dlg.records_with_counts[checked_indices[0]]
            self._dlg.btn_delete.setText(f"🗑  Delete: {rec.get('lastname')}, {rec.get('firstname')} (ID: {rec['beneficiary_id']})")
        else:
            self._dlg.btn_delete.setText(f"🗑  Delete {num_checked} Selected Records")

        self._dlg.lbl_status.setText("Select duplicate records to delete.")
        self._dlg.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")

    def _build_delete_summary(self, recs_to_delete):
        summary_lines = []
        total_counts = {}
        for rec, counts in recs_to_delete:
            summary_lines.append(f"  • {rec.get('lastname')}, {rec.get('firstname')} (ID: {rec['beneficiary_id']})")
            for k, v in counts.items():
                if isinstance(v, int):
                    total_counts[k] = total_counts.get(k, 0) + v
        detail_lines = [f"  • {k}: {v} records" for k, v in total_counts.items() if v > 0]
        detail = "\n".join(detail_lines) if detail_lines else "  • No related counts found"
        return summary_lines, detail

    def on_delete(self):
        from ui.auth_guard import require_permission

        if not require_permission(self._dlg, self._dlg._current_user(), "delete_beneficiary"):
            return False
        if not self._dlg.selected_ids:
            return False

        recs_to_delete = []
        for b_id in self._dlg.selected_ids:
            rec = next((r for r, _ in self._dlg.records_with_counts if r['beneficiary_id'] == b_id), {})
            counts = next((c for r, c in self._dlg.records_with_counts if r['beneficiary_id'] == b_id), {})
            recs_to_delete.append((rec, counts))

        summary_lines, detail = self._build_delete_summary(recs_to_delete)
        confirm = self._dlg._confirm_delete(summary_lines, detail)
        if confirm != True:
            return False

        self._dlg.btn_delete.setEnabled(False)
        self._dlg.btn_delete.setText("Deleting...")
        self._dlg.lbl_status.setText("Deleting records and all related data...")

        from ui.components.db_duplicate_dialog import DeleteWorker
        self._dlg.del_worker = DeleteWorker(self._dlg.selected_ids)
        self._dlg.del_worker.finished.connect(self.on_delete_done)
        self._dlg.del_worker.start()
        return True

    def on_delete_done(self, success, err):
        if success:
            self._dlg.lbl_status.setText("✅  Selected record(s) and all related data deleted successfully.")
            self._dlg.records_with_counts = [
                (r, c) for r, c in self._dlg.records_with_counts
                if r['beneficiary_id'] not in self._dlg.selected_ids
            ]
            self._dlg.selected_ids = []
            self._dlg._populate_table(self._dlg.records_with_counts)
            self._dlg._update_delete_btn()

            if len(self._dlg.records_with_counts) <= 1:
                self._dlg._show_message("Done", "Duplicate resolved! Only one record remains.")
                self._dlg.accept()
        else:
            self._dlg.lbl_status.setText(f"❌  Error: {err}")
            self._dlg._update_delete_btn()
            self._dlg._show_message("Delete Failed", f"Could not delete record(s):\n{err}")

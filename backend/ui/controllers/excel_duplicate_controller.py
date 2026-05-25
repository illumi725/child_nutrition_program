"""Controller to handle deletion logic for ExcelDuplicateDialog."""

from __future__ import annotations

import os


class ExcelDuplicateDialogController:
    def __init__(self, dialog):
        self._dlg = dialog

    def apply_delete_permission(self):
        from ui.auth_guard import user_has_permission

        if not user_has_permission(self._dlg._current_user(), "delete_excel_row"):
            self._dlg.btn_delete.setVisible(False)
            self._dlg.btn_delete.setEnabled(False)

    def update_delete_button(self):
        num_checked = sum(1 for chk in self._dlg.checkboxes if chk.isChecked())
        total_rows = len(self._dlg.checkboxes)

        if num_checked == 0:
            self._dlg.btn_delete.setEnabled(False)
            self._dlg.lbl_status.setText("Select duplicate rows to delete.")
            self._dlg.lbl_status.setStyleSheet("color: #2980b9; font-size: 11px;")
            return

        if num_checked == total_rows:
            self._dlg.btn_delete.setEnabled(False)
            self._dlg.lbl_status.setText(
                "⚠ You cannot delete ALL occurrences. At least one row must be retained."  # noqa: E501
            )
            self._dlg.lbl_status.setStyleSheet(
                "color: #c0392b; font-size: 11px; font-weight: bold;"
            )
            return

        self._dlg.btn_delete.setEnabled(True)

    def on_delete(self):
        from ui.auth_guard import require_permission

        if not require_permission(
            self._dlg, self._dlg._current_user(), "delete_excel_row"
        ):
            return False

        selected_indices = [
            i for i, chk in enumerate(self._dlg.checkboxes) if chk.isChecked()
        ]
        if not selected_indices:
            return False

        selected_rows = [self._dlg.rows[i] for i in selected_indices]
        summary = "\n".join(
            f"  Row {r.get('row_number')} in {os.path.basename(r.get('file_path', ''))}"
            for r in selected_rows
        )

        from PySide6.QtWidgets import QMessageBox

        confirm = QMessageBox.warning(
            self._dlg,
            "Confirm Row Deletion",
            f"You are about to PERMANENTLY DELETE {len(selected_rows)} row(s) from Excel:\n\n"  # noqa: E501
            f"{summary}\n\n"
            "⚠  This will also clear the inter-file index cache.\n"
            "The rows will be removed and remaining rows will shift up.\n\n"
            "Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if confirm != QMessageBox.Yes:
            return False

        from core.excel_updater import delete_excel_row
        from collections import defaultdict

        by_file = defaultdict(list)
        for rec in selected_rows:
            by_file[rec.get("file_path", "")].append(rec)

        errors = []
        deleted = 0
        for file_path, recs in by_file.items():
            for rec in sorted(recs, key=lambda r: r.get("row_number", 0), reverse=True):
                ok, err = delete_excel_row(file_path, rec.get("row_number"))
                if ok:
                    deleted += 1
                else:
                    errors.append(
                        f"{os.path.basename(file_path)} row {rec.get('row_number')}: {err}"  # noqa: E501
                    )

        # Clear inter-file index cache
        try:
            cache = self._dlg._interfile_cache_path()
            if os.path.exists(cache):
                os.remove(cache)
        except Exception as e:
            errors.append(f"Cache clear failed: {e}")

        # Refresh table — remove deleted rows
        deleted_file_rows = {
            (r.get("file_path"), r.get("row_number")) for r in selected_rows
        }
        self._dlg.rows = [
            r
            for r in self._dlg.rows
            if (r.get("file_path"), r.get("row_number")) not in deleted_file_rows
        ]
        self._dlg.checkboxes = []
        self._dlg.populate_table()

        from PySide6.QtWidgets import QMessageBox as _QMsg

        if errors:
            self._dlg.lbl_status.setText(
                f"⚠  {deleted} row(s) deleted. {len(errors)} error(s) occurred."
            )
            _QMsg.warning(
                self._dlg,
                "Partial Success",
                "Some rows could not be deleted:\n" + "\n".join(errors),
            )
        else:
            self._dlg.lbl_status.setText(
                f"✅  {deleted} row(s) deleted. Inter-file index cache cleared — will rebuild on next scan."  # noqa: E501
            )

        # Check database for matches and optionally open DB duplicate dialog
        name_parts = self._dlg.dup_entry.get("name", "").split(", ", 1)
        if len(name_parts) == 2:
            ln, fn = name_parts[0], name_parts[1]
            from core.database import find_beneficiaries_by_name

            db_matches = find_beneficiaries_by_name(ln, fn)

            if db_matches:
                db_confirm = _QMsg.question(
                    self._dlg,
                    "Database Records Found",
                    f"Successfully deleted from Excel.\n\n"
                    f"We also found {len(db_matches)} record(s) for '{fn} {ln}' in the Database.\n\n"  # noqa: E501
                    f"Would you like to review and delete them from the Database as well?",  # noqa: E501
                    _QMsg.Yes | _QMsg.No,
                    _QMsg.Yes,
                )
                if db_confirm == _QMsg.Yes:
                    from ui.components.db_duplicate_dialog import DBDuplicateDialog

                    db_dlg = DBDuplicateDialog(db_matches, parent=self._dlg)
                    db_dlg.exec()

        if len(self._dlg.rows) <= 1:
            _QMsg.information(
                self._dlg, "Done", "Duplicate resolved! Only one occurrence remains."
            )
            self._dlg.accept()

        return True

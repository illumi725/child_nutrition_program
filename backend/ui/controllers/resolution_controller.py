"""Missing-in-DB and missing-in-Excel resolution actions (R7)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from ui.auth_guard import require_permission


class ResolutionController:
    def __init__(self, main_window):
        self._win = main_window

    def on_missing_db_action(self, action_name, record_data, action_widget):
        from core.database import add_beneficiary_to_db, get_sites
        from ui.components.edit_beneficiary_dialog import EditBeneficiaryDialog

        if action_name != "add_to_db":
            return

        if not require_permission(self._win, self._win.current_user, "add_beneficiary"):
            return

        sites = get_sites()
        if not sites:
            QMessageBox.warning(
                self._win,
                "Error",
                "No feeding sites found in the database. Cannot add.",
            )
            return

        dialog = EditBeneficiaryDialog(record_data, sites, self._win)
        if not dialog.exec():
            return

        final_data = dialog.get_data()
        created_by = (
            self._win.current_user["user_id"] if self._win.current_user else "system"
        )

        success, msg = add_beneficiary_to_db(
            site_id=final_data["site_id"],
            lastname=final_data["lastname"],
            firstname=final_data["firstname"],
            middlename=final_data["middlename"],
            birthday=final_data["birthday"],
            gender=final_data["gender"],
            weight=final_data["weight"],
            height=final_data["height"],
            date_collected=final_data["date_collected"],
            created_by=created_by,
        )

        if success:
            self._win._audit(
                "add_beneficiary",
                "beneficiary",
                entity_id=str(msg) if msg else None,
                details={
                    "firstname": final_data["firstname"],
                    "lastname": final_data["lastname"],
                },
            )
            record_data["_added_to_db"] = True
            action_widget.mark_as_resolved()
            QMessageBox.information(
                self._win,
                "Success",
                f"Successfully added {final_data['firstname']} to the database.",
            )
        else:
            QMessageBox.warning(
                self._win, "Error", f"Failed to add to database:\n{msg}"
            )

    def on_missing_excel_action(self, action, record, widget: Any):
        if action != "delete_from_db":
            return

        from core.database import delete_beneficiary_cascade

        name = f"{record.get('lastname', '')}, {record.get('firstname', '')}"
        reply = QMessageBox.question(
            self._win,
            "Confirm Deletion",
            f"Are you sure you want to permanently delete {name} and all related records from the database?",  # noqa: E501
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        if not require_permission(
            self._win, self._win.current_user, "delete_beneficiary"
        ):
            return

        try:
            bid = record.get("beneficiary_id")
            ok, err = delete_beneficiary_cascade(bid)
            if not ok:
                QMessageBox.critical(
                    self._win,
                    "Database Error",
                    f"Failed to delete record:\n{err or 'Unknown error'}",
                )
                return
            self._win._audit("delete_beneficiary", "beneficiary", bid)
            record["_deleted_from_db"] = True
            if hasattr(widget, "mark_as_resolved"):
                widget.mark_as_resolved()
            QMessageBox.information(
                self._win, "Deleted", f"Successfully deleted {name}."
            )
        except Exception as e:
            QMessageBox.critical(
                self._win, "Database Error", f"Failed to delete record:\n{e}"
            )

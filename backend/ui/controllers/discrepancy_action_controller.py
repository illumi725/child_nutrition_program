"""Controller for discrepancy and missing data actions extracted from RecordActionController."""  # noqa: E501

from __future__ import annotations

from typing import Any


class DiscrepancyActionController:
    def __init__(self, main_window):
        self._win = main_window

    def on_missing_db_action(
        self, action_name: str, record_data: dict, action_widget: Any
    ):
        from core.database import add_beneficiary_to_db, get_sites
        from ui.components.edit_beneficiary_dialog import EditBeneficiaryDialog
        from PySide6.QtWidgets import QMessageBox
        from ui.auth_guard import require_permission

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

    def on_bday_action(self, action_name: str, record: dict, action_widget: Any):
        from core.database import update_birthday_db
        from core.excel_updater import update_excel_birthday
        from PySide6.QtWidgets import QMessageBox, QInputDialog
        from ui.auth_guard import require_permission

        if not require_permission(
            self._win, self._win.current_user, "edit_discrepancy"
        ):
            return

        ex = record["excel"]
        db = record["db"]

        if action_name == "use_excel":
            success = update_birthday_db(db["beneficiary_id"], ex["birthday"])
            if success:
                record["baseline_mismatch"] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(
                    self._win, "Success", f"Updated DB birthday to {ex['birthday']}."
                )
            else:
                QMessageBox.warning(self._win, "Error", "Failed to update DB birthday.")

        elif action_name == "use_db":
            success = update_excel_birthday(
                ex["file_path"], ex["row_number"], db["birthday"]
            )
            if success:
                record["baseline_mismatch"] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(
                    self._win,
                    "Success",
                    f"Updated Excel file birthday to {db['birthday']}.",
                )
            else:
                QMessageBox.warning(
                    self._win, "Error", "Failed to update Excel file birthday."
                )

        elif action_name == "manual":
            date_str, ok = QInputDialog.getText(
                self._win,
                "Manual Correction",
                f"Enter correct birthday for {db['lastname']} (YYYY-MM-DD):",
                text=ex["birthday"] or db["birthday"],
            )
            if not ok or not date_str:
                return

            import re

            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                QMessageBox.warning(
                    self._win, "Error", "Invalid date format. Please use YYYY-MM-DD."
                )
                return

            success_db = update_birthday_db(db["beneficiary_id"], date_str)
            success_ex = update_excel_birthday(
                ex["file_path"], ex["row_number"], date_str
            )

            if success_db and success_ex:
                record["baseline_mismatch"] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(
                    self._win, "Success", f"Updated both DB and Excel to {date_str}."
                )
            else:
                QMessageBox.warning(
                    self._win,
                    "Error",
                    "Failed to fully update. Check console for details.",
                )

    def on_name_action(self, action_name: str, record: dict, action_widget: Any):
        from core.database import update_name_db, get_surname_dictionary
        from core.excel_updater import update_excel_name
        from core.parser import split_beneficiary_name
        from PySide6.QtWidgets import QMessageBox, QInputDialog
        from ui.auth_guard import require_permission

        if not require_permission(
            self._win, self._win.current_user, "edit_discrepancy"
        ):
            return

        ex = record["excel"]
        db = record["db"]

        db_fullname = f"{db.get('lastname', '')}, {db.get('firstname', '')}"
        if db.get("middlename"):
            db_fullname += f" {db.get('middlename')}"

        ex_fullname = ex.get("raw_name", "")

        if action_name == "use_excel":
            surname_dict = get_surname_dictionary()
            ln, fn, mn = split_beneficiary_name(ex_fullname, surname_dict=surname_dict)
            success = update_name_db(db["beneficiary_id"], ln, fn, mn)
            if success:
                record["name_mismatch"] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(
                    self._win, "Success", f"Updated DB name to {ex_fullname}."
                )
            else:
                QMessageBox.warning(self._win, "Error", "Failed to update DB name.")

        elif action_name == "use_db":
            success = update_excel_name(ex["file_path"], ex["row_number"], db_fullname)
            if success:
                record["name_mismatch"] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(
                    self._win, "Success", f"Updated Excel file name to {db_fullname}."
                )
            else:
                QMessageBox.warning(
                    self._win, "Error", "Failed to update Excel file name."
                )

        elif action_name == "manual":
            name_str, ok = QInputDialog.getText(
                self._win,
                "Manual Correction",
                f"Enter correct name for {db_fullname} (Format: LASTNAME, FIRSTNAME MIDDLENAME):",  # noqa: E501
                text=ex_fullname,
            )
            if not ok or not name_str:
                return

            surname_dict = get_surname_dictionary()
            ln, fn, mn = split_beneficiary_name(name_str, surname_dict=surname_dict)
            if not ln or not fn:
                QMessageBox.warning(
                    self._win,
                    "Error",
                    "Invalid name format. Please use 'LASTNAME, FIRSTNAME MIDDLENAME'.",
                )
                return

            success_db = update_name_db(db["beneficiary_id"], ln, fn, mn)
            success_ex = update_excel_name(ex["file_path"], ex["row_number"], name_str)

            if success_db and success_ex:
                record["name_mismatch"] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(
                    self._win, "Success", f"Updated both DB and Excel to {name_str}."
                )
            else:
                QMessageBox.warning(
                    self._win,
                    "Error",
                    "Failed to fully update. Check console for details.",
                )

    def on_missing_excel_action(self, action: str, record: dict, widget: Any):
        if action != "delete_from_db":
            return

        from PySide6.QtWidgets import QMessageBox
        from core.database import delete_beneficiary_cascade
        from ui.auth_guard import require_permission

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
                    f"Failed to delete beneficiary {name}: {err}",
                )
                return

            record["_deleted_from_db"] = True
            widget.mark_as_resolved()
            self._win._audit(
                "delete_beneficiary",
                "beneficiary",
                entity_id=bid,
                details={"name": name},
            )
            QMessageBox.information(
                self._win,
                "Deleted",
                f"Successfully deleted {name} and related database records.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self._win,
                "Deletion Error",
                f"An error occurred while deleting {name}: {exc}",
            )

"""Bulk sync and bulk-correction controller extracted from MainWindow (R7).

Provides methods for bulk baseline sync, bulk birthday/name corrections.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox


class SyncController:
    def __init__(self, main_window):
        self._win = main_window

    def on_bulk_sync_exact(self):
        from core.database import sync_baseline
        from ui.auth_guard import require_permission

        if not require_permission(self._win, self._win.current_user, "bulk_sync"):
            return

        if not hasattr(self._win, 'exact_matches') or not self._win.exact_matches:
            return

        success_count = 0
        fail_count = 0

        self._win.btn_bulk_sync.setEnabled(False)
        self._win.btn_bulk_sync.setText("Syncing...")
        QApplication.processEvents()

        for record in self._win.exact_matches:
            ex = record['excel']
            db = record['db']

            weight = ex.get('weight') or db.get('weight')
            height = ex.get('height') or db.get('height')
            date_collected = ex.get('date_collected') or db.get('date_collected')
            birthday = ex.get('birthday') or db.get('birthday')

            if weight and height:
                success = sync_baseline(
                    beneficiary_id=db['beneficiary_id'],
                    weight=weight,
                    height=height,
                    date_collected=date_collected,
                    birthday=birthday,
                )
                if success:
                    record['baseline_mismatch'] = False
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1

        self._win.btn_bulk_sync.setEnabled(True)
        self._win.btn_bulk_sync.setText("Bulk Sync All Exact Matches")

        self._win.grid_exact.set_data(self._win.exact_matches, self._win.match_columns, action_label="Sync")

        if success_count:
            self._win._audit(
                "bulk_sync",
                "beneficiary",
                details={"count": success_count, "mode": "exact"},
            )
        QMessageBox.information(self._win, "Bulk Sync Complete", f"Successfully synced {success_count} matches.\nFailed/Skipped: {fail_count}")

    def _do_bulk_sync(self, match_list, btn, grid, label):
        from core.database import sync_baseline
        from ui.auth_guard import require_permission

        if not require_permission(self._win, self._win.current_user, "bulk_sync"):
            return

        if not match_list:
            return

        success_count = 0
        fail_count = 0

        btn.setEnabled(False)
        btn.setText("Syncing…")
        QApplication.processEvents()

        for record in match_list:
            ex = record['excel']
            db = record['db']

            weight = ex.get('weight') or db.get('weight')
            height = ex.get('height') or db.get('height')
            date_collected = ex.get('date_collected') or db.get('date_collected')
            birthday = ex.get('birthday') or db.get('birthday')

            if weight and height:
                success = sync_baseline(
                    beneficiary_id=db['beneficiary_id'],
                    weight=weight,
                    height=height,
                    date_collected=date_collected,
                    birthday=birthday,
                )
                if success:
                    record['baseline_mismatch'] = False
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1

        btn.setEnabled(True)
        btn.setText(label)

        grid.set_data(match_list, self._win.match_columns, action_label="Sync")

        if success_count:
            self._win._audit(
                "bulk_sync",
                "beneficiary",
                details={"count": success_count, "mode": label},
            )
        QMessageBox.information(self._win, "Bulk Sync Complete", f"Successfully synced {success_count} records.\nFailed/Skipped: {fail_count}")

    def on_bulk_sync_fuzzy(self):
        self._do_bulk_sync(
            match_list=getattr(self._win, 'fuzzy_matches', []),
            btn=self._win.btn_bulk_sync_fuzzy,
            grid=self._win.grid_fuzzy,
            label="⚡ Bulk Sync Baseline — High Confidence",
        )

    def on_bulk_sync_potential(self):
        self._do_bulk_sync(
            match_list=getattr(self._win, 'potential_matches', []),
            btn=self._win.btn_bulk_sync_potential,
            grid=self._win.grid_potential,
            label="⚡ Bulk Sync Baseline — Review Required",
        )

    def on_bulk_bday_use_excel(self):
        from core.database import update_birthday_db

        if not hasattr(self._win, 'bday_discrepancies') or not self._win.bday_discrepancies:
            return

        success_count, fail_count = 0, 0
        self._win.btn_bday_bulk_excel.setEnabled(False)
        self._win.btn_bday_bulk_db.setEnabled(False)
        self._win.btn_bday_bulk_excel.setText("Updating...")
        QApplication.processEvents()

        for record in self._win.bday_discrepancies:
            if not record.get('baseline_mismatch'):
                continue
            success = update_birthday_db(record['db']['beneficiary_id'], record['excel']['birthday'])
            if success:
                record['baseline_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1

        self._win.btn_bday_bulk_excel.setEnabled(True)
        self._win.btn_bday_bulk_db.setEnabled(True)
        self._win.btn_bday_bulk_excel.setText("Bulk Correct (Use Excel)")
        self._win.grid_bday.set_data(self._win.bday_discrepancies, self._win.match_columns, action_label="BirthdayActions")
        QMessageBox.information(self._win, "Complete", f"Successfully applied Excel birthdays to {success_count} records.")

    def on_bulk_bday_use_db(self):
        from core.excel_updater import update_excel_birthday

        if not hasattr(self._win, 'bday_discrepancies') or not self._win.bday_discrepancies:
            return

        success_count, fail_count = 0, 0
        self._win.btn_bday_bulk_excel.setEnabled(False)
        self._win.btn_bday_bulk_db.setEnabled(False)
        self._win.btn_bday_bulk_db.setText("Updating...")
        QApplication.processEvents()

        for record in self._win.bday_discrepancies:
            if not record.get('baseline_mismatch'):
                continue
            success = update_excel_birthday(record['excel']['file_path'], record['excel']['row_number'], record['db']['birthday'])
            if success:
                record['baseline_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1

        self._win.btn_bday_bulk_excel.setEnabled(True)
        self._win.btn_bday_bulk_db.setEnabled(True)
        self._win.btn_bday_bulk_db.setText("Bulk Correct (Use DB)")
        self._win.grid_bday.set_data(self._win.bday_discrepancies, self._win.match_columns, action_label="BirthdayActions")
        QMessageBox.information(self._win, "Complete", f"Successfully applied DB birthdays to {success_count} Excel records.")

    def on_bulk_name_use_excel(self):
        from core.database import update_name_db, get_surname_dictionary
        from core.parser import split_beneficiary_name

        if not hasattr(self._win, 'name_discrepancies') or not self._win.name_discrepancies:
            return

        success_count, fail_count = 0, 0
        self._win.btn_name_bulk_excel.setEnabled(False)
        self._win.btn_name_bulk_db.setEnabled(False)
        self._win.btn_name_bulk_excel.setText("Updating...")
        QApplication.processEvents()

        surname_dict = get_surname_dictionary()

        for record in self._win.name_discrepancies:
            if not record.get('name_mismatch'):
                continue
            ex_name = record['excel'].get('raw_name', '')
            ln, fn, mn = split_beneficiary_name(ex_name, surname_dict=surname_dict)
            success = update_name_db(record['db']['beneficiary_id'], ln, fn, mn)
            if success:
                record['name_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1

        self._win.btn_name_bulk_excel.setEnabled(True)
        self._win.btn_name_bulk_db.setEnabled(True)
        self._win.btn_name_bulk_excel.setText("Bulk Correct (Use Excel)")
        self._win.grid_name.set_data(self._win.name_discrepancies, self._win.name_match_columns, action_label="NameActions")
        QMessageBox.information(self._win, "Complete", f"Successfully applied Excel names to {success_count} DB records.")

    def on_bulk_name_use_db(self):
        from core.excel_updater import update_excel_name

        if not hasattr(self._win, 'name_discrepancies') or not self._win.name_discrepancies:
            return

        success_count, fail_count = 0, 0
        self._win.btn_name_bulk_excel.setEnabled(False)
        self._win.btn_name_bulk_db.setEnabled(False)
        self._win.btn_name_bulk_db.setText("Updating...")
        QApplication.processEvents()

        for record in self._win.name_discrepancies:
            if not record.get('name_mismatch'):
                continue

            db = record['db']
            db_fullname = f"{db.get('lastname', '')}, {db.get('firstname', '')}"
            if db.get('middlename'):
                db_fullname += f" {db.get('middlename')}"

            success = update_excel_name(record['excel']['file_path'], record['excel']['row_number'], db_fullname)
            if success:
                record['name_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1

        self._win.btn_name_bulk_excel.setEnabled(True)
        self._win.btn_name_bulk_db.setEnabled(True)
        self._win.btn_name_bulk_db.setText("Bulk Correct (Use DB)")
        self._win.grid_name.set_data(self._win.name_discrepancies, self._win.name_match_columns, action_label="NameActions")
        QMessageBox.information(self._win, "Complete", f"Successfully applied DB names to {success_count} Excel records.")

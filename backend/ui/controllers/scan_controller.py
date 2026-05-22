"""Scan controller: start scan, handle progress, and populate main window views.

Extracted from `ui/main_window.py` as part of R7 Phase 2.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox


class ScanController:
    def __init__(self, main_window):
        self._win = main_window
        self.worker = None

    def start_scan(self) -> None:
        if not getattr(self._win, 'selected_files', None):
            return
        self._win.btn_scan.setEnabled(False)
        self._win.progress_bar.setVisible(True)
        self._win.progress_bar.setValue(0)
        self._win.lbl_status.setText("Scanning...")
        self._win.console.clear()
        self._win.log_message("Scan started.")

        from ui.workers import ScanWorker

        self.worker = ScanWorker(self._win.selected_files, root_dir=self._win.file_explorer.model.rootPath())
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self._win.log_message)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        self.worker.start()

    def update_progress(self, val, msg):
        self._win.progress_bar.setValue(val)
        self._win.lbl_status.setText(msg)
        self._win.log_message(msg)

    def on_scan_finished(self, results):
        self._win.progress_bar.setVisible(False)
        self._win.lbl_status.setText("Scan Complete!")
        self._win.btn_scan.setEnabled(True)

        self._win.exact_matches = results.get("exact_matches", [])
        self._win.fuzzy_matches = results.get("fuzzy_matches", [])
        self._win.potential_matches = results.get("potential_matches", [])
        from ui.auth_guard import user_has_permission
        can_bulk = user_has_permission(self._win.current_user, "bulk_sync")
        self._win.btn_bulk_sync.setEnabled(can_bulk and len(self._win.exact_matches) > 0)
        self._win.btn_bulk_sync_fuzzy.setEnabled(can_bulk and len(self._win.fuzzy_matches) > 0)
        self._win.btn_bulk_sync_potential.setEnabled(can_bulk and len(self._win.potential_matches) > 0)

        # Populate Birthday Discrepancies
        self._win.bday_discrepancies = []
        for r in self._win.exact_matches + self._win.fuzzy_matches:
            if r.get('birthday_mismatch') == True:
                self._win.bday_discrepancies.append(r)

        self._win.btn_bday_bulk_excel.setEnabled(len(self._win.bday_discrepancies) > 0)
        self._win.btn_bday_bulk_db.setEnabled(len(self._win.bday_discrepancies) > 0)

        self._win.grid_bday.set_data(self._win.bday_discrepancies, self._win.match_columns, action_label="BirthdayActions")

        # Populate Name Discrepancies
        self._win.name_discrepancies = []
        for r in self._win.exact_matches + self._win.fuzzy_matches:
            if r.get('name_mismatch') == True:
                self._win.name_discrepancies.append(r)

        self._win.btn_name_bulk_excel.setEnabled(len(self._win.name_discrepancies) > 0)
        self._win.btn_name_bulk_db.setEnabled(len(self._win.name_discrepancies) > 0)

        self._win.grid_name.set_data(self._win.name_discrepancies, self._win.name_match_columns, action_label="NameActions")

        # Update Exact
        self._win.grid_exact.set_data(self._win.exact_matches, self._win.match_columns, action_label="Sync")
        self._win.tabs.setTabText(0, f"Exact Matches ({len(self._win.exact_matches)})")

        # Update Fuzzy
        self._win.grid_fuzzy.set_data(self._win.fuzzy_matches, self._win.match_columns, action_label="Sync")
        self._win.tabs.setTabText(1, f"High Confidence ({len(self._win.fuzzy_matches)})")

        # Update Potential
        self._win.grid_potential.set_data(self._win.potential_matches, self._win.match_columns, action_label="Resolve")
        self._win.tabs.setTabText(2, f"Review Required ({len(self._win.potential_matches)})")

        self._win.tabs.setTabText(3, f"Name Discrepancies ({len(self._win.name_discrepancies)})")
        self._win.tabs.setTabText(4, f"Birthday Discrepancies ({len(self._win.bday_discrepancies)})")

        # Update Missing
        missing_db_cols = [
            {"label": "Excel Name", "key": "raw_name"},
            {"label": "Birthday", "key": "birthday", "getter": lambda r: r.get('birthday')},
            {"label": "Gender", "key": "gender"},
            {"label": "Weight", "key": "weight"},
            {"label": "Height", "key": "height"},
        ]
        self._win.grid_missing_db.set_data(results.get("missing_in_db", []), missing_db_cols, action_label="MissingDbActions")
        self._win.tabs.setTabText(5, f"Missing in DB ({len(results.get('missing_in_db', []))})")

        missing_ex_cols = [
            {"label": "DB Name", "key": "fullname", "getter": lambda r: f"{r.get('lastname', '')}, {r.get('firstname', '')}"},
            {"label": "Birthday", "key": "birthday", "getter": lambda r: r.get('birthday')},
            {"label": "Site Name", "key": "site_name"},
            {"label": "Barangay", "key": "barangay_name"}
        ]
        self._win.grid_missing_excel.set_data(results.get("missing_in_excel", []), missing_ex_cols, action_label="MissingExcelActions")
        # ensure missing-excel actions connect
        try:
            self._win.grid_missing_excel.action_triggered.connect(self._win._on_missing_excel_action)
        except Exception:
            pass
        self._win.tabs.setTabText(6, f"Missing in Excel ({len(results.get('missing_in_excel', []))})")

        # Update Excel Duplicates
        duplicate_cols = [
            {"label": "Name", "key": "name"},
            {"label": "Duplicate Type", "key": "type"},
            {"label": "Birthday", "key": "birthday", "getter": lambda r: r.get('birthday')},
            {"label": "Detected In Files", "key": "files", "getter": lambda r: str(r.get('files', '')).replace(", ", ",\n")}
        ]
        excel_dupes = results.get("excel_duplicates", [])
        self._win._excel_dupes_list = excel_dupes
        self._win.grid_excel_duplicates.set_data(excel_dupes, duplicate_cols, action_label="ManageDup")
        self._win.tabs.setTabText(7, f"Excel Duplicates ({len(excel_dupes)})")

        # Update DB Duplicates
        db_duplicates_groups = []
        db_records = results.get("db_records", [])
        if db_records:
            from collections import defaultdict
            groups = defaultdict(list)
            for r in db_records:
                key = (str(r.get('lastname', '')).upper().strip(), str(r.get('firstname', '')).upper().strip())
                groups[key].append(r)
            for key, group in groups.items():
                if len(group) > 1:
                    name = f"{key[0]}, {key[1]}"
                    count = str(len(group))
                    birthdays = ",\n".join(sorted(list(set(r.get('birthday') for r in group if r.get('birthday')))))
                    sites = ",\n".join(sorted(list(set(str(r.get('site_name', '—')) for r in group))))
                    db_duplicates_groups.append({
                        "name": name,
                        "count": count,
                        "birthdays": birthdays,
                        "sites": sites,
                        "records": group
                    })
        self._win.grid_db_duplicates.set_data(db_duplicates_groups, self._win.db_duplicate_columns, action_label="ManageDup")
        self._win.tabs.setTabText(8, f"DB Duplicates ({len(db_duplicates_groups)})")

    def on_scan_error(self, err_msg):
        self._win.progress_bar.setVisible(False)
        self._win.lbl_status.setText(f"Error: {err_msg}")
        self._win.btn_scan.setEnabled(True)

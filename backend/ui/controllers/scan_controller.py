"""File selection, scan worker, and results tab population (R7)."""

from __future__ import annotations

import os
import sys
from collections import defaultdict

from PySide6.QtWidgets import QFileDialog, QMessageBox

from ui.format_utils import format_display_date
from ui.workers import ScanWorker


class ScanController:
    """Handles directory browsing, scanning, and populating result grids."""

    def __init__(self, main_window):
        self._win = main_window
        self._worker = None

    @property
    def win(self):
        return self._win

    def on_files_selected(self, files):
        self._win.selected_files = files
        self._win.btn_scan.setEnabled(len(files) > 0)
        self._win.btn_scan.setText(f"Scan Selected Files ({len(files)})")

    def on_browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(
            self._win,
            "Select Directory containing Excel Files",
            self._win.file_explorer.model.rootPath(),
        )
        if dir_path:
            self._win.file_explorer.set_root_path(dir_path)

    def on_rebuild_index(self):
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
        cache_path = os.path.join(base, "interfile_index_cache.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            self._win.log_message(
                "🗂 Inter-file index cache cleared. It will be rebuilt on the next scan."
            )
            QMessageBox.information(
                self._win,
                "Index Cleared",
                "The inter-file duplicate index cache has been cleared.\n"
                "It will be rebuilt automatically on the next scan.",
            )
        else:
            QMessageBox.information(
                self._win,
                "No Cache",
                "No cached index found. The index will be built fresh on the next scan.",  # noqa: E501
            )

    def start_scan(self):
        if not self._win.selected_files:
            return
        self._win.btn_scan.setEnabled(False)
        self._win.progress_bar.setVisible(True)
        self._win.progress_bar.setValue(0)
        self._win.lbl_status.setText("Scanning...")
        self._win.console.clear()
        self._win.log_message("Scan started.")

        self._worker = ScanWorker(
            self._win.selected_files,
            root_dir=self._win.file_explorer.model.rootPath(),
        )
        self._worker.progress.connect(self.update_progress)
        self._worker.log.connect(self._win.log_message)
        self._worker.finished.connect(self.on_scan_finished)
        self._worker.error.connect(self.on_scan_error)
        self._worker.start()
        self._win.worker = self._worker

    def update_progress(self, val, msg):
        self._win.progress_bar.setValue(val)
        self._win.lbl_status.setText(msg)
        self._win.log_message(msg)

    def on_scan_finished(self, results):
        win = self._win
        win.progress_bar.setVisible(False)
        win.lbl_status.setText("Scan Complete!")
        win.btn_scan.setEnabled(True)

        win.exact_matches = results.get("exact_matches", [])
        win.fuzzy_matches = results.get("fuzzy_matches", [])
        win.potential_matches = results.get("potential_matches", [])

        from ui.auth_guard import user_has_permission

        can_bulk = user_has_permission(win.current_user, "bulk_sync")
        win.btn_bulk_sync.setEnabled(can_bulk and len(win.exact_matches) > 0)
        win.btn_bulk_sync_fuzzy.setEnabled(can_bulk and len(win.fuzzy_matches) > 0)
        win.btn_bulk_sync_potential.setEnabled(
            can_bulk and len(win.potential_matches) > 0
        )

        win.bday_discrepancies = []
        for r in win.exact_matches + win.fuzzy_matches:
            if r.get("birthday_mismatch") is True:
                win.bday_discrepancies.append(r)

        win.btn_bday_bulk_excel.setEnabled(len(win.bday_discrepancies) > 0)
        win.btn_bday_bulk_db.setEnabled(len(win.bday_discrepancies) > 0)
        win.grid_bday.set_data(
            win.bday_discrepancies, win.match_columns, action_label="BirthdayActions"
        )

        win.name_discrepancies = []
        for r in win.exact_matches + win.fuzzy_matches:
            if r.get("name_mismatch") is True:
                win.name_discrepancies.append(r)

        win.btn_name_bulk_excel.setEnabled(len(win.name_discrepancies) > 0)
        win.btn_name_bulk_db.setEnabled(len(win.name_discrepancies) > 0)
        win.grid_name.set_data(
            win.name_discrepancies, win.name_match_columns, action_label="NameActions"
        )

        win.grid_exact.set_data(
            win.exact_matches, win.match_columns, action_label="Sync"
        )
        win.tabs.setTabText(0, f"Exact Matches ({len(win.exact_matches)})")

        win.grid_fuzzy.set_data(
            win.fuzzy_matches, win.match_columns, action_label="Sync"
        )
        win.tabs.setTabText(1, f"High Confidence ({len(win.fuzzy_matches)})")

        win.grid_potential.set_data(
            win.potential_matches, win.match_columns, action_label="Resolve"
        )
        win.tabs.setTabText(2, f"Review Required ({len(win.potential_matches)})")

        win.tabs.setTabText(3, f"Name Discrepancies ({len(win.name_discrepancies)})")
        win.tabs.setTabText(
            4, f"Birthday Discrepancies ({len(win.bday_discrepancies)})"
        )

        missing_db_cols = [
            {"label": "Excel Name", "key": "raw_name"},
            {
                "label": "Birthday",
                "key": "birthday",
                "getter": lambda r: format_display_date(r.get("birthday")),
            },
            {"label": "Gender", "key": "gender"},
            {"label": "Weight", "key": "weight"},
            {"label": "Height", "key": "height"},
        ]
        missing_in_db = results.get("missing_in_db", [])
        win.grid_missing_db.set_data(
            missing_in_db, missing_db_cols, action_label="MissingDbActions"
        )
        win.tabs.setTabText(5, f"Missing in DB ({len(missing_in_db)})")

        missing_ex_cols = [
            {
                "label": "DB Name",
                "key": "fullname",
                "getter": lambda r: (
                    f"{r.get('lastname', '')}, {r.get('firstname', '')}"
                ),
            },
            {
                "label": "Birthday",
                "key": "birthday",
                "getter": lambda r: format_display_date(r.get("birthday")),
            },
            {"label": "Site Name", "key": "site_name"},
            {"label": "Barangay", "key": "barangay_name"},
        ]
        missing_in_excel = results.get("missing_in_excel", [])
        win.grid_missing_excel.set_data(
            missing_in_excel, missing_ex_cols, action_label="MissingExcelActions"
        )
        win.tabs.setTabText(6, f"Missing in Excel ({len(missing_in_excel)})")

        duplicate_cols = [
            {"label": "Name", "key": "name"},
            {"label": "Duplicate Type", "key": "type"},
            {
                "label": "Birthday",
                "key": "birthday",
                "getter": lambda r: format_display_date(r.get("birthday")),
            },
            {
                "label": "Detected In Files",
                "key": "files",
                "getter": lambda r: str(r.get("files", "")).replace(", ", ",\n"),
            },
        ]
        excel_dupes = results.get("excel_duplicates", [])
        win._excel_dupes_list = excel_dupes
        win.grid_excel_duplicates.set_data(
            excel_dupes, duplicate_cols, action_label="ManageDup"
        )
        win.tabs.setTabText(7, f"Excel Duplicates ({len(excel_dupes)})")

        db_duplicates_groups = []
        db_records = results.get("db_records", [])
        if db_records:
            groups = defaultdict(list)
            for r in db_records:
                key = (
                    str(r.get("lastname", "")).upper().strip(),
                    str(r.get("firstname", "")).upper().strip(),
                )
                groups[key].append(r)
            for key, group in groups.items():
                if len(group) > 1:
                    name = f"{key[0]}, {key[1]}"
                    count = str(len(group))
                    birthdays = ",\n".join(
                        sorted(
                            list(
                                set(
                                    format_display_date(r.get("birthday"))
                                    for r in group
                                    if r.get("birthday")
                                )
                            )
                        )
                    )
                    sites = ",\n".join(
                        sorted(list(set(str(r.get("site_name", "—")) for r in group)))
                    )
                    db_duplicates_groups.append(
                        {
                            "name": name,
                            "count": count,
                            "birthdays": birthdays,
                            "sites": sites,
                            "records": group,
                        }
                    )
        win.grid_db_duplicates.set_data(
            db_duplicates_groups, win.db_duplicate_columns, action_label="ManageDup"
        )
        win.tabs.setTabText(8, f"DB Duplicates ({len(db_duplicates_groups)})")

    def on_scan_error(self, err_msg):
        self._win.progress_bar.setVisible(False)
        self._win.lbl_status.setText(f"Error: {err_msg}")
        self._win.btn_scan.setEnabled(True)

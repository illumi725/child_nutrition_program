"""Controller for file explorer and index management actions."""
from __future__ import annotations


class FileExplorerController:
    def __init__(self, main_window):
        self._win = main_window

    def on_files_selected(self, files):
        self._win.selected_files = files
        self._win.btn_scan.setEnabled(len(files) > 0)
        self._win.btn_scan.setText(f"Scan Selected Files ({len(files)})")

    def on_browse_folder(self):
        from PySide6.QtWidgets import QFileDialog

        dir_path = QFileDialog.getExistingDirectory(
            self._win,
            "Select Directory containing Excel Files",
            self._win.file_explorer.model.rootPath(),
        )
        if dir_path:
            self._win.file_explorer.set_root_path(dir_path)

    def on_rebuild_index(self):
        from PySide6.QtWidgets import QMessageBox
        import sys
        import os

        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cache_path = os.path.join(base, "interfile_index_cache.json")

        if os.path.exists(cache_path):
            os.remove(cache_path)
            self._win.log_message("🗂 Inter-file index cache cleared. It will be rebuilt on the next scan.")
            QMessageBox.information(
                self._win,
                "Index Cleared",
                "The inter-file duplicate index cache has been cleared.\nIt will be rebuilt automatically on the next scan.",
            )
        else:
            QMessageBox.information(
                self._win,
                "No Cache",
                "No cached index found. The index will be built fresh on the next scan.",
            )

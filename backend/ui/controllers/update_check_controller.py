"""Controller for update checks (background and manual) extracted from UpdateController."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressDialog, QMessageBox

from typing import Any


class UpdateCheckController:
    def __init__(self, main_window):
        self._win = main_window
        self._bg_thread = None
        self._manual_thread = None
        self._manual_progress = None

    def start_background_check(self) -> None:
        import os

        if os.environ.get("HAPAG_DISABLE_AUTO_UPDATE") == "1":
            return
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return

        from core.updater import UpdateCheckThread

        self._bg_thread = UpdateCheckThread(self._win)
        self._bg_thread.update_available.connect(self.on_update_available)
        self._bg_thread.start()

    def on_update_available(
        self,
        latest_version,
        release_notes,
        html_url,
        download_url,
        expected_sha256="",
    ):
        from PySide6.QtWidgets import QMessageBox
        from ui.controllers.update_download_controller import UpdateProgressDialog

        reply = QMessageBox.question(
            self._win,
            "Update Available",
            f"A new version of the application ({latest_version}) is available!\n\n"
            f"Would you like to install it automatically now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            dialog = UpdateProgressDialog(
                download_url,
                latest_version,
                self._win,
                expected_sha256=expected_sha256 or None,
            )
            dialog.exec()

    def check_for_updates_manual(self) -> None:
        from core.updater import UpdateCheckThread
        from core.version import APP_VERSION
        from ui.controllers.update_download_controller import UpdateProgressDialog

        self._manual_progress = QProgressDialog(
            "Checking for updates...\nConnecting to GitHub server...",
            "Cancel",
            0,
            0,
            self._win,
        )
        self._manual_progress.setWindowTitle("Check for Updates")
        self._manual_progress.setWindowModality(Qt.WindowModal)
        self._manual_progress.setMinimumDuration(0)
        self._manual_progress.show()

        self._manual_thread = UpdateCheckThread(self._win)

        def on_avail(tag, body, html_url, download_url, expected_sha256=""):
            self._manual_progress.close()
            self.on_update_available(tag, body, html_url, download_url, expected_sha256)

        def on_uptodate():
            self._manual_progress.close()
            QMessageBox.information(
                self._win,
                "App Up to Date",
                f"You are running the latest version: {APP_VERSION}.\n"
                "No updates are available at this time.",
            )

        def on_error(err_msg):
            self._manual_progress.close()
            QMessageBox.warning(
                self._win,
                "Check Failed",
                f"Failed to check for updates:\n{err_msg}",
            )

        def on_cancel():
            if not self._manual_thread:
                return
            try:
                self._manual_thread.update_available.disconnect()
                self._manual_thread.up_to_date.disconnect()
                self._manual_thread.error_occurred.disconnect()
            except (RuntimeError, TypeError):
                pass

        self._manual_thread.update_available.connect(on_avail)
        self._manual_thread.up_to_date.connect(on_uptodate)
        self._manual_thread.error_occurred.connect(on_error)
        self._manual_progress.canceled.connect(on_cancel)
        self._manual_thread.start()

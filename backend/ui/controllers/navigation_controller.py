"""Controller for main window navigation and UI action wiring."""

from __future__ import annotations


class NavigationController:
    def __init__(self, main_window):
        self._win = main_window

    def apply_action_permissions(self):
        from ui.auth_guard import user_has_permission

        user = self._win.current_user
        can_bulk = user_has_permission(user, "bulk_sync")
        can_transfer = user_has_permission(user, "bulk_transfer")

        self._win.btn_bulk_transfer.setEnabled(can_transfer)
        self._win.btn_bulk_transfer.setToolTip(
            "" if can_transfer else "Your role cannot use bulk transfer."
        )

        for btn in (
            getattr(self._win, "btn_bulk_sync", None),
            getattr(self._win, "btn_bulk_sync_fuzzy", None),
            getattr(self._win, "btn_bulk_sync_potential", None),
        ):
            if btn and not can_bulk:
                btn.setEnabled(False)
                btn.setToolTip("Your role cannot run bulk baseline sync.")

    def open_dashboard(self):
        from ui.dashboard_window import DashboardWindow

        dash = DashboardWindow(self._win.file_explorer.model.rootPath(), self._win)
        dash.exec()

    def open_search(self):
        from ui.search_window import SearchBeneficiaryWindow

        search = SearchBeneficiaryWindow(self._win)
        search.exec()

    def open_bulk_transfer(self):
        from ui.bulk_transfer_window import BulkTransferWindow
        from ui.auth_guard import require_permission

        if not require_permission(self._win, self._win.current_user, "bulk_transfer"):
            return

        transfer = BulkTransferWindow(self._win)
        transfer.exec()

    def toggle_theme(self):
        from core.app_settings import get_theme, set_theme
        from ui.theme import apply_theme
        from PySide6.QtWidgets import QApplication

        current_theme = get_theme()
        new_theme = "dark" if current_theme == "light" else "light"
        set_theme(new_theme)

        btn_text = "☀️ Light" if new_theme == "dark" else "🌙 Dark"
        self._win.btn_theme_toggle.setText(btn_text)

        apply_theme(QApplication.instance(), new_theme)

    def open_settings(self):
        from ui.components.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._win)
        dlg.exec()

        user_display = (
            (
                f"{self._win.current_user['firstname']} {self._win.current_user['lastname']} "  # noqa: E501
                f"({self._win.current_user['role']})"
            )
            if self._win.current_user
            else "Unknown User"
        )
        self._win._update_window_title(user_display)
        self._win.auto_sync_controller.start_auto_sync_timer()

    def open_about(self):
        from PySide6.QtWidgets import QMessageBox
        import datetime

        try:
            from core.version import APP_VERSION, APP_RELEASE_DATE
        except ImportError:
            from core.version import APP_VERSION

            APP_RELEASE_DATE = datetime.date.today().strftime("%B %d, %Y")

        current_year = datetime.date.today().year
        about_text = (
            "HAPAG Form 5A Comparator\n\n"
            f"Version: {APP_VERSION}\n"
            f"Update Date: {APP_RELEASE_DATE}\n\n"
            "Developed By: Jhay [06194]\n"
            "Agile Transformation Office\n\n"
            "ASA Philippines Foundation, Inc. (A Microfinance NGO)\n\n"
            f"All Rights Reserved. © {current_year}"
        )

        msg_box = QMessageBox(self._win)
        msg_box.setWindowTitle("About HAPAG Form 5A Comparator")
        msg_box.setText(about_text)
        msg_box.setIcon(QMessageBox.Information)

        btn_check = msg_box.addButton("Check for Updates", QMessageBox.ActionRole)
        msg_box.addButton(QMessageBox.Close)

        msg_box.exec()

        if msg_box.clickedButton() == btn_check:
            self._win.update_controller.check_for_updates_manual()

    def open_user_manual(self):
        from ui.main_window import UserManualBrowser

        dlg = UserManualBrowser(self._win)
        dlg.exec()

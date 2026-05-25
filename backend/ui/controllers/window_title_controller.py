"""Controller for updating the main window title."""

from __future__ import annotations


class WindowTitleController:
    def __init__(self, main_window):
        self._win = main_window

    def update_title(self, user_display: str) -> None:
        from core.app_settings import get_mode

        mode_tag = "☁ CLOUD" if get_mode() == "cloud" else "💾 LOCAL"
        self._win.setWindowTitle(
            f"HAPAG Form 5A Comparator [{mode_tag}] — {user_display}"
        )

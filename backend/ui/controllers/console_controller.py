"""Controller for console log and toggle behavior."""

from __future__ import annotations


class ConsoleController:
    def __init__(self, main_window):
        self._win = main_window

    def toggle_console(self, checked):
        self._win.console.setVisible(checked)
        self._win.btn_console_toggle.setText(
            ("▼" if checked else "▶") + "  Console Log"
        )

    def log_message(self, msg):
        import datetime

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._win.console.appendPlainText(f"[{ts}]  {msg}")

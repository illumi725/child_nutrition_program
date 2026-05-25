"""Unit tests for ConsoleController."""

from __future__ import annotations

from ui.controllers.console_controller import ConsoleController


class DummyConsole:
    def __init__(self):
        self.visible = False
        self.text = ""

    def setVisible(self, visible):
        self.visible = visible

    def appendPlainText(self, text):
        self.text = text


class DummyButton:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class DummyWindow:
    def __init__(self):
        self.console = DummyConsole()
        self.btn_console_toggle = DummyButton()


def test_console_toggle_and_log_message():
    win = DummyWindow()
    ctrl = ConsoleController(win)
    ctrl.toggle_console(True)

    assert win.console.visible is True
    assert win.btn_console_toggle.text.startswith("▼")

    ctrl.log_message("hello world")
    assert win.console.text.endswith("hello world")
    assert win.console.text.startswith("[")

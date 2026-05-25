"""Unit tests for FileExplorerController."""

from __future__ import annotations

import os
import sys
import types

import pytest

from ui.controllers.file_explorer_controller import FileExplorerController


class FakeFileDialog:
    last_parent = None
    last_title = None
    last_dir = None
    return_path = ""

    @staticmethod
    def getExistingDirectory(parent, title, dir_path):
        FakeFileDialog.last_parent = parent
        FakeFileDialog.last_title = title
        FakeFileDialog.last_dir = dir_path
        return FakeFileDialog.return_path


class FakeMessageBox:
    last_args = None

    @staticmethod
    def information(parent, title, message):
        FakeMessageBox.last_args = (parent, title, message)


class DummyButton:
    def __init__(self):
        self.enabled = False
        self.text = ""

    def setEnabled(self, value):
        self.enabled = value

    def setText(self, text):
        self.text = text


class DummyExplorer:
    def __init__(self):
        self.root_path = "/tmp/root"

    class model:
        @staticmethod
        def rootPath():
            return "/tmp/root"

    def set_root_path(self, path):
        self.root_path = path


class DummyMainWindow:
    def __init__(self):
        self.selected_files = []
        self.file_explorer = DummyExplorer()
        self.btn_scan = DummyButton()
        self.logs = []

    def log_message(self, msg):
        self.logs.append(msg)


@pytest.fixture
def file_explorer_env(monkeypatch):
    qt_widgets = types.ModuleType("PySide6.QtWidgets")
    qt_widgets.QFileDialog = FakeFileDialog
    qt_widgets.QMessageBox = FakeMessageBox
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qt_widgets)


def test_on_files_selected(file_explorer_env):
    win = DummyMainWindow()
    ctrl = FileExplorerController(win)
    ctrl.on_files_selected(["a.xlsx", "b.xlsx"])

    assert win.selected_files == ["a.xlsx", "b.xlsx"]
    assert win.btn_scan.enabled is True
    assert "2" in win.btn_scan.text


def test_on_browse_folder(file_explorer_env):
    win = DummyMainWindow()
    ctrl = FileExplorerController(win)
    FakeFileDialog.return_path = "/new/path"
    ctrl.on_browse_folder()

    assert win.file_explorer.root_path == "/new/path"


def test_on_rebuild_index_clears_cache(file_explorer_env):

    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cache = os.path.join(backend_root, "interfile_index_cache.json")
    try:
        with open(cache, "w", encoding="utf-8") as f:
            f.write("{}")

        win = DummyMainWindow()
        ctrl = FileExplorerController(win)
        ctrl.on_rebuild_index()

        assert not os.path.exists(cache)
        assert FakeMessageBox.last_args is not None
    finally:
        if os.path.exists(cache):
            os.remove(cache)

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


def test_main_window_starts_offscreen():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication
    from backend.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(current_user={
        "firstname": "Test",
        "lastname": "User",
        "role": "admin",
        "user_id": 1,
    })

    assert window is not None
    assert "HAPAG Form 5A Comparator" in window.windowTitle()

    window.close()


def test_main_window_layout_and_update_controller_wiring():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication
    from backend.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(current_user={
        "firstname": "Test",
        "lastname": "User",
        "role": "admin",
        "user_id": 1,
    })

    assert hasattr(window, "layout_controller")
    assert hasattr(window, "record_action_controller")
    assert hasattr(window, "duplicate_controller")
    assert window.btn_scan is not None
    assert window.btn_settings is not None
    assert window.tabs is not None
    assert window.grid_exact is not None
    assert window.grid_name is not None

    # Background auto-update should not start in offscreen mode.
    assert window.update_controller._bg_thread is None

    window.close()

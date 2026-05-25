"""Integration smoke tests for MainWindow refactor wiring."""

from __future__ import annotations

import inspect


from ui.main_window import MainWindow

EXPECTED_CONTROLLERS = (
    "layout_controller",
    "audit_controller",
    "console_controller",
    "window_title_controller",
    "navigation_controller",
    "auto_sync_controller",
    "duplicate_controller",
    "resolution_controller",
    "record_action_controller",
    "scan_controller",
    "sync_controller",
    "update_controller",
)


def _make_window() -> MainWindow:
    return MainWindow(
        current_user={
            "firstname": "Test",
            "lastname": "User",
            "role": "admin",
            "user_id": 1,
        }
    )


def test_main_window_starts_offscreen(qapp):
    window = _make_window()

    assert window is not None
    assert "HAPAG Form 5A Comparator" in window.windowTitle()

    window.close()


def test_main_window_controllers_and_wiring(qapp):
    window = _make_window()

    for name in EXPECTED_CONTROLLERS:
        assert hasattr(window, name), f"Missing controller: {name}"
        assert getattr(window, name) is not None

    assert window.btn_scan is not None
    assert window.btn_settings is not None
    assert window.tabs is not None
    assert window.grid_exact is not None
    assert window.grid_name is not None

    # Background update check is skipped in tests (HAPAG_SKIP_BACKGROUND_UPDATE).
    assert window.update_controller._bg_thread is None

    window.close()


def test_scan_and_resolution_controllers_are_wired(qapp):
    window = _make_window()

    assert window.scan_controller is not None
    assert callable(window.scan_controller.on_browse_folder)
    assert callable(window.scan_controller.start_scan)
    assert window.resolution_controller is not None
    assert callable(window.resolution_controller.on_missing_db_action)
    assert callable(window.resolution_controller.on_missing_excel_action)

    window.close()


def test_main_window_delegates_audit_and_log(qapp):
    window = _make_window()

    assert callable(window._audit)
    assert callable(window.log_message)
    assert inspect.ismethod(window._update_window_title) or callable(
        window._update_window_title
    )

    window.close()

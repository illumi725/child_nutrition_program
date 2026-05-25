"""Controller for auto-sync timer and background sync logic."""
from __future__ import annotations


class AutoSyncController:
    def __init__(self, main_window):
        self._win = main_window
        self._timer = None

    def start_auto_sync_timer(self):
        from PySide6.QtCore import QTimer
        from core.app_settings import get_mode, get_auto_sync_enabled, get_auto_sync_interval

        if self._timer:
            self._timer.stop()
            self._timer = None

        if get_mode() != 'local' or not get_auto_sync_enabled():
            return

        interval_ms = get_auto_sync_interval() * 60 * 1000
        self._timer = QTimer(self._win)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.run_background_sync)
        self._timer.start()
        self._win.log_message(f"🔄 Auto-sync enabled every {get_auto_sync_interval()} min.")

    def run_background_sync(self):
        from core.sync_engine import SyncWorker

        self._win.log_message("🔄 Auto-sync started...")
        worker = SyncWorker(mode=SyncWorker.MODE_SYNC, parent=self._win)
        worker.finished.connect(lambda ok, msg: self._win.log_message(f"🔄 Auto-sync: {msg}"))
        worker.error.connect(lambda e: self._win.log_message(f"⚠ Auto-sync error: {e}"))
        worker.start()

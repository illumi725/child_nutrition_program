"""Controller for settings dialog sync actions.

Moves the sync worker lifecycle out of the UI dialog so it is testable.
"""
from __future__ import annotations

from typing import Optional


class SettingsController:
    def __init__(self, dialog):
        self.dialog = dialog
        self._sync_worker = None

    def start_sync(self, mode: str):
        from core.sync_engine import SyncWorker

        if self._sync_worker and getattr(self._sync_worker, 'isRunning', lambda: False)():
            return

        dlg = self.dialog
        dlg.progress_bar.setVisible(True)
        dlg.progress_bar.setValue(0)
        dlg.lbl_progress_msg.setVisible(True)
        dlg.btn_sync_now.setEnabled(False)
        dlg.btn_full_replicate.setEnabled(False)
        dlg.btn_save.setEnabled(False)

        worker_mode = SyncWorker.MODE_FULL if mode == 'full' else SyncWorker.MODE_SYNC
        self._sync_worker = SyncWorker(mode=worker_mode, parent=dlg)
        # hook up to dialog handlers (keeps UI methods intact)
        try:
            self._sync_worker.progress.connect(dlg._on_progress)
            self._sync_worker.finished.connect(dlg._on_finished)
            self._sync_worker.error.connect(dlg._on_error)
        except Exception:
            pass
        self._sync_worker.start()

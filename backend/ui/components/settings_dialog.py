from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QRadioButton, QProgressBar, QSpinBox, QCheckBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._sync_worker = None
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ── Database Mode ──────────────────────────────────────────────────
        mode_box = QGroupBox("Database Mode")
        mode_layout = QVBoxLayout(mode_box)

        self.rb_cloud = QRadioButton("☁  Cloud Mode  —  Always connects to the production database in real time")
        self.rb_local = QRadioButton("💾  Local Mode  —  Uses a local SQLite snapshot (works offline)")
        mode_layout.addWidget(self.rb_cloud)
        mode_layout.addWidget(self.rb_local)

        mode_note = QLabel("⚠  A restart is required after switching modes.")
        mode_note.setStyleSheet("color: #e67e22; font-size: 11px;")
        mode_layout.addWidget(mode_note)
        layout.addWidget(mode_box)

        # ── Sync Controls ──────────────────────────────────────────────────
        sync_box = QGroupBox("Sync Controls  (Local Mode)")
        sync_layout = QVBoxLayout(sync_box)

        self.lbl_last_sync = QLabel("Last Sync: —")
        self.lbl_last_sync.setStyleSheet("color: grey; font-size: 11px;")
        sync_layout.addWidget(self.lbl_last_sync)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        sync_layout.addWidget(self.progress_bar)

        self.lbl_progress_msg = QLabel("")
        self.lbl_progress_msg.setStyleSheet("color: grey; font-size: 11px;")
        self.lbl_progress_msg.setVisible(False)
        sync_layout.addWidget(self.lbl_progress_msg)

        btn_row = QHBoxLayout()
        self.btn_sync_now = QPushButton("⟳  Sync Now (Delta)")
        self.btn_sync_now.setToolTip("Sync only changed rows since last sync")
        self.btn_sync_now.clicked.connect(self._run_sync)
        self.btn_full_replicate = QPushButton("⬇  Full Replication")
        self.btn_full_replicate.setToolTip("Wipe and re-download ALL data from cloud (first-run setup)")
        self.btn_full_replicate.clicked.connect(self._run_full_replicate)
        btn_row.addWidget(self.btn_sync_now)
        btn_row.addWidget(self.btn_full_replicate)
        sync_layout.addLayout(btn_row)

        # Auto-sync
        auto_row = QHBoxLayout()
        self.chk_auto_sync = QCheckBox("Auto-sync every")
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(5, 1440)
        self.spin_interval.setSuffix(" min")
        auto_row.addWidget(self.chk_auto_sync)
        auto_row.addWidget(self.spin_interval)
        auto_row.addStretch()
        sync_layout.addLayout(auto_row)

        layout.addWidget(sync_box)

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        self.btn_save = QPushButton("Save & Close")

        self.btn_save.clicked.connect(self._save_and_close)
        btn_row2.addWidget(self.btn_save)
        layout.addLayout(btn_row2)

    def _load_settings(self):
        from core.app_settings import (get_mode, get_auto_sync_enabled,
                                       get_auto_sync_interval, get_last_synced)
        mode = get_mode()
        self.rb_cloud.setChecked(mode == 'cloud')
        self.rb_local.setChecked(mode == 'local')
        self.chk_auto_sync.setChecked(get_auto_sync_enabled())
        self.spin_interval.setValue(get_auto_sync_interval())
        self.lbl_last_sync.setText(f"Last Sync: {get_last_synced()}")

    def _save_and_close(self):
        from core.app_settings import (set_mode, set_auto_sync_enabled,
                                       set_auto_sync_interval, get_mode)
        old_mode = get_mode()
        new_mode = 'cloud' if self.rb_cloud.isChecked() else 'local'
        set_mode(new_mode)
        set_auto_sync_enabled(self.chk_auto_sync.isChecked())
        set_auto_sync_interval(self.spin_interval.value())

        if old_mode != new_mode:
            import sys
            import subprocess
            from PySide6.QtWidgets import QApplication

            QMessageBox.information(
                self,
                "Restarting Application",
                f"Mode switched to {'☁ Cloud' if new_mode == 'cloud' else '💾 Local'}.\n"
                "The application will now restart to apply this change."
            )
            
            # Close this dialog
            self.accept()
            
            # Formulate the restart command to support raw python and compiled PyInstaller executables
            args = sys.argv[:]
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable] + args[1:]
            else:
                cmd = [sys.executable] + args
                
            try:
                subprocess.Popen(cmd)
            except Exception as e:
                pass
                
            QApplication.quit()
        else:
            self.accept()

    def _run_sync(self):
        self._start_sync_worker(mode='sync')

    def _run_full_replicate(self):
        confirm = QMessageBox.question(self, "Full Replication",
            "This will wipe the local database and re-download ALL data from cloud.\n"
            "This may take several minutes. Continue?",
            QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self._start_sync_worker(mode='full')

    def _start_sync_worker(self, mode: str):
        from core.sync_engine import SyncWorker
        if self._sync_worker and self._sync_worker.isRunning():
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_progress_msg.setVisible(True)
        self.btn_sync_now.setEnabled(False)
        self.btn_full_replicate.setEnabled(False)
        self.btn_save.setEnabled(False)

        worker_mode = SyncWorker.MODE_FULL if mode == 'full' else SyncWorker.MODE_SYNC
        self._sync_worker = SyncWorker(mode=worker_mode, parent=self)
        self._sync_worker.progress.connect(self._on_progress)
        self._sync_worker.finished.connect(self._on_finished)
        self._sync_worker.error.connect(self._on_error)
        self._sync_worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_progress_msg.setText(msg)

    def _on_finished(self, success: bool, summary: str):
        from core.app_settings import get_last_synced
        self.progress_bar.setValue(100)
        self.lbl_last_sync.setText(f"Last Sync: {get_last_synced()}")
        self.lbl_progress_msg.setText(summary)
        self.btn_sync_now.setEnabled(True)
        self.btn_full_replicate.setEnabled(True)
        self.btn_save.setEnabled(True)
        if success:
            QMessageBox.information(self, "Sync Complete", summary)

    def _on_error(self, msg: str):
        self.lbl_progress_msg.setText(f"Error: {msg}")
        self.btn_sync_now.setEnabled(True)
        self.btn_full_replicate.setEnabled(True)
        self.btn_save.setEnabled(True)
        QMessageBox.critical(self, "Sync Error", msg)

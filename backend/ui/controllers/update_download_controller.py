"""Download dialog and handoff script for updates (extracted from UpdateController)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


class UpdateProgressDialog(QDialog):
    def __init__(self, download_url, latest_version, parent=None, expected_sha256=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Update")
        self.setFixedSize(400, 160)
        self.setModal(True)

        self.download_url = download_url
        self.latest_version = latest_version
        self.expected_sha256 = expected_sha256

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.lbl_title = QLabel(
            f"Downloading HAPAG Form 5A Comparator {latest_version}..."
        )
        self.lbl_title.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #2c3e50;"
        )

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.lbl_status = QLabel("Initializing download...")
        self.lbl_status.setStyleSheet("color: #7f8c8d; font-size: 11px;")

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.cancel_download)
        btn_layout.addWidget(self.btn_cancel)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_status)
        layout.addLayout(btn_layout)

        from core.updater import DownloadUpdateThread

        self.thread = DownloadUpdateThread(download_url, expected_sha256, self)
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def on_progress(self, pct, text):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(text)

    def cancel_download(self):
        self.thread.cancel()
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText("Cancelling...")

    def on_finished(self, extracted_dir, source_dir):
        self.lbl_status.setText("Download completed! Launching update script...")
        self.btn_cancel.setEnabled(False)
        self.run_handoff_script(source_dir)
        self.accept()

    def on_error(self, err_msg):
        QMessageBox.critical(
            self, "Update Error", f"Failed to download or apply update:\n{err_msg}"
        )
        self.reject()

    def run_handoff_script(self, source_dir):
        if getattr(sys, "frozen", False):
            target_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        temp_dir = tempfile.gettempdir()

        if sys.platform.startswith("win32"):
            script_path = os.path.join(temp_dir, "hapag_update.bat")
            exe_name = os.path.basename(sys.executable)
            script_content = f"""@echo off
:wait_loop
tasklist /FI "IMAGENAME eq {exe_name}" 2>NUL | find /I /N "{exe_name}">NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak > nul
    goto wait_loop
)
xcopy /s /e /y "{source_dir}\\*" "{target_dir}\\"
start "" "{sys.executable}"
del "%~f0"
"""
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            subprocess.Popen(
                ["cmd.exe", "/c", script_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            script_path = os.path.join(temp_dir, "hapag_update.sh")
            parent_pid = os.getpid()
            script_content = f"""#!/bin/bash
parent_pid={parent_pid}
while kill -0 "$parent_pid" 2>/dev/null; do
    sleep 0.5
done

cp -rf "{source_dir}/"* "{target_dir}/"
chmod +x "{sys.executable}"
"{sys.executable}" &
rm -- "$0"
"""
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)
            subprocess.Popen([script_path])

        QApplication.quit()
        sys.exit(0)

import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QSplitter, QTabWidget, QPushButton, QLabel, QProgressBar,
                               QApplication, QPlainTextEdit, QSizePolicy, QDialog)
from PySide6.QtCore import Qt, QTimer
from ui.components.file_explorer import FileExplorer
from ui.components.data_grid import ResultsDataGrid
from ui.workers import ScanWorker
from datetime import datetime

def format_display_date(date_val):
    if not date_val: return ""
    date_str = str(date_val).strip()
    try:
        # Assuming input is usually YYYY-MM-DD
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except:
        return date_str

class UpdateProgressDialog(QDialog):
    def __init__(self, download_url, latest_version, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Update")
        self.setFixedSize(400, 160)
        self.setModal(True)
        
        self.download_url = download_url
        self.latest_version = latest_version
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        self.lbl_title = QLabel(f"Downloading HAPAG Form 5A Comparator {latest_version}...")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #2c3e50;")
        
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
        self.thread = DownloadUpdateThread(download_url, self)
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
        
        # Execute Handoff Overwrite Update
        self.run_handoff_script(source_dir)
        self.accept()
        
    def on_error(self, err_msg):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Update Error", f"Failed to download or apply update:\n{err_msg}")
        self.reject()
        
    def run_handoff_script(self, source_dir):
        import sys
        import os
        import subprocess
        
        # Determine the target application directory
        if getattr(sys, 'frozen', False):
            target_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        if sys.platform.startswith('win32'):
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
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
                
            # Execute modelessly in a separate cmd process
            subprocess.Popen(["cmd.exe", "/c", script_path], creationflags=subprocess.CREATE_NO_WINDOW)
            
        else:
            # Linux and macOS
            script_path = os.path.join(temp_dir, "hapag_update.sh")
            parent_pid = os.getpid()
            
            script_content = f"""#!/bin/bash
parent_pid={parent_pid}
while kill -0 "$parent_pid" 2>/dev/null; do
    sleep 0.5
done

# Copy new files over
cp -rf "{source_dir}/"* "{target_dir}/"

# Grant executable permission to the newly copied executable
chmod +x "{sys.executable}"

# Relaunch the new application
"{sys.executable}" &

# Delete itself
rm -- "$0"
"""
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
                
            # Make the updater script itself executable
            os.chmod(script_path, 0o755)
            
            # Execute in the background
            subprocess.Popen([script_path])
            
        # Exit the current application immediately
        QApplication.quit()
        sys.exit(0)


class UserManualBrowser(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HAPAG Form 5A Comparator - User's Manual")
        self.resize(1000, 750)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtCore import QUrl
        
        self.web_view = QWebEngineView(self)
        layout.addWidget(self.web_view)
        
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        manual_path = os.path.join(base_dir, "manual.html")
        if os.path.exists(manual_path):
            self.web_view.setUrl(QUrl.fromLocalFile(manual_path))
        else:
            self.web_view.setHtml("<h3>User Manual file not found.</h3>")


class MainWindow(QMainWindow):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        user_display = f"{current_user['firstname']} {current_user['lastname']} ({current_user['role']})" if current_user else "Unknown User"
        self._update_window_title(user_display)
        self.resize(1200, 800)
        self._auto_sync_timer = None

        # Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header = QLabel("HAPAG Registration & Baseline Diagnostics")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            margin: 10px; 
            color: #2c3e50;
        """)
        main_layout.addWidget(header, 0) # stretch=0

        # Splitter for Sidebar and Main Content
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter, 1) # stretch=1

        # Left Sidebar (File Explorer + Actions)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "HAPAG APPROVED BASELINE"))
        if not os.path.exists(base_dir):
            base_dir = os.path.expanduser("~")
            
        self.file_explorer = FileExplorer(base_dir)
        self.file_explorer.files_selected.connect(self.on_files_selected)
        
        self.btn_browse = QPushButton("Browse Folder...")
        self.btn_browse.setStyleSheet("padding: 5px; background-color: #34495e; color: white;")
        self.btn_browse.clicked.connect(self.on_browse_folder)
        
        self.btn_scan = QPushButton("Scan Selected Files")
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self.start_scan)

        self.btn_rebuild_index = QPushButton("🗂 Rebuild Inter-file Index")
        self.btn_rebuild_index.setStyleSheet("padding: 4px; background-color: #7f8c8d; color: white; font-size: 11px;")
        self.btn_rebuild_index.setToolTip("Delete the cached inter-file duplicate index so it is rebuilt from scratch on the next scan.")
        self.btn_rebuild_index.clicked.connect(self.on_rebuild_index)

        left_layout.addWidget(QLabel("Local Directory Scanner"))
        left_layout.addWidget(self.btn_browse)
        left_layout.addWidget(self.file_explorer)
        left_layout.addWidget(self.btn_scan)
        left_layout.addWidget(self.btn_rebuild_index)


        self.splitter.addWidget(left_panel)

        # Right Panel (Results Tabs)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_header_layout = QHBoxLayout()
        self.btn_settings = QPushButton("⚙ Settings")
        self.btn_settings.setStyleSheet("background-color: #555; color: white; font-weight: bold; padding: 5px;")
        self.btn_settings.clicked.connect(self.open_settings)
        
        self.btn_about = QPushButton("ℹ️ About")
        self.btn_about.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; padding: 5px;")
        self.btn_about.clicked.connect(self.open_about)
        
        self.btn_manual = QPushButton("📖 User Manual")
        self.btn_manual.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 5px;")
        self.btn_manual.clicked.connect(self.open_user_manual)
        
        self.btn_dashboard = QPushButton("📊 System Dashboard")
        self.btn_dashboard.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 5px;")
        self.btn_dashboard.clicked.connect(self.open_dashboard)
        
        self.btn_search_beneficiary = QPushButton("🔍 Search Beneficiary")
        self.btn_search_beneficiary.setStyleSheet("background-color: #16a085; color: white; font-weight: bold; padding: 5px;")
        self.btn_search_beneficiary.clicked.connect(self.open_search)
        
        right_header_layout.addStretch()
        right_header_layout.addWidget(self.btn_search_beneficiary)
        right_header_layout.addWidget(self.btn_dashboard)
        right_header_layout.addWidget(self.btn_settings)
        right_header_layout.addWidget(self.btn_about)
        right_header_layout.addWidget(self.btn_manual)
        
        right_layout.addLayout(right_header_layout)

        self.tabs = QTabWidget()
        
        # Setup Data Grids
        self.grid_exact = ResultsDataGrid()
        self.grid_fuzzy = ResultsDataGrid()
        self.grid_potential = ResultsDataGrid()
        self.grid_missing_db = ResultsDataGrid()
        self.grid_bday = ResultsDataGrid()
        self.grid_name = ResultsDataGrid()
        
        self.grid_exact.action_triggered.connect(self.on_grid_action)
        self.grid_fuzzy.action_triggered.connect(self.on_grid_action)
        self.grid_potential.action_triggered.connect(self.on_grid_action)
        self.grid_bday.action_triggered.connect(self.on_bday_action)
        self.grid_name.action_triggered.connect(self.on_name_action)
        self.grid_missing_db.action_triggered.connect(self.on_missing_db_action)
        
        self.grid_missing_excel = ResultsDataGrid()
        self.grid_excel_duplicates = ResultsDataGrid()
        
        # Exact Matches Tab Widget with Bulk Sync Button
        self.exact_tab_widget = QWidget()
        exact_layout = QVBoxLayout(self.exact_tab_widget)
        exact_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_bulk_sync = QPushButton("Bulk Sync All Exact Matches")
        self.btn_bulk_sync.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 5px;")
        self.btn_bulk_sync.setEnabled(False)
        self.btn_bulk_sync.clicked.connect(self.on_bulk_sync_exact)
        
        exact_layout.addWidget(self.btn_bulk_sync)
        exact_layout.addWidget(self.grid_exact)

        self.tabs.addTab(self.exact_tab_widget, "Exact Matches (0)")
        self.tabs.addTab(self.grid_fuzzy, "High Confidence (0)")
        
        # Birthday Discrepancies Tab Widget
        self.bday_tab_widget = QWidget()
        bday_layout = QVBoxLayout(self.bday_tab_widget)
        bday_layout.setContentsMargins(0, 0, 0, 0)
        
        bday_btn_layout = QHBoxLayout()
        self.btn_bday_bulk_excel = QPushButton("Bulk Correct (Use Excel)")
        self.btn_bday_bulk_db = QPushButton("Bulk Correct (Use DB)")
        self.btn_bday_bulk_excel.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 5px;")
        self.btn_bday_bulk_db.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 5px;")
        
        self.btn_bday_bulk_excel.clicked.connect(self.on_bulk_bday_use_excel)
        self.btn_bday_bulk_db.clicked.connect(self.on_bulk_bday_use_db)
        self.btn_bday_bulk_excel.setEnabled(False)
        self.btn_bday_bulk_db.setEnabled(False)
        
        bday_btn_layout.addWidget(self.btn_bday_bulk_excel)
        bday_btn_layout.addWidget(self.btn_bday_bulk_db)
        
        bday_layout.addLayout(bday_btn_layout)
        bday_layout.addWidget(self.grid_bday)
        
        # Name Discrepancies Tab Widget
        self.name_tab_widget = QWidget()
        name_layout = QVBoxLayout(self.name_tab_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        
        name_btn_layout = QHBoxLayout()
        self.btn_name_bulk_excel = QPushButton("Bulk Correct (Use Excel)")
        self.btn_name_bulk_db = QPushButton("Bulk Correct (Use DB)")
        self.btn_name_bulk_excel.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 5px;")
        self.btn_name_bulk_db.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 5px;")
        
        self.btn_name_bulk_excel.clicked.connect(self.on_bulk_name_use_excel)
        self.btn_name_bulk_db.clicked.connect(self.on_bulk_name_use_db)
        self.btn_name_bulk_excel.setEnabled(False)
        self.btn_name_bulk_db.setEnabled(False)
        
        name_btn_layout.addWidget(self.btn_name_bulk_excel)
        name_btn_layout.addWidget(self.btn_name_bulk_db)
        
        name_layout.addLayout(name_btn_layout)
        name_layout.addWidget(self.grid_name)
        
        self.tabs.addTab(self.bday_tab_widget, "Birthday Discrepancies (0)")
        self.tabs.addTab(self.name_tab_widget, "Name Discrepancies (0)")
        self.tabs.addTab(self.grid_potential, "Review Required (0)")
        self.tabs.addTab(self.grid_missing_db, "Missing in DB (0)")
        self.tabs.addTab(self.grid_missing_excel, "Missing in Excel (0)")
        self.tabs.addTab(self.grid_excel_duplicates, "Excel Duplicates (0)")

        right_layout.addWidget(self.tabs)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.lbl_status = QLabel("Ready")
        right_layout.addWidget(self.progress_bar)
        right_layout.addWidget(self.lbl_status)

        # ── Collapsible Console ──────────────────────────────────────────────
        console_header = QHBoxLayout()
        self.btn_console_toggle = QPushButton("▶  Console Log")
        self.btn_console_toggle.setCheckable(True)
        self.btn_console_toggle.setChecked(False)
        self.btn_console_toggle.setStyleSheet("""
            QPushButton { background: #2c3e50; color: #ecf0f1;
                font-size: 11px; font-weight: bold; padding: 3px 8px;
                border: none; border-radius: 3px; text-align: left; }
            QPushButton:hover { background: #34495e; }
            QPushButton:checked { background: #1a252f; }
        """)
        self.btn_console_toggle.toggled.connect(self._toggle_console)
        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("font-size: 10px; padding: 2px 6px; color: #7f8c8d;")
        btn_clear.clicked.connect(lambda: self.console.clear())
        console_header.addWidget(self.btn_console_toggle)
        console_header.addStretch()
        console_header.addWidget(btn_clear)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(1000)  # keep last 1000 lines
        self.console.setVisible(False)
        self.console.setFixedHeight(140)
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background: #1e2a35; color: #a8d8a8;
                font-family: Consolas, monospace; font-size: 11px;
                border: none; padding: 4px;
            }
        """)

        right_layout.addLayout(console_header)
        right_layout.addWidget(self.console)

        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([300, 900])


        self.selected_files = []
        
        self.match_columns = [
            {"label": "Excel Name", "key": "excel.raw_name", "getter": lambda r: r['excel'].get('raw_name', '')},
            {"label": "DB Name", "key": "db.fullname", "getter": lambda r: f"{r['db'].get('lastname', '')}, {r['db'].get('firstname', '')} {r['db'].get('middlename', '')}".strip()},
            {"label": "Excel Bday", "key": "excel.birthday", "getter": lambda r: format_display_date(r['excel'].get('birthday'))},
            {"label": "DB Bday", "key": "db.birthday", "getter": lambda r: format_display_date(r['db'].get('birthday'))},
            {"label": "Excel Wt", "key": "excel.weight"},
            {"label": "DB Wt", "key": "db.weight"},
            {"label": "Excel Ht", "key": "excel.height"},
            {"label": "DB Ht", "key": "db.height"},
            {"label": "Excel Date", "key": "excel.date_collected", "getter": lambda r: format_display_date(r['excel'].get('date_collected'))},
            {"label": "DB Date", "key": "db.date_collected", "getter": lambda r: format_display_date(r['db'].get('date_collected'))},
            {"label": "Score", "key": "score"}
        ]
        
        self.name_match_columns = [
            {"label": "Excel Name", "key": "excel.raw_name", "getter": lambda r: r['excel'].get('raw_name', '')},
            {"label": "DB Lastname", "key": "db.lastname", "getter": lambda r: r['db'].get('lastname', '')},
            {"label": "DB Firstname", "key": "db.firstname", "getter": lambda r: r['db'].get('firstname', '')},
            {"label": "DB Middlename", "key": "db.middlename", "getter": lambda r: r['db'].get('middlename', '')},
            {"label": "Excel Bday", "key": "excel.birthday", "getter": lambda r: format_display_date(r['excel'].get('birthday'))},
            {"label": "DB Bday", "key": "db.birthday", "getter": lambda r: format_display_date(r['db'].get('birthday'))},
            {"label": "Excel Wt", "key": "excel.weight"},
            {"label": "DB Wt", "key": "db.weight"},
            {"label": "Excel Ht", "key": "excel.height"},
            {"label": "DB Ht", "key": "db.height"},
            {"label": "Excel Date", "key": "excel.date_collected", "getter": lambda r: format_display_date(r['excel'].get('date_collected'))},
            {"label": "DB Date", "key": "db.date_collected", "getter": lambda r: format_display_date(r['db'].get('date_collected'))},
            {"label": "Score", "key": "score"}
        ]

        # Start auto-sync if Local mode is active
        self._start_auto_sync_timer()
        
        # Setup Auto-Update Checker
        from core.updater import UpdateCheckThread
        self.updater_thread = UpdateCheckThread(self)
        self.updater_thread.update_available.connect(self.on_update_available)
        self.updater_thread.start()

    def on_update_available(self, latest_version, release_notes, html_url, download_url):
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Update Available",
            f"A new version of the application ({latest_version}) is available!\n\n"
            f"Would you like to install it automatically now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            dialog = UpdateProgressDialog(download_url, latest_version, self)
            dialog.exec()

    def on_grid_action(self, action_name, record, action_widget):
        from core.database import sync_baseline
        from PySide6.QtWidgets import QMessageBox
        
        if action_name in ["Sync", "Resolve"]:
            ex = record['excel']
            db = record['db']
            
            # Using excel baseline data, or fallback to DB if excel doesn't have it (or we could just use excel)
            weight = ex.get('weight') or db.get('weight')
            height = ex.get('height') or db.get('height')
            date_collected = ex.get('date_collected') or db.get('date_collected')
            birthday = ex.get('birthday') or db.get('birthday')
            
            if not weight or not height:
                QMessageBox.warning(self, "Missing Data", "Cannot sync: weight or height is missing.")
                return
                
            success = sync_baseline(
                beneficiary_id=db['beneficiary_id'], 
                weight=weight, 
                height=height, 
                date_collected=date_collected, 
                birthday=birthday
            )
            
            if success:
                action_widget.mark_as_synced()
                QMessageBox.information(self, "Success", f"Successfully synced baseline data for {db.get('lastname') + ', ' + db.get('firstname')}.")
            else:
                QMessageBox.warning(self, "Error", "Failed to sync baseline data. Check console for details.")

    def on_missing_db_action(self, action_name, record_data, action_widget):
        from core.database import add_beneficiary_to_db, get_sites
        from ui.components.edit_beneficiary_dialog import EditBeneficiaryDialog
        from PySide6.QtWidgets import QMessageBox
        
        if action_name == "add_to_db":
            sites = get_sites()
            if not sites:
                QMessageBox.warning(self, "Error", "No feeding sites found in the database. Cannot add.")
                return
                
            # Open Edit Dialog
            dialog = EditBeneficiaryDialog(record_data, sites, self)
            if dialog.exec():
                final_data = dialog.get_data()
                
                # Use current_user if available
                created_by = self.current_user['user_id'] if self.current_user else "system"
                
                success, msg = add_beneficiary_to_db(
                    site_id=final_data['site_id'],
                    lastname=final_data['lastname'],
                    firstname=final_data['firstname'],
                    middlename=final_data['middlename'],
                    birthday=final_data['birthday'],
                    gender=final_data['gender'],
                    weight=final_data['weight'],
                    height=final_data['height'],
                    date_collected=final_data['date_collected'],
                    created_by=created_by
                )
                
                if success:
                    record_data['_added_to_db'] = True
                    action_widget.mark_as_resolved()
                    QMessageBox.information(self, "Success", f"Successfully added {final_data['firstname']} to the database.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to add to database:\n{msg}")

    def on_bday_action(self, action_name, record, action_widget):
        from core.database import update_birthday_db
        from core.excel_updater import update_excel_birthday
        from PySide6.QtWidgets import QMessageBox, QInputDialog
        
        ex = record['excel']
        db = record['db']
        
        if action_name == "use_excel":
            success = update_birthday_db(db['beneficiary_id'], ex['birthday'])
            if success:
                record['baseline_mismatch'] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(self, "Success", f"Updated DB birthday to {ex['birthday']}.")
            else:
                QMessageBox.warning(self, "Error", "Failed to update DB birthday.")
                
        elif action_name == "use_db":
            success = update_excel_birthday(ex['file_path'], ex['row_number'], db['birthday'])
            if success:
                record['baseline_mismatch'] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(self, "Success", f"Updated Excel file birthday to {db['birthday']}.")
            else:
                QMessageBox.warning(self, "Error", "Failed to update Excel file birthday.")
                
        elif action_name == "manual":
            # Prompt user for a date
            date_str, ok = QInputDialog.getText(self, "Manual Correction", f"Enter correct birthday for {db['lastname']} (YYYY-MM-DD):", text=ex['birthday'] or db['birthday'])
            if ok and date_str:
                import re
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                    QMessageBox.warning(self, "Error", "Invalid date format. Please use YYYY-MM-DD.")
                    return
                    
                # Update both!
                success_db = update_birthday_db(db['beneficiary_id'], date_str)
                success_ex = update_excel_birthday(ex['file_path'], ex['row_number'], date_str)
                
                if success_db and success_ex:
                    record['baseline_mismatch'] = False
                    action_widget.mark_as_resolved()
                    QMessageBox.information(self, "Success", f"Updated both DB and Excel to {date_str}.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to fully update. Check console for details.")

    def on_name_action(self, action_name, record, action_widget):
        from core.database import update_name_db, get_surname_dictionary
        from core.excel_updater import update_excel_name
        from core.parser import split_beneficiary_name
        from PySide6.QtWidgets import QMessageBox, QInputDialog
        
        ex = record['excel']
        db = record['db']
        
        db_fullname = f"{db.get('lastname', '')}, {db.get('firstname', '')}"
        if db.get('middlename'):
            db_fullname += f" {db.get('middlename')}"
            
        ex_fullname = ex.get('raw_name', '')
        
        if action_name == "use_excel":
            surname_dict = get_surname_dictionary()
            ln, fn, mn = split_beneficiary_name(ex_fullname, surname_dict=surname_dict)
            success = update_name_db(db['beneficiary_id'], ln, fn, mn)
            if success:
                record['name_mismatch'] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(self, "Success", f"Updated DB name to {ex_fullname}.")
            else:
                QMessageBox.warning(self, "Error", "Failed to update DB name.")
                
        elif action_name == "use_db":
            success = update_excel_name(ex['file_path'], ex['row_number'], db_fullname)
            if success:
                record['name_mismatch'] = False
                action_widget.mark_as_resolved()
                QMessageBox.information(self, "Success", f"Updated Excel file name to {db_fullname}.")
            else:
                QMessageBox.warning(self, "Error", "Failed to update Excel file name.")
                
        elif action_name == "manual":
            # Prompt user for a name
            name_str, ok = QInputDialog.getText(self, "Manual Correction", f"Enter correct name for {db_fullname} (Format: LASTNAME, FIRSTNAME MIDDLENAME):", text=ex_fullname)
            if ok and name_str:
                surname_dict = get_surname_dictionary()
                ln, fn, mn = split_beneficiary_name(name_str, surname_dict=surname_dict)
                if not ln or not fn:
                    QMessageBox.warning(self, "Error", "Invalid name format. Please use 'LASTNAME, FIRSTNAME MIDDLENAME'.")
                    return
                    
                # Update both!
                success_db = update_name_db(db['beneficiary_id'], ln, fn, mn)
                success_ex = update_excel_name(ex['file_path'], ex['row_number'], name_str)
                
                if success_db and success_ex:
                    record['name_mismatch'] = False
                    action_widget.mark_as_resolved()
                    QMessageBox.information(self, "Success", f"Updated both DB and Excel to {name_str}.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to fully update. Check console for details.")

    def on_bulk_sync_exact(self):
        from core.database import sync_baseline
        from PySide6.QtWidgets import QMessageBox
        
        if not hasattr(self, 'exact_matches') or not self.exact_matches:
            return
            
        success_count = 0
        fail_count = 0
        
        self.btn_bulk_sync.setEnabled(False)
        self.btn_bulk_sync.setText("Syncing...")
        QApplication.processEvents() # Let the UI update
        
        for record in self.exact_matches:
            ex = record['excel']
            db = record['db']
            
            weight = ex.get('weight') or db.get('weight')
            height = ex.get('height') or db.get('height')
            date_collected = ex.get('date_collected') or db.get('date_collected')
            birthday = ex.get('birthday') or db.get('birthday')
            
            if weight and height:
                success = sync_baseline(
                    beneficiary_id=db['beneficiary_id'], 
                    weight=weight, 
                    height=height, 
                    date_collected=date_collected, 
                    birthday=birthday
                )
                if success:
                    record['baseline_mismatch'] = False
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
                
        self.btn_bulk_sync.setEnabled(True)
        self.btn_bulk_sync.setText("Bulk Sync All Exact Matches")
        
        # Re-render the grid so the ActionWidgets update to "Synced ✓"
        self.grid_exact.set_data(self.exact_matches, self.match_columns, action_label="Sync")
        
        QMessageBox.information(self, "Bulk Sync Complete", f"Successfully synced {success_count} matches.\nFailed/Skipped: {fail_count}")

    def on_bulk_bday_use_excel(self):
        from core.database import update_birthday_db
        from PySide6.QtWidgets import QMessageBox
        
        if not hasattr(self, 'bday_discrepancies') or not self.bday_discrepancies:
            return
            
        success_count, fail_count = 0, 0
        self.btn_bday_bulk_excel.setEnabled(False)
        self.btn_bday_bulk_db.setEnabled(False)
        self.btn_bday_bulk_excel.setText("Updating...")
        QApplication.processEvents()
        
        for record in self.bday_discrepancies:
            if not record.get('baseline_mismatch'): continue
            success = update_birthday_db(record['db']['beneficiary_id'], record['excel']['birthday'])
            if success:
                record['baseline_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1
                
        self.btn_bday_bulk_excel.setEnabled(True)
        self.btn_bday_bulk_db.setEnabled(True)
        self.btn_bday_bulk_excel.setText("Bulk Correct (Use Excel)")
        self.grid_bday.set_data(self.bday_discrepancies, self.match_columns, action_label="BirthdayActions")
        QMessageBox.information(self, "Complete", f"Successfully applied Excel birthdays to {success_count} records.")

    def on_bulk_bday_use_db(self):
        from core.excel_updater import update_excel_birthday
        from PySide6.QtWidgets import QMessageBox
        
        if not hasattr(self, 'bday_discrepancies') or not self.bday_discrepancies:
            return
            
        success_count, fail_count = 0, 0
        self.btn_bday_bulk_excel.setEnabled(False)
        self.btn_bday_bulk_db.setEnabled(False)
        self.btn_bday_bulk_db.setText("Updating...")
        QApplication.processEvents()
        
        for record in self.bday_discrepancies:
            if not record.get('baseline_mismatch'): continue
            success = update_excel_birthday(record['excel']['file_path'], record['excel']['row_number'], record['db']['birthday'])
            if success:
                record['baseline_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1
                
        self.btn_bday_bulk_excel.setEnabled(True)
        self.btn_bday_bulk_db.setEnabled(True)
        self.btn_bday_bulk_db.setText("Bulk Correct (Use DB)")
        self.grid_bday.set_data(self.bday_discrepancies, self.match_columns, action_label="BirthdayActions")
        QMessageBox.information(self, "Complete", f"Successfully applied DB birthdays to {success_count} Excel records.")

    def on_bulk_name_use_excel(self):
        from core.database import update_name_db, get_surname_dictionary
        from core.parser import split_beneficiary_name
        from PySide6.QtWidgets import QMessageBox
        
        if not hasattr(self, 'name_discrepancies') or not self.name_discrepancies:
            return
            
        success_count, fail_count = 0, 0
        self.btn_name_bulk_excel.setEnabled(False)
        self.btn_name_bulk_db.setEnabled(False)
        self.btn_name_bulk_excel.setText("Updating...")
        QApplication.processEvents()
        
        surname_dict = get_surname_dictionary()
        
        for record in self.name_discrepancies:
            if not record.get('name_mismatch'): continue
            ex_name = record['excel'].get('raw_name', '')
            ln, fn, mn = split_beneficiary_name(ex_name, surname_dict=surname_dict)
            success = update_name_db(record['db']['beneficiary_id'], ln, fn, mn)
            if success:
                record['name_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1
                
        self.btn_name_bulk_excel.setEnabled(True)
        self.btn_name_bulk_db.setEnabled(True)
        self.btn_name_bulk_excel.setText("Bulk Correct (Use Excel)")
        self.grid_name.set_data(self.name_discrepancies, self.name_match_columns, action_label="NameActions")
        QMessageBox.information(self, "Complete", f"Successfully applied Excel names to {success_count} DB records.")

    def on_bulk_name_use_db(self):
        from core.excel_updater import update_excel_name
        from PySide6.QtWidgets import QMessageBox
        
        if not hasattr(self, 'name_discrepancies') or not self.name_discrepancies:
            return
            
        success_count, fail_count = 0, 0
        self.btn_name_bulk_excel.setEnabled(False)
        self.btn_name_bulk_db.setEnabled(False)
        self.btn_name_bulk_db.setText("Updating...")
        QApplication.processEvents()
        
        for record in self.name_discrepancies:
            if not record.get('name_mismatch'): continue
            
            db = record['db']
            db_fullname = f"{db.get('lastname', '')}, {db.get('firstname', '')}"
            if db.get('middlename'): db_fullname += f" {db.get('middlename')}"
            
            success = update_excel_name(record['excel']['file_path'], record['excel']['row_number'], db_fullname)
            if success:
                record['name_mismatch'] = False
                success_count += 1
            else:
                fail_count += 1
                
        self.btn_name_bulk_excel.setEnabled(True)
        self.btn_name_bulk_db.setEnabled(True)
        self.btn_name_bulk_db.setText("Bulk Correct (Use DB)")
        self.grid_name.set_data(self.name_discrepancies, self.name_match_columns, action_label="NameActions")
        QMessageBox.information(self, "Complete", f"Successfully applied DB names to {success_count} Excel records.")

    def on_files_selected(self, files):
        self.selected_files = files
        self.btn_scan.setEnabled(len(files) > 0)
        self.btn_scan.setText(f"Scan Selected Files ({len(files)})")
        
    def on_browse_folder(self):
        from PySide6.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory containing Excel Files", self.file_explorer.model.rootPath())
        if dir_path:
            self.file_explorer.set_root_path(dir_path)

    def on_rebuild_index(self):
        from PySide6.QtWidgets import QMessageBox
        import sys
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cache_path = os.path.join(base, "interfile_index_cache.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            self.log_message("🗂 Inter-file index cache cleared. It will be rebuilt on the next scan.")
            QMessageBox.information(self, "Index Cleared", "The inter-file duplicate index cache has been cleared.\nIt will be rebuilt automatically on the next scan.")
        else:
            QMessageBox.information(self, "No Cache", "No cached index found. The index will be built fresh on the next scan.")



    def open_dashboard(self):
        from ui.dashboard_window import DashboardWindow
        dash = DashboardWindow(self.file_explorer.model.rootPath(), self)
        dash.exec()

    def open_search(self):
        from ui.search_window import SearchBeneficiaryWindow
        search = SearchBeneficiaryWindow(self)
        search.exec()

    def open_settings(self):
        from ui.components.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec()
        # Refresh title after settings change (mode may have changed)
        user_display = (f"{self.current_user['firstname']} {self.current_user['lastname']} "
                        f"({self.current_user['role']})") if self.current_user else "Unknown User"
        self._update_window_title(user_display)
        self._start_auto_sync_timer()

    def open_about(self):
        from PySide6.QtWidgets import QMessageBox
        import datetime
        try:
            from core.version import APP_VERSION, APP_RELEASE_DATE
        except ImportError:
            from core.version import APP_VERSION
            APP_RELEASE_DATE = datetime.date.today().strftime("%B %d, %Y")
        
        current_year = datetime.date.today().year
        
        about_text = (
            "HAPAG Form 5A Comparator\n\n"
            f"Version: {APP_VERSION}\n"
            f"Update Date: {APP_RELEASE_DATE}\n\n"
            "Developed By: Jhay [06194]\n"
            "Agile Transformation Office\n\n"
            "ASA Philippines Foundation, Inc. (A Microfinance NGO)\n\n"
            f"All Rights Reserved. © {current_year}"
        )
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("About HAPAG Form 5A Comparator")
        msg_box.setText(about_text)
        msg_box.setIcon(QMessageBox.Information)
        
        # Add custom Check for Updates button
        btn_check = msg_box.addButton("Check for Updates", QMessageBox.ActionRole)
        msg_box.addButton(QMessageBox.Ok)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_check:
            self.check_for_updates_manual()

    def check_for_updates_manual(self):
        from PySide6.QtWidgets import QProgressDialog, QMessageBox
        from core.updater import UpdateCheckThread
        
        self.manual_progress = QProgressDialog(
            "Checking for updates...\nConnecting to GitHub server...", 
            "Cancel", 0, 0, self
        )
        self.manual_progress.setWindowTitle("Check for Updates")
        self.manual_progress.setWindowModality(Qt.WindowModal)
        self.manual_progress.setMinimumDuration(0)
        self.manual_progress.show()
        
        self.manual_updater_thread = UpdateCheckThread(self)
        
        def on_avail(tag, body, html_url, download_url):
            self.manual_progress.close()
            self.on_update_available(tag, body, html_url, download_url)
            
        def on_uptodate():
            self.manual_progress.close()
            from core.version import APP_VERSION
            QMessageBox.information(
                self,
                "App Up to Date",
                f"You are running the latest version: {APP_VERSION}.\n"
                "No updates are available at this time."
            )
            
        def on_error(err_msg):
            self.manual_progress.close()
            QMessageBox.warning(
                self,
                "Check Failed",
                f"Failed to check for updates:\n{err_msg}"
            )
            
        def on_cancel():
            try:
                self.manual_updater_thread.update_available.disconnect()
                self.manual_updater_thread.up_to_date.disconnect()
                self.manual_updater_thread.error_occurred.disconnect()
            except:
                pass
            
        self.manual_updater_thread.update_available.connect(on_avail)
        self.manual_updater_thread.up_to_date.connect(on_uptodate)
        self.manual_updater_thread.error_occurred.connect(on_error)
        self.manual_progress.canceled.connect(on_cancel)
        
        self.manual_updater_thread.start()

    def open_user_manual(self):
        dlg = UserManualBrowser(self)
        dlg.exec()

    def _update_window_title(self, user_display: str):
        from core.app_settings import get_mode
        mode_tag = "☁ CLOUD" if get_mode() == 'cloud' else "💾 LOCAL"
        self.setWindowTitle(f"HAPAG Form 5A Comparator [{mode_tag}] — {user_display}")

    def _start_auto_sync_timer(self):
        from core.app_settings import get_mode, get_auto_sync_enabled, get_auto_sync_interval
        if self._auto_sync_timer:
            self._auto_sync_timer.stop()
            self._auto_sync_timer = None

        if get_mode() == 'local' and get_auto_sync_enabled():
            interval_ms = get_auto_sync_interval() * 60 * 1000
            self._auto_sync_timer = QTimer(self)
            self._auto_sync_timer.setInterval(interval_ms)
            self._auto_sync_timer.timeout.connect(self._run_background_sync)
            self._auto_sync_timer.start()
            self.log_message(f"🔄 Auto-sync enabled every {get_auto_sync_interval()} min.")

    def _run_background_sync(self):
        from core.sync_engine import SyncWorker
        self.log_message("🔄 Auto-sync started...")
        worker = SyncWorker(mode=SyncWorker.MODE_SYNC, parent=self)
        worker.finished.connect(lambda ok, msg: self.log_message(f"🔄 Auto-sync: {msg}"))
        worker.error.connect(lambda e: self.log_message(f"⚠ Auto-sync error: {e}"))
        worker.start()

    def _toggle_console(self, checked):
        self.console.setVisible(checked)
        self.btn_console_toggle.setText(("▼" if checked else "▶") + "  Console Log")

    def log_message(self, msg):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.appendPlainText(f"[{ts}]  {msg}")

    def start_scan(self):
        if not self.selected_files: return
        self.btn_scan.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Scanning...")
        self.console.clear()
        self.log_message("Scan started.")
        
        self.worker = ScanWorker(self.selected_files, root_dir=self.file_explorer.model.rootPath())
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.log_message)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        self.worker.start()

    def update_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(msg)
        self.log_message(msg)


    def on_scan_finished(self, results):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("Scan Complete!")
        self.btn_scan.setEnabled(True)
        
        self.exact_matches = results.get("exact_matches", [])
        self.fuzzy_matches = results.get("fuzzy_matches", [])
        self.btn_bulk_sync.setEnabled(len(self.exact_matches) > 0)
        
        # Populate Birthday Discrepancies
        self.bday_discrepancies = []
        for r in self.exact_matches + self.fuzzy_matches:
            if r.get('birthday_mismatch') == True:
                self.bday_discrepancies.append(r)
                
        self.btn_bday_bulk_excel.setEnabled(len(self.bday_discrepancies) > 0)
        self.btn_bday_bulk_db.setEnabled(len(self.bday_discrepancies) > 0)
        
        self.grid_bday.set_data(self.bday_discrepancies, self.match_columns, action_label="BirthdayActions")
        
        # Populate Name Discrepancies
        self.name_discrepancies = []
        for r in self.exact_matches + self.fuzzy_matches:
            if r.get('name_mismatch') == True:
                self.name_discrepancies.append(r)
                
        self.btn_name_bulk_excel.setEnabled(len(self.name_discrepancies) > 0)
        self.btn_name_bulk_db.setEnabled(len(self.name_discrepancies) > 0)
        
        self.grid_name.set_data(self.name_discrepancies, self.name_match_columns, action_label="NameActions")
        
        # Update Exact
        self.grid_exact.set_data(self.exact_matches, self.match_columns, action_label="Sync")
        self.tabs.setTabText(0, f"Exact Matches ({len(self.exact_matches)})")

        # Update Fuzzy
        self.grid_fuzzy.set_data(self.fuzzy_matches, self.match_columns, action_label="Sync")
        self.tabs.setTabText(1, f"High Confidence ({len(self.fuzzy_matches)})")
        
        self.tabs.setTabText(2, f"Birthday Discrepancies ({len(self.bday_discrepancies)})")
        self.tabs.setTabText(3, f"Name Discrepancies ({len(self.name_discrepancies)})")
        
        # Update Potential
        self.grid_potential.set_data(results.get("potential_matches", []), self.match_columns, action_label="Resolve")
        self.tabs.setTabText(4, f"Review Required ({len(results.get('potential_matches', []))})")

        # Update Missing
        missing_db_cols = [
            {"label": "Excel Name", "key": "raw_name"},
            {"label": "Birthday", "key": "birthday", "getter": lambda r: format_display_date(r.get('birthday'))},
            {"label": "Gender", "key": "gender"},
            {"label": "Weight", "key": "weight"},
            {"label": "Height", "key": "height"},
        ]
        self.grid_missing_db.set_data(results.get("missing_in_db", []), missing_db_cols, action_label="MissingDbActions")
        self.tabs.setTabText(5, f"Missing in DB ({len(results.get('missing_in_db', []))})")
        
        missing_ex_cols = [
            {"label": "DB Name", "key": "fullname", "getter": lambda r: f"{r.get('lastname', '')}, {r.get('firstname', '')}"},
            {"label": "Birthday", "key": "birthday", "getter": lambda r: format_display_date(r.get('birthday'))},
            {"label": "Site Name", "key": "site_name"},
            {"label": "Barangay", "key": "barangay_name"}
        ]
        self.grid_missing_excel.set_data(results.get("missing_in_excel", []), missing_ex_cols)
        self.tabs.setTabText(6, f"Missing in Excel ({len(results.get('missing_in_excel', []))})")

        # Update Excel Duplicates
        duplicate_cols = [
            {"label": "Name", "key": "name"},
            {"label": "Duplicate Type", "key": "type"},
            {"label": "Birthday", "key": "birthday", "getter": lambda r: format_display_date(r.get('birthday'))},
            {"label": "Detected In Files", "key": "files"}
        ]
        excel_dupes = results.get("excel_duplicates", [])
        self._excel_dupes_list = excel_dupes  # store full list for manage dialog
        self.grid_excel_duplicates.set_data(excel_dupes, duplicate_cols, action_label="ManageDup")
        self.grid_excel_duplicates.action_triggered.connect(self._on_excel_dup_action)
        self.tabs.setTabText(7, f"Excel Duplicates ({len(excel_dupes)})")


    def on_scan_error(self, err_msg):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"Error: {err_msg}")
        self.btn_scan.setEnabled(True)

    # ── Excel Duplicate Management ────────────────────────────────────────────

    def _on_excel_dup_action(self, action, record, widget):
        """Called when the 'Manage' button is clicked on an Excel Duplicates row."""
        from ui.components.excel_duplicate_dialog import ExcelDuplicateDialog
        dlg = ExcelDuplicateDialog(record, parent=self)
        dlg.exec()

    # ── DB Duplicate Management ───────────────────────────────────────────────

    def open_db_duplicate_manager(self, duplicate_records):
        """Open the DB Duplicate Manager for a set of duplicate beneficiary records."""
        from ui.components.db_duplicate_dialog import DBDuplicateDialog
        dlg = DBDuplicateDialog(duplicate_records, parent=self)
        dlg.exec()


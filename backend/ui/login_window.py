import sys
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QApplication, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

class GoogleLoginThread(QThread):
    finished_auth = Signal(str, str) # email, error_message
    open_browser = Signal(str) # url
    
    def log_debug(self, msg):
        import traceback, datetime
        try:
            log_path = os.path.expanduser("~/hapag_auth_debug.log")
            with open(log_path, "a") as f:
                f.write(f"{datetime.datetime.now().isoformat()} - {msg}\n")
        except:
            pass

    def run(self):
        self.log_debug("--- Starting Google Login Thread ---")
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            import requests
        except ImportError:
            self.log_debug("ImportError: Missing modules")
            self.finished_auth.emit("", "Missing required Google Auth libraries.")
            return

        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
            self.log_debug(f"Running frozen. MEIPASS: {base_dir}")
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            self.log_debug(f"Running locally. Base dir: {base_dir}")
            
        client_secrets_file = os.path.join(base_dir, 'client_secrets.json')
            
        if not os.path.exists(client_secrets_file):
            self.log_debug("Error: client_secrets.json not found")
            self.finished_auth.emit("", "Missing client_secrets.json file. Cannot authenticate with Google.")
            return

        scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
        try:
            env_patch = {}
            if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
                self.log_debug("Patching LD_LIBRARY_PATH for Linux frozen bundle")
                if 'LD_LIBRARY_PATH_ORIG' in os.environ:
                    env_patch['LD_LIBRARY_PATH'] = os.environ.get('LD_LIBRARY_PATH', '')
                    os.environ['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH_ORIG']
                elif 'LD_LIBRARY_PATH' in os.environ:
                    env_patch['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH']
                    del os.environ['LD_LIBRARY_PATH']

            import webbrowser
            
            original_get = webbrowser.get
            
            class AsyncBrowser:
                def __init__(self, thread):
                    self.thread = thread
                def open(self, url, new=0, autoraise=True):
                    self.thread.log_debug("AsyncBrowser.open called, emitting signal to main thread")
                    self.thread.open_browser.emit(url)
                    return True
                    
            def async_get(*args, **kwargs):
                self.log_debug(f"webbrowser.get called with args: {args}")
                return AsyncBrowser(self)
                
            webbrowser.get = async_get

            try:
                self.log_debug("Initializing InstalledAppFlow")
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
                self.log_debug("Calling flow.run_local_server(port=0)")
                creds = flow.run_local_server(port=0)
                self.log_debug("Returned from flow.run_local_server!")
            finally:
                self.log_debug("Restoring webbrowser.get and LD_LIBRARY_PATH")
                webbrowser.get = original_get
                if 'LD_LIBRARY_PATH' in env_patch:
                    os.environ['LD_LIBRARY_PATH'] = env_patch['LD_LIBRARY_PATH']
            
            self.log_debug("Requesting userinfo from Google API...")
            response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': f'Bearer {creds.token}'})
            self.log_debug(f"Userinfo response status: {response.status_code}")
            
            if response.status_code == 200:
                user_info = response.json()
                email = user_info.get('email', '')
                self.log_debug(f"Success! Email: {email}")
                self.finished_auth.emit(email, "")
            else:
                self.log_debug("Failed to fetch user info")
                self.finished_auth.emit("", f"Failed to fetch user info: HTTP {response.status_code}")

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self.log_debug(f"CRITICAL EXCEPTION:\n{err}")
            self.finished_auth.emit("", str(e))


class LoginWindow(QWidget):
    login_successful = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HAPAG Form 5A Comparator - Security Login")
        self.setFixedSize(400, 250)
        self.failed_attempts = 0
        self.authorized_email = None
        
        self.setup_ui()
        
        # Check for persistent Google SSO session
        from core.app_settings import get_cached_email
        cached_email = get_cached_email()
        if cached_email:
            self.authorized_email = cached_email
            self.lbl_subtitle.setText(f"Signed in as {cached_email}\nPlease enter your Access Code.")
            self.lbl_subtitle.setStyleSheet("color: #2c3e50; font-size: 12px;")
            self.stack.setCurrentIndex(1)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.txt_access_code.setFocus())
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        
        lbl_title = QLabel("HAPAG Form 5A Comparator")
        font = QFont("Inter", 16, QFont.Bold)
        lbl_title.setFont(font)
        lbl_title.setAlignment(Qt.AlignCenter)
        
        self.lbl_subtitle = QLabel("Please sign in with your Google Account.")
        self.lbl_subtitle.setAlignment(Qt.AlignCenter)
        self.lbl_subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        
        self.stack = QStackedWidget()
        
        # Page 0: Google Sign In
        page_google = QWidget()
        pg_layout = QVBoxLayout(page_google)
        pg_layout.setAlignment(Qt.AlignCenter)
        
        self.btn_google = QPushButton("Sign in with Google")
        self.btn_google.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #444;
                font-weight: bold;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f1f1f1;
            }
        """)
        self.btn_google.clicked.connect(self.start_google_sso)
        pg_layout.addWidget(self.btn_google)
        self.stack.addWidget(page_google)
        
        # Page 1: Access Code
        page_code = QWidget()
        pc_layout = QVBoxLayout(page_code)
        
        self.txt_access_code = QLineEdit()
        self.txt_access_code.setPlaceholderText("Enter Access Code")
        self.txt_access_code.setEchoMode(QLineEdit.Password)
        self.txt_access_code.setStyleSheet("""
            QLineEdit {
                padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px; font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #3498db; }
        """)
        self.txt_access_code.returnPressed.connect(self.attempt_login)
        
        self.btn_login = QPushButton("Verify & Login")
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #2980b9; color: white; font-weight: bold;
                padding: 10px; border: none; border-radius: 5px; font-size: 14px;
            }
            QPushButton:hover { background-color: #3498db; }
        """)
        self.btn_login.clicked.connect(self.attempt_login)
        
        self.btn_switch_account = QPushButton("Sign in with a different Google account")
        self.btn_switch_account.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #2980b9; font-size: 11px;
                text-decoration: underline; margin-top: 5px;
            }
            QPushButton:hover { color: #3498db; }
        """)
        self.btn_switch_account.clicked.connect(self.switch_google_account)
        
        pc_layout.addWidget(self.txt_access_code)
        pc_layout.addWidget(self.btn_login)
        pc_layout.addWidget(self.btn_switch_account)
        self.stack.addWidget(page_code)
        
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.stack)

    def start_google_sso(self):
        self.btn_google.setEnabled(False)
        self.btn_google.setText("Waiting for browser...")
        self.lbl_subtitle.setText("Please complete the sign-in process in your web browser.")
        QApplication.processEvents()

        self.auth_thread = GoogleLoginThread()
        self.auth_thread.finished_auth.connect(self.on_google_auth_finished)
        self.auth_thread.open_browser.connect(self.on_open_browser)
        self.auth_thread.start()

    def on_open_browser(self, url):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))

    def on_google_auth_finished(self, email, error_msg):
        def log_ui(msg):
            try:
                import datetime
                log_path = os.path.expanduser("~/hapag_auth_debug.log")
                with open(log_path, "a") as f:
                    f.write(f"{datetime.datetime.now().isoformat()} - [UI] {msg}\n")
            except:
                pass
                
        log_ui(f"on_google_auth_finished called. email: {email}, error_msg: {error_msg}")
        
        if error_msg:
            log_ui("Google Sign-In failed with error_msg")
            self.lbl_subtitle.setText(f"Google Sign-In Failed: {error_msg}")
            self.lbl_subtitle.setStyleSheet("color: #e74c3c; font-size: 12px;")
            self.reset_google_btn()
            return
            
        if not email:
            log_ui("Google Sign-In failed: no email")
            self.lbl_subtitle.setText("Error: Could not retrieve email from Google.")
            self.lbl_subtitle.setStyleSheet("color: #e74c3c; font-size: 12px;")
            self.reset_google_btn()
            return

        try:
            log_ui("Importing core.database")
            from core.database import check_email_exists
            log_ui("Calling check_email_exists")
            is_authorized = check_email_exists(email)
            log_ui(f"check_email_exists returned: {is_authorized}")
            db_error = None
        except Exception as e:
            import traceback
            log_ui(f"Exception during check_email_exists:\n{traceback.format_exc()}")
            is_authorized = False
            db_error = str(e)
        
        if db_error:
            log_ui(f"Database error: {db_error}")
            self.lbl_subtitle.setText(f"Database Connection Error: {db_error}")
            self.lbl_subtitle.setStyleSheet("color: #e74c3c; font-size: 12px;")
            self.reset_google_btn()
        elif is_authorized:
            log_ui("Email authorized. Switching to page 1")
            self.authorized_email = email
            
            # Persist Google SSO email session
            from core.app_settings import set_cached_email
            set_cached_email(email)
            
            self.lbl_subtitle.setText(f"Signed in as {email}\nPlease enter your Access Code.")
            self.lbl_subtitle.setStyleSheet("color: #2c3e50; font-size: 12px;")
            self.stack.setCurrentIndex(1)
            self.txt_access_code.setFocus()
        else:
            log_ui("Email NOT authorized.")
            self.lbl_subtitle.setText(f"Unauthorized: '{email}' is not in the system.")
            self.lbl_subtitle.setStyleSheet("color: #e74c3c; font-size: 12px;")
            self.reset_google_btn()

    def reset_google_btn(self):
        self.btn_google.setEnabled(True)
        self.btn_google.setText("Sign in with Google")
        self.lbl_subtitle.setText("Please sign in with your Google Account.")

    def switch_google_account(self):
        from core.app_settings import clear_cached_email
        clear_cached_email()
        self.authorized_email = None
        self.lbl_subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        self.reset_google_btn()
        self.stack.setCurrentIndex(0)

    def attempt_login(self):
        code = self.txt_access_code.text().strip()
        if not code:
            QMessageBox.warning(self, "Validation Error", "Access Code cannot be empty.")
            return
            
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Authenticating...")
        QApplication.processEvents()
        
        from core.database import authenticate_user
        user = authenticate_user(code, self.authorized_email)
        
        if user:
            self.login_successful.emit(user)
            self.close()
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= 5:
                QMessageBox.critical(self, "Security Lockout", "Too many failed attempts. The application will now exit.")
                sys.exit(0)
            else:
                rem = 5 - self.failed_attempts
                QMessageBox.critical(self, "Authentication Failed", f"Invalid Access Code. You have {rem} attempt(s) remaining.")
                self.txt_access_code.clear()
                self.btn_login.setEnabled(True)
                self.btn_login.setText("Verify & Login")
                self.txt_access_code.setFocus()

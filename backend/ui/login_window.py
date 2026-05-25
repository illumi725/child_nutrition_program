import logging
import sys
import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QApplication,
    QStackedWidget,
    QDialog,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class GoogleLoginThread(QThread):
    finished_auth = Signal(str, str)  # email, error_message
    open_browser = Signal(str)  # url

    def log_debug(self, msg):
        from ui.auth_debug import auth_debug_log

        auth_debug_log(msg)

    def run(self):
        self.log_debug("--- Starting Google Login Thread ---")
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            import requests
        except ImportError:
            self.log_debug("ImportError: Missing modules")
            self.finished_auth.emit("", "Missing required Google Auth libraries.")
            return

        if getattr(sys, "frozen", False):
            base_dir = sys._MEIPASS
            self.log_debug(f"Running frozen. MEIPASS: {base_dir}")
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.log_debug(f"Running locally. Base dir: {base_dir}")

        client_secrets_file = os.path.join(base_dir, "client_secrets.json")

        if not os.path.exists(client_secrets_file):
            self.log_debug("Error: client_secrets.json not found")
            self.finished_auth.emit(
                "", "Missing client_secrets.json file. Cannot authenticate with Google."
            )
            return

        scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]
        try:
            env_patch = {}
            if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
                self.log_debug("Patching LD_LIBRARY_PATH for Linux frozen bundle")
                if "LD_LIBRARY_PATH_ORIG" in os.environ:
                    env_patch["LD_LIBRARY_PATH"] = os.environ.get("LD_LIBRARY_PATH", "")
                    os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH_ORIG"]
                elif "LD_LIBRARY_PATH" in os.environ:
                    env_patch["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]
                    del os.environ["LD_LIBRARY_PATH"]

            import webbrowser

            original_get = webbrowser.get

            class AsyncBrowser:
                def __init__(self, thread):
                    self.thread = thread

                def open(self, url, new=0, autoraise=True):
                    self.thread.log_debug(
                        "AsyncBrowser.open called, emitting signal to main thread"
                    )
                    try:
                        from urllib.parse import urlparse, parse_qs

                        parsed_url = urlparse(url)
                        query_params = parse_qs(parsed_url.query)
                        redirect_uri = query_params.get("redirect_uri", [""])[0]
                        if redirect_uri:
                            parsed_redirect = urlparse(redirect_uri)
                            self.thread.local_port = parsed_redirect.port
                            self.thread.log_debug(
                                f"Captured local server port: {self.thread.local_port}"
                            )
                    except Exception as e:
                        self.thread.log_debug(f"Error parsing local port: {e}")
                    self.thread.open_browser.emit(url)
                    return True

            def async_get(*args, **kwargs):
                self.log_debug(f"webbrowser.get called with args: {args}")
                return AsyncBrowser(self)

            webbrowser.get = async_get

            try:
                self.log_debug("Initializing InstalledAppFlow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, scopes
                )
                self.log_debug("Calling flow.run_local_server(port=0)")
                creds = flow.run_local_server(port=0)
                self.log_debug("Returned from flow.run_local_server!")
            finally:
                self.log_debug("Restoring webbrowser.get and LD_LIBRARY_PATH")
                webbrowser.get = original_get
                if "LD_LIBRARY_PATH" in env_patch:
                    os.environ["LD_LIBRARY_PATH"] = env_patch["LD_LIBRARY_PATH"]

            self.log_debug("Requesting userinfo from Google API...")
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {creds.token}"},
            )
            self.log_debug(f"Userinfo response status: {response.status_code}")

            if response.status_code == 200:
                user_info = response.json()
                email = user_info.get("email", "")
                self.log_debug(f"Success! Email: {email}")
                self.finished_auth.emit(email, "")
            else:
                self.log_debug("Failed to fetch user info")
                self.finished_auth.emit(
                    "", f"Failed to fetch user info: HTTP {response.status_code}"
                )

        except Exception as e:
            import traceback

            err = traceback.format_exc()
            self.log_debug(f"CRITICAL EXCEPTION:\n{err}")
            self.finished_auth.emit("", str(e))


class BuiltInSSOBrowser(QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Google Sign-In")
        self.resize(600, 700)

        # Use QStackedWidget to transition from browser to success screen
        self.stack = QStackedWidget(self)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stack)

        # Page 0: Browser View
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtCore import QUrl

        self.web_view = QWebEngineView(self)
        self.stack.addWidget(self.web_view)

        # Override User-Agent to standard desktop Chrome to bypass Google's embedded browser block  # noqa: E501
        profile = self.web_view.page().profile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        self.web_view.setUrl(QUrl(url))

        # Page 1: Success Screen View
        self.success_widget = QWidget(self)
        self.success_widget.setStyleSheet("background-color: #ffffff;")

        success_layout = QVBoxLayout(self.success_widget)
        success_layout.setAlignment(Qt.AlignCenter)
        success_layout.setSpacing(20)

        # Green checkmark circle with premium modern styling
        self.lbl_check = QLabel()
        self.lbl_check.setFixedSize(80, 80)
        self.lbl_check.setAlignment(Qt.AlignCenter)
        self.lbl_check.setStyleSheet("""
            QLabel {
                background-color: #2ecc71;
                color: white;
                font-size: 40px;
                font-weight: bold;
                border-radius: 40px;
            }
        """)
        self.lbl_check.setText("✓")

        self.lbl_success_title = QLabel("Authentication Successful!")
        self.lbl_success_title.setFont(QFont("Inter", 20, QFont.Bold))
        self.lbl_success_title.setStyleSheet("color: #2c3e50;")
        self.lbl_success_title.setAlignment(Qt.AlignCenter)

        self.lbl_success_subtitle = QLabel("Welcome to HAPAG Form 5A Comparator")
        self.lbl_success_subtitle.setFont(QFont("Inter", 12))
        self.lbl_success_subtitle.setStyleSheet("color: #7f8c8d;")
        self.lbl_success_subtitle.setAlignment(Qt.AlignCenter)

        self.lbl_timer_msg = QLabel("Closing window in 5 seconds...")
        self.lbl_timer_msg.setFont(QFont("Inter", 11, QFont.Bold))
        self.lbl_timer_msg.setStyleSheet("color: #2980b9; margin-top: 15px;")
        self.lbl_timer_msg.setAlignment(Qt.AlignCenter)

        success_layout.addWidget(self.lbl_check)
        success_layout.addWidget(self.lbl_success_title)
        success_layout.addWidget(self.lbl_success_subtitle)
        success_layout.addWidget(self.lbl_timer_msg)

        self.stack.addWidget(self.success_widget)

        # Timer tracking
        self.countdown = 5
        self.on_close_callback = None
        self.timer = None

    def show_success_screen(self, email, callback):
        self.on_close_callback = callback
        self.lbl_success_subtitle.setText(
            f"Signed in as {email}\nWelcome to HAPAG Form 5A Comparator"
        )
        self.stack.setCurrentIndex(1)

        # Start countdown timer
        from PySide6.QtCore import QTimer

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick_countdown)
        self.timer.start(1000)

    def tick_countdown(self):
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer.stop()
            if self.on_close_callback:
                self.on_close_callback()
        else:
            self.lbl_timer_msg.setText(f"Closing window in {self.countdown} seconds...")


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
        from core.app_settings import get_cached_email, get_recent_emails

        cached_email = get_cached_email()
        if cached_email:
            self.authorized_email = cached_email
            self.lbl_subtitle.setText(
                f"Signed in as {cached_email}\nPlease enter your Access Code."
            )
            self.lbl_subtitle.setStyleSheet("color: #2c3e50; font-size: 12px;")
            self.stack.setCurrentIndex(1)
            from PySide6.QtCore import QTimer

            QTimer.singleShot(100, lambda: self.txt_access_code.setFocus())
        else:
            recent = get_recent_emails()
            if recent:
                self.lbl_subtitle.setText("Choose an account to continue.")
                self.lbl_subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px;")
                self.update_recent_accounts_list()
                self.stack.setCurrentIndex(2)

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
        """)  # noqa: E501
        self.txt_access_code.returnPressed.connect(self.attempt_login)

        self.btn_login = QPushButton(" Verify and Login")
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

        # Page 2: Choose Account
        self.page_choose_account = QWidget()
        pc_acc_layout = QVBoxLayout(self.page_choose_account)
        pc_acc_layout.setContentsMargins(10, 5, 10, 5)
        pc_acc_layout.setSpacing(10)

        self.recent_list_layout = QVBoxLayout()
        self.recent_list_layout.setSpacing(8)
        pc_acc_layout.addLayout(self.recent_list_layout)

        self.btn_use_another = QPushButton("＋ Use another account")
        self.btn_use_another.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #2980b9; font-weight: bold;
                padding: 8px; border: 1px dashed #2980b9; border-radius: 5px; font-size: 13px;
            }
            QPushButton:hover { background-color: #f6fbfe; }
        """)  # noqa: E501
        self.btn_use_another.clicked.connect(self.show_google_sign_in_page)
        pc_acc_layout.addWidget(self.btn_use_another)

        self.stack.addWidget(self.page_choose_account)

        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.stack)

    def start_google_sso(self):
        self.btn_google.setEnabled(False)
        self.btn_google.setText("Waiting for browser...")
        self.lbl_subtitle.setText(
            "Please complete the sign-in process in your web browser."
        )
        QApplication.processEvents()

        self.auth_thread = GoogleLoginThread()
        self.auth_thread.finished_auth.connect(self.on_google_auth_finished)
        self.auth_thread.open_browser.connect(self.on_open_browser)
        self.auth_thread.start()

    def on_open_browser(self, url):
        self.sso_browser = BuiltInSSOBrowser(url, self)
        self.sso_browser.finished.connect(self.on_sso_browser_finished)
        self.sso_browser.show()

    def on_sso_browser_finished(self, result):
        self.sso_browser = None
        if self.btn_google.text() == "Waiting for browser...":
            from ui.auth_debug import auth_debug_log

            auth_debug_log("[UI] SSO Browser closed manually by the user")

            self.lbl_subtitle.setText("Sign-in cancelled.")
            self.lbl_subtitle.setStyleSheet("color: #e74c3c; font-size: 12px;")
            self.reset_google_btn()

            # Unblock the background server safely by hitting it with a dummy request
            port = getattr(self.auth_thread, "local_port", None)
            if port:

                def shutdown_server():
                    try:
                        import requests

                        requests.get(
                            f"http://localhost:{port}/?error=cancelled", timeout=2
                        )
                    except OSError as exc:
                        logger.debug("SSO cancel shutdown request failed: %s", exc)

                import threading

                threading.Thread(target=shutdown_server, daemon=True).start()

    def on_google_auth_finished(self, email, error_msg):
        from ui.auth_debug import auth_debug_log

        def log_ui(msg):
            auth_debug_log(f"[UI] {msg}")

        log_ui(
            f"on_google_auth_finished called. email: {email}, error_msg: {error_msg}"
        )

        # Close immediately on error, or show a 3-second countdown on successful login
        if hasattr(self, "sso_browser") and self.sso_browser:
            if not error_msg and email:
                # Disconnect standard finished signal to prevent trigger overlap
                try:
                    self.sso_browser.finished.disconnect(self.on_sso_browser_finished)
                except (RuntimeError, TypeError):
                    pass

                browser_ref = self.sso_browser

                def close_and_cleanup():
                    try:
                        browser_ref.close()
                    except RuntimeError:
                        pass

                browser_ref.show_success_screen(email, close_and_cleanup)
                self.sso_browser = None
            else:
                try:
                    self.sso_browser.blockSignals(True)
                    self.sso_browser.close()
                except RuntimeError:
                    pass
                self.sso_browser = None

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

            self.lbl_subtitle.setText(
                f"Signed in as {email}\nPlease enter your Access Code."
            )
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
        from core.app_settings import clear_cached_email, get_recent_emails

        clear_cached_email()
        self.authorized_email = None

        recent = get_recent_emails()
        if recent:
            self.lbl_subtitle.setText("Choose an account to continue.")
            self.lbl_subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px;")
            self.update_recent_accounts_list()
            self.stack.setCurrentIndex(2)
        else:
            self.lbl_subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px;")
            self.reset_google_btn()
            self.stack.setCurrentIndex(0)

    def show_google_sign_in_page(self):
        self.lbl_subtitle.setText("Please sign in with your Google Account.")
        self.lbl_subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        self.reset_google_btn()
        self.stack.setCurrentIndex(0)

    def update_recent_accounts_list(self):
        # Clear previous items from layout
        while self.recent_list_layout.count():
            item = self.recent_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        from core.app_settings import get_recent_emails

        recent_emails = get_recent_emails()

        # Limit to the last 3 accounts for clean visual space in the fixed window size
        for email in recent_emails[-3:]:
            row_widget = QWidget()
            row_widget.setStyleSheet("""
                QWidget {
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 5px;
                }
                QWidget:hover {
                    background-color: #e9ecef;
                }
            """)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 5, 8, 5)
            row_layout.setSpacing(5)

            # Clickable account selection button
            btn_email = QPushButton(email)
            btn_email.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #2c3e50;
                    font-weight: bold;
                    text-align: left;
                    font-size: 12px;
                    padding: 5px;
                }
            """)
            btn_email.clicked.connect(
                lambda checked=False, em=email: self.select_recent_account(em)
            )

            # Small delete button next to email
            btn_remove = QPushButton("✕")
            btn_remove.setToolTip("Remove account from this list")
            btn_remove.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #e74c3c;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 2px;
                }
                QPushButton:hover {
                    color: #c0392b;
                }
            """)
            btn_remove.clicked.connect(
                lambda checked=False, em=email: self.remove_recent_account_from_list(em)
            )

            row_layout.addWidget(btn_email, 1)
            row_layout.addWidget(btn_remove)

            self.recent_list_layout.addWidget(row_widget)

    def select_recent_account(self, email):
        # Checks if email exists in database (offline or online)
        from core.database import check_email_exists

        if check_email_exists(email):
            # Set active cached email
            from core.app_settings import set_cached_email

            set_cached_email(email)

            self.authorized_email = email
            self.lbl_subtitle.setText(
                f"Signed in as {email}\nPlease enter your Access Code."
            )
            self.lbl_subtitle.setStyleSheet("color: #2c3e50; font-size: 12px;")
            self.stack.setCurrentIndex(1)
            self.txt_access_code.setFocus()
        else:
            QMessageBox.critical(
                self,
                "Access Blocked",
                f"The account '{email}' is no longer registered or authorized in the system.",  # noqa: E501
            )
            self.remove_recent_account_from_list(email)

    def remove_recent_account_from_list(self, email):
        from core.app_settings import remove_recent_email

        remove_recent_email(email)
        self.update_recent_accounts_list()

        # If no more recent accounts remain, redirect to standard Google SSO page
        from core.app_settings import get_recent_emails

        if not get_recent_emails():
            self.show_google_sign_in_page()

    def attempt_login(self):
        code = self.txt_access_code.text().strip()
        if not code:
            QMessageBox.warning(
                self, "Validation Error", "Access Code cannot be empty."
            )
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Authenticating...")
        QApplication.processEvents()

        from core.database import authenticate_user
        from core.permissions import is_app_access_allowed

        user = authenticate_user(code, self.authorized_email)

        if user:
            if not is_app_access_allowed(user.get("role")):
                role_label = user.get("role", "Unknown")
                QMessageBox.warning(
                    self,
                    "Access Not Allowed",
                    f"Your role ({role_label}) is not permitted to use the HAPAG Form 5A Comparator.\n\n"  # noqa: E501
                    "This application is for ADMIN, PM, and PO users only.\n"
                    "FPA accounts cannot sign in.",
                )
                self.btn_login.setEnabled(True)
                self.btn_login.setText(" Verify and Login")
                return
            self.login_successful.emit(user)
            self.close()
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= 5:
                QMessageBox.critical(
                    self,
                    "Security Lockout",
                    "Too many failed attempts. The application will now exit.",
                )
                sys.exit(0)
            else:
                rem = 5 - self.failed_attempts
                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    f"Invalid Access Code. You have {rem} attempt(s) remaining.",
                )
                self.txt_access_code.clear()
                self.btn_login.setEnabled(True)
                self.btn_login.setText(" Verify and Login")
                self.txt_access_code.setFocus()

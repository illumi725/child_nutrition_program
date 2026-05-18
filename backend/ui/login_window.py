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
    
    def run(self):
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            import requests
        except ImportError:
            self.finished_auth.emit("", "Missing required Google Auth libraries.")
            return

        client_secrets_file = os.path.join(os.path.dirname(__file__), '..', 'client_secrets.json')
        if not os.path.exists(client_secrets_file):
            if hasattr(sys, '_MEIPASS'):
                client_secrets_file = os.path.join(sys._MEIPASS, 'client_secrets.json')
            
        if not os.path.exists(client_secrets_file):
            self.finished_auth.emit("", "Missing client_secrets.json file. Cannot authenticate with Google.")
            return

        scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            creds = flow.run_local_server(port=0)
            
            response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': f'Bearer {creds.token}'})
            if response.status_code == 200:
                user_info = response.json()
                email = user_info.get('email', '')
                self.finished_auth.emit(email, "")
            else:
                self.finished_auth.emit("", f"Failed to fetch user info: HTTP {response.status_code}")

        except Exception as e:
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
        
        pc_layout.addWidget(self.txt_access_code)
        pc_layout.addWidget(self.btn_login)
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
        self.auth_thread.start()

    def on_google_auth_finished(self, email, error_msg):
        if error_msg:
            QMessageBox.critical(self, "Google Sign-In Failed", error_msg)
            self.reset_google_btn()
            return
            
        if not email:
            QMessageBox.critical(self, "Error", "Could not retrieve email from Google.")
            self.reset_google_btn()
            return

        from core.database import check_email_exists
        is_authorized = check_email_exists(email)
        
        if is_authorized:
            self.authorized_email = email
            self.lbl_subtitle.setText(f"Signed in as {email}\nPlease enter your Access Code.")
            self.stack.setCurrentIndex(1)
            self.txt_access_code.setFocus()
        else:
            QMessageBox.warning(self, "Unauthorized", f"The email '{email}' is not authorized to use this application.")
            self.reset_google_btn()

    def reset_google_btn(self):
        self.btn_google.setEnabled(True)
        self.btn_google.setText("Sign in with Google")
        self.lbl_subtitle.setText("Please sign in with your Google Account.")

    def attempt_login(self):
        code = self.txt_access_code.text().strip()
        if not code:
            QMessageBox.warning(self, "Validation Error", "Access Code cannot be empty.")
            return
            
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Authenticating...")
        QApplication.processEvents()
        
        from core.database import authenticate_user
        user = authenticate_user(code)
        
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

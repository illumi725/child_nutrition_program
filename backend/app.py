import sys
import os

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

from core.app_settings import get_theme
from ui.theme import apply_theme

def main():
    from core.logging_config import setup_logging
    setup_logging()

    app = QApplication(sys.argv)
    
    # Apply macOS-inspired style with Dark/Light mode support
    app.setStyle("Fusion")
    apply_theme(app, get_theme())
    
    login = LoginWindow()
    main_window = None
    
    def on_login(user):
        nonlocal main_window
        main_window = MainWindow(current_user=user)
        main_window.showMaximized()
        
    login.login_successful.connect(on_login)
    login.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

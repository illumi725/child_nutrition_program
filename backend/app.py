import sys
import os

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Optionally apply a modern style
    app.setStyle("Fusion")
    
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

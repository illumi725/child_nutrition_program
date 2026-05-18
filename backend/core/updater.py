import requests
from PySide6.QtCore import QThread, Signal
from core.version import APP_VERSION
import re

class UpdateCheckThread(QThread):
    # Signals:
    # str: latest version tag (e.g. "v1.0.6")
    # str: release notes / body text
    # str: direct html url to the release page
    update_available = Signal(str, str, str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_url = "https://api.github.com/repos/illumi725/child_nutrition_program/releases/latest"
        
    def _parse_version(self, version_str):
        """Extracts integers from a version string like 'v1.0.5' for comparison."""
        numbers = re.findall(r'\d+', version_str)
        return [int(n) for n in numbers]

    def run(self):
        try:
            # Set a short timeout so we don't hang the thread indefinitely on slow connections
            response = requests.get(self.api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "")
                
                # Simple version comparison
                current_parts = self._parse_version(APP_VERSION)
                latest_parts = self._parse_version(latest_tag)
                
                # If parsed parts exist and latest is greater than current
                if current_parts and latest_parts and latest_parts > current_parts:
                    body = data.get("body", "No release notes provided.")
                    html_url = data.get("html_url", "")
                    self.update_available.emit(latest_tag, body, html_url)
            else:
                self.error_occurred.emit(f"GitHub API returned {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(str(e))

import os
import re
import sys
import tempfile
import zipfile
import requests
from PySide6.QtCore import QThread, Signal
from core.version import APP_VERSION

class UpdateCheckThread(QThread):
    # Signals:
    # str: latest version tag (e.g. "v1.1.7")
    # str: release notes / body text
    # str: direct html url to the release page
    # str: platform-specific download url
    update_available = Signal(str, str, str, str)
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
                    
                    # Format platform-specific download zip URL based on OS
                    tag = latest_tag
                    if sys.platform.startswith('win32'):
                        download_url = f"https://github.com/illumi725/child_nutrition_program/releases/download/{tag}/hapag-comparator-windows.zip"
                    elif sys.platform.startswith('darwin'):
                        download_url = f"https://github.com/illumi725/child_nutrition_program/releases/download/{tag}/hapag-comparator-macos.zip"
                    else:
                        download_url = f"https://github.com/illumi725/child_nutrition_program/releases/download/{tag}/hapag-comparator-linux.zip"
                        
                    self.update_available.emit(latest_tag, body, html_url, download_url)
            else:
                self.error_occurred.emit(f"GitHub API returned {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadUpdateThread(QThread):
    # Signals:
    # int: progress percentage (0-100)
    # str: progress status message text
    progress = Signal(int, str)
    finished = Signal(str, str) # Path to local extracted directory, and path to source directory containing files
    error = Signal(str)

    def __init__(self, download_url, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.progress.emit(0, "Connecting to update server...")
            response = requests.get(self.download_url, stream=True, timeout=10)
            if response.status_code != 200:
                self.error.emit(f"Failed to download update: HTTP {response.status_code}")
                return
                
            total_size = int(response.headers.get('content-length', 0))
            
            # Save temporary files in OS temp dir
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, "hapag_update.zip")
            
            downloaded = 0
            chunk_size = 1024 * 64
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._is_cancelled:
                        self.error.emit("Download cancelled.")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            self.progress.emit(pct, f"Downloading update... {pct}% ({downloaded // 1024} KB / {total_size // 1024} KB)")
                        else:
                            self.progress.emit(50, f"Downloading update... ({downloaded // 1024} KB)")
                            
            if self._is_cancelled:
                self.error.emit("Download cancelled.")
                return
                
            self.progress.emit(95, "Extracting update archive...")
            
            extracted_dir = os.path.join(temp_dir, "hapag_extracted")
            
            # Wipe previous extraction folder if present
            if os.path.exists(extracted_dir):
                import shutil
                try:
                    shutil.rmtree(extracted_dir)
                except Exception as e:
                    pass
            os.makedirs(extracted_dir, exist_ok=True)
            
            # Unzip contents
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extracted_dir)
                
            # Clean up the zip file itself
            try:
                os.remove(zip_path)
            except:
                pass
                
            # Auto-detect nested packaging folders inside the zip (e.g. hapag-comparator-linux/)
            source_dir = extracted_dir
            contents = os.listdir(extracted_dir)
            if len(contents) == 1 and os.path.isdir(os.path.join(extracted_dir, contents[0])):
                source_dir = os.path.join(extracted_dir, contents[0])
                
            self.progress.emit(100, "Update extraction ready.")
            self.finished.emit(extracted_dir, source_dir)
            
        except Exception as e:
            self.error.emit(str(e))

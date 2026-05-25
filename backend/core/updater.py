import hashlib
import os
import re
import sys
import tempfile
import zipfile
import requests
from PySide6.QtCore import QThread, Signal
from core.version import APP_VERSION


def _parse_sha256_file(content: str) -> dict[str, str]:
    """Parse 'HASH  filename' lines from checksums.txt or .sha256 sidecar."""
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 64:
            result[parts[-1]] = parts[0].lower()
    return result


def compute_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract_zip(zip_path: str, dest_dir: str) -> None:
    """Extract zip members only under dest_dir (prevents zip-slip)."""
    dest_real = os.path.realpath(dest_dir)
    os.makedirs(dest_real, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            target = os.path.realpath(os.path.join(dest_dir, member))
            if not (target == dest_real or target.startswith(dest_real + os.sep)):
                raise ValueError(f"Unsafe path in archive: {member}")
        zf.extractall(dest_dir)


def resolve_source_dir(extracted_dir: str) -> str:
    source_dir = extracted_dir
    contents = os.listdir(extracted_dir)
    if len(contents) == 1 and os.path.isdir(os.path.join(extracted_dir, contents[0])):
        source_dir = os.path.join(extracted_dir, contents[0])
    return source_dir


def fetch_expected_sha256(download_url: str, assets: list) -> str | None:
    """Find expected SHA256 from release assets (sidecar or checksums.txt)."""
    if not download_url:
        return None
    basename = os.path.basename(download_url.split("?")[0])

    for asset in assets:
        name = asset.get("name", "")
        if name == f"{basename}.sha256" or name.endswith(f"{basename}.sha256"):
            url = asset.get("browser_download_url", "")
            if url:
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200:
                        parsed = _parse_sha256_file(r.text)
                        if parsed:
                            return next(iter(parsed.values()))
                        line = r.text.strip().split()
                        if line and len(line[0]) == 64:
                            return line[0].lower()
                except Exception:
                    pass

    for asset in assets:
        if asset.get("name", "").lower() == "checksums.txt":
            url = asset.get("browser_download_url", "")
            if url:
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200:
                        parsed = _parse_sha256_file(r.text)
                        return parsed.get(basename) or parsed.get(f"./{basename}")
                except Exception:
                    pass
    return None


class UpdateCheckThread(QThread):
    update_available = Signal(
        str, str, str, str, str
    )  # tag, body, html_url, download_url, expected_sha256
    up_to_date = Signal()
    error_occurred = Signal(str)

    GITHUB_OWNER = "illumi725"
    GITHUB_REPO = "child_nutrition_program"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_url = (
            f"https://api.github.com/repos/"
            f"{self.GITHUB_OWNER}/{self.GITHUB_REPO}/releases/latest"
        )

    def _parse_version(self, version_str):
        numbers = re.findall(r"\d+", version_str)
        return [int(n) for n in numbers]

    def run(self):
        try:
            headers = {"Accept": "application/vnd.github+json"}
            response = requests.get(self.api_url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "")
                body = data.get("body", "No release notes provided.")
                html_url = data.get("html_url", "")
                assets = data.get("assets", [])

                current_parts = self._parse_version(APP_VERSION)
                latest_parts = self._parse_version(latest_tag)

                if current_parts and latest_parts and latest_parts > current_parts:
                    if sys.platform.startswith("win32"):
                        keyword = "windows"
                    elif sys.platform.startswith("darwin"):
                        keyword = "macos"
                    else:
                        keyword = "linux"

                    download_url = ""
                    for asset in assets:
                        if keyword in asset.get("name", "").lower():
                            download_url = asset.get("browser_download_url", "")
                            break

                    expected_sha256 = fetch_expected_sha256(download_url, assets) or ""
                    self.update_available.emit(
                        latest_tag, body, html_url, download_url, expected_sha256
                    )
                else:
                    self.up_to_date.emit()
            elif response.status_code == 404:
                self.up_to_date.emit()
            else:
                self.error_occurred.emit(f"GitHub API returned {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadUpdateThread(QThread):
    progress = Signal(int, str)
    finished = Signal(str, str)
    error = Signal(str)

    def __init__(self, download_url, expected_sha256=None, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.expected_sha256 = (expected_sha256 or "").strip().lower() or None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.progress.emit(0, "Connecting to update server...")
            response = requests.get(self.download_url, stream=True, timeout=10)
            if response.status_code != 200:
                self.error.emit(
                    f"Failed to download update: HTTP {response.status_code}"
                )
                return

            total_size = int(response.headers.get("content-length", 0))
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, "hapag_update.zip")

            downloaded = 0
            chunk_size = 1024 * 64

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._is_cancelled:
                        self.error.emit("Download cancelled.")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 100)
                            self.progress.emit(
                                pct,
                                f"Downloading update... {pct}% ({downloaded // 1024} KB / {total_size // 1024} KB)",  # noqa: E501
                            )
                        else:
                            self.progress.emit(
                                50, f"Downloading update... ({downloaded // 1024} KB)"
                            )

            if self._is_cancelled:
                self.error.emit("Download cancelled.")
                return

            if self.expected_sha256:
                self.progress.emit(92, "Verifying download integrity...")
                actual = compute_file_sha256(zip_path)
                if actual != self.expected_sha256:
                    try:
                        os.remove(zip_path)
                    except OSError:
                        pass
                    self.error.emit(
                        "Download integrity check failed (SHA256 mismatch). "
                        "The update was not installed."
                    )
                    return

            self.progress.emit(95, "Extracting update archive...")

            extracted_dir = os.path.join(temp_dir, "hapag_extracted")

            if os.path.exists(extracted_dir):
                import shutil

                try:
                    shutil.rmtree(extracted_dir)
                except OSError:
                    pass
            os.makedirs(extracted_dir, exist_ok=True)

            safe_extract_zip(zip_path, extracted_dir)

            try:
                os.remove(zip_path)
            except OSError:
                pass

            source_dir = resolve_source_dir(extracted_dir)

            self.progress.emit(100, "Update extraction ready.")
            self.finished.emit(extracted_dir, source_dir)

        except ValueError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))

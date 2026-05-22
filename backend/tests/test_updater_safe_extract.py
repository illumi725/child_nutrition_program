import os
import tempfile
import zipfile

import pytest

from core.updater import compute_file_sha256, safe_extract_zip


def test_safe_extract_rejects_zip_slip():
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "evil.zip")
        dest = os.path.join(tmp, "out")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../outside.txt", "bad")
        with pytest.raises(ValueError, match="Unsafe path"):
            safe_extract_zip(zip_path, dest)


def test_compute_file_sha256():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello")
        path = f.name
    try:
        assert len(compute_file_sha256(path)) == 64
    finally:
        os.remove(path)

"""
App settings manager.
Reads/writes a JSON file in the OS-appropriate AppData directory.
Manages mode (cloud/local) and auto-sync settings.
"""
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

APP_NAME = "HAPAGComparator"

def _get_settings_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.path.expanduser("~/.config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path

def _settings_path() -> str:
    return os.path.join(_get_settings_dir(), "app_settings.json")

def _load() -> dict:
    path = _settings_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load app settings from %s: %s", path, exc)
        return {}

def _save(data: dict):
    with open(_settings_path(), 'w') as f:
        json.dump(data, f, indent=2)

# ── Public API ────────────────────────────────────────────────

def get_mode() -> str:
    """Returns 'cloud' or 'local'. Defaults to 'cloud'."""
    return _load().get('mode', 'cloud')

def set_mode(mode: str):
    assert mode in ('cloud', 'local')
    d = _load()
    d['mode'] = mode
    _save(d)

def get_theme() -> str:
    """Returns 'light' or 'dark'. Defaults to 'light'."""
    return _load().get('theme', 'light')

def set_theme(theme: str):
    assert theme in ('light', 'dark')
    d = _load()
    d['theme'] = theme
    _save(d)

def get_local_db_path() -> str:
    """Returns the absolute path to the local SQLite database file."""
    return os.path.join(_get_settings_dir(), "hapag_local.db")

def get_auto_sync_enabled() -> bool:
    return _load().get('auto_sync', True)

def set_auto_sync_enabled(val: bool):
    d = _load()
    d['auto_sync'] = val
    _save(d)

def get_auto_sync_interval() -> int:
    """Returns auto-sync interval in minutes. Default: 30."""
    return int(_load().get('auto_sync_interval', 30))

def set_auto_sync_interval(minutes: int):
    d = _load()
    d['auto_sync_interval'] = minutes
    _save(d)

def get_last_synced() -> str:
    return _load().get('last_synced', 'Never')

def set_last_synced(ts: str):
    d = _load()
    d['last_synced'] = ts
    _save(d)

def get_cached_email() -> str | None:
    return _load().get('cached_email', None)

def set_cached_email(email: str):
    d = _load()
    d['cached_email'] = email
    
    # Auto-add to recent list
    recent = d.get('recent_emails', [])
    if email not in recent:
        recent.append(email)
    d['recent_emails'] = recent
    _save(d)

def clear_cached_email():
    d = _load()
    if 'cached_email' in d:
        del d['cached_email']
    _save(d)

def get_recent_emails() -> list:
    return _load().get('recent_emails', [])

def remove_recent_email(email: str):
    d = _load()
    recent = d.get('recent_emails', [])
    if email in recent:
        recent.remove(email)
    d['recent_emails'] = recent
    if d.get('cached_email') == email:
        d['cached_email'] = None
    _save(d)

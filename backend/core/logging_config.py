"""Application-wide logging setup."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from core.app_settings import _get_settings_dir

_CONFIGURED = False
_UI_HANDLER: logging.Handler | None = None


def setup_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = _get_settings_dir()
    log_path = os.path.join(log_dir, "hapag_comparator.log")

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    if not getattr(sys, "frozen", False):
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        console.setLevel(logging.WARNING)
        root.addHandler(console)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


class _QtLogHandler(logging.Handler):
    """Forwards log records to a UI callback (e.g. MainWindow console)."""

    def __init__(self, emit_callback):
        super().__init__()
        self._emit_callback = emit_callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._emit_callback(self.format(record))
        except Exception:
            self.handleError(record)


def attach_ui_log_handler(emit_callback, level: int = logging.WARNING) -> None:
    """Attach a handler that mirrors WARNING+ logs to the in-app console."""
    global _UI_HANDLER
    setup_logging()
    if _UI_HANDLER is not None:
        logging.getLogger().removeHandler(_UI_HANDLER)
    fmt = logging.Formatter("%(levelname)s %(name)s: %(message)s")
    _UI_HANDLER = _QtLogHandler(emit_callback)
    _UI_HANDLER.setFormatter(fmt)
    _UI_HANDLER.setLevel(level)
    logging.getLogger().addHandler(_UI_HANDLER)

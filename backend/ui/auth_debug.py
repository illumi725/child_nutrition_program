"""Development-only auth debug file logging (disabled in production builds)."""

from __future__ import annotations

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def auth_debug_log(msg: str) -> None:
    from core.version import IS_PRODUCTION_BUILD

    if IS_PRODUCTION_BUILD:
        return
    try:
        log_path = os.path.expanduser("~/hapag_auth_debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {msg}\n")
    except OSError as exc:
        logger.debug("auth debug log write failed: %s", exc)

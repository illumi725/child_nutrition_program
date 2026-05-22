"""Desktop audit logging (R19). Writes to cloud DB when available."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def audit_user_id(user: Optional[dict]) -> Optional[str]:
    """Extract user_id from the logged-in user dict passed through the UI."""
    if not user:
        return None
    uid = user.get("user_id")
    return str(uid) if uid is not None else None


def log_action(
    user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Record an audit entry. Fails silently if table missing (migration pending).
    """
    try:
        from core.database import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO desktop_audit_log
                        (user_id, action, entity_type, entity_id, details)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        action,
                        entity_type,
                        entity_id,
                        json.dumps(details) if details else None,
                    ),
                )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        logger.warning("audit log skipped: %s", e)
        return False

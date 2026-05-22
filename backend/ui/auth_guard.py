"""UI helpers for permission checks."""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtWidgets import QMessageBox, QWidget

from core.permissions import PERMISSION_LABELS, has_permission


def user_has_permission(user: Optional[dict[str, Any]], permission: str) -> bool:
    if not user:
        return False
    return has_permission(user.get("role"), permission)


def require_permission(
    parent: QWidget,
    user: Optional[dict[str, Any]],
    permission: str,
) -> bool:
    if user_has_permission(user, permission):
        return True
    role = (user or {}).get("role", "unknown")
    action = PERMISSION_LABELS.get(permission, permission.replace("_", " "))
    QMessageBox.warning(
        parent,
        "Access Denied",
        f"Your role ({role}) is not allowed to {action}.\n"
        "Contact an administrator if you need access.",
    )
    return False

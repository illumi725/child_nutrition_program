"""Controller for user action audit logging."""
from __future__ import annotations


class AuditController:
    def __init__(self, main_window):
        self._win = main_window

    def audit(self, action, entity_type, entity_id=None, details=None):
        from core.audit import audit_user_id, log_action

        log_action(
            audit_user_id(self._win.current_user),
            action,
            entity_type,
            entity_id=entity_id,
            details=details,
        )

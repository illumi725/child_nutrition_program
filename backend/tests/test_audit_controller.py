"""Unit tests for AuditController."""

from __future__ import annotations

import sys
import types

import pytest

from ui.controllers.audit_controller import AuditController


@pytest.fixture
def audit_env(monkeypatch):
    log_action_calls = []

    audit_mod = types.ModuleType("core.audit")
    audit_mod.audit_user_id = lambda user: user.get("id", 0)
    audit_mod.log_action = lambda user_id, action, entity_type, entity_id=None, details=None: log_action_calls.append(
        (user_id, action, entity_type, entity_id, details)
    )
    monkeypatch.setitem(sys.modules, "core.audit", audit_mod)
    return log_action_calls


class DummyWindow:
    def __init__(self):
        self.current_user = {"id": 99}


def test_audit_forwards_to_core(audit_env):
    win = DummyWindow()
    ctrl = AuditController(win)
    ctrl.audit("test_action", "entity", entity_id=123, details="detail")

    assert audit_env == [(99, "test_action", "entity", 123, "detail")]

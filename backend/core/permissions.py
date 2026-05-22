"""Role-based permissions for desktop actions (BRD §7.3.2).

Organization roles:
  ADMIN — full access
  PM, PO — encoders (comparison, sync, add, resolve; no destructive/bulk admin actions)
  FPA — not permitted to use this desktop application
"""

from __future__ import annotations

from typing import Optional

# Keys are normalized to lowercase via normalize_role().

_ENCODER_PERMISSIONS = {
    "scan",
    "sync_baseline",
    "add_beneficiary",
    "edit_discrepancy",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "scan",
        "sync_baseline",
        "bulk_sync",
        "add_beneficiary",
        "edit_discrepancy",
        "delete_beneficiary",
        "delete_excel_row",
        "bulk_transfer",
        "full_replication",
        "settings_mode_switch",
    },
    "pm": set(_ENCODER_PERMISSIONS),
    "po": set(_ENCODER_PERMISSIONS),
    "fpa": set(),
}

# Roles that must not pass login (even with valid access code).
ROLES_BLOCKED_FROM_APP: frozenset[str] = frozenset({"fpa"})

PERMISSION_LABELS: dict[str, str] = {
    "scan": "scan folders",
    "sync_baseline": "sync baseline data",
    "bulk_sync": "run bulk baseline sync",
    "add_beneficiary": "add beneficiaries",
    "edit_discrepancy": "resolve discrepancies",
    "delete_beneficiary": "delete beneficiaries from the database",
    "delete_excel_row": "delete rows from Excel files",
    "bulk_transfer": "bulk transfer beneficiaries between sites",
    "full_replication": "run full database replication",
    "settings_mode_switch": "change cloud/local mode in settings",
}


def normalize_role(role: Optional[str]) -> str:
    return str(role or "").strip().lower()


def is_app_access_allowed(role: Optional[str]) -> bool:
    """False for FPA and unknown roles without a permission map."""
    norm = normalize_role(role)
    if norm in ROLES_BLOCKED_FROM_APP:
        return False
    return norm in ROLE_PERMISSIONS and bool(ROLE_PERMISSIONS[norm])


def has_permission(role: Optional[str], permission: str) -> bool:
    if not role or not permission:
        return False
    norm = normalize_role(role)
    if norm in ROLES_BLOCKED_FROM_APP:
        return False
    perms = ROLE_PERMISSIONS.get(norm, set())
    return permission in perms

from core.permissions import has_permission, is_app_access_allowed


def test_admin_can_delete():
    assert has_permission("ADMIN", "delete_beneficiary")


def test_pm_cannot_delete():
    assert not has_permission("PM", "delete_beneficiary")


def test_po_can_sync():
    assert has_permission("PO", "sync_baseline")


def test_pm_cannot_bulk_sync():
    assert not has_permission("pm", "bulk_sync")


def test_fpa_blocked_from_app():
    assert not is_app_access_allowed("FPA")
    assert not has_permission("FPA", "scan")


def test_fpa_cannot_login():
    assert not is_app_access_allowed("fpa")


def test_pm_can_use_app():
    assert is_app_access_allowed("PM")


def test_unknown_role_denied():
    assert not is_app_access_allowed("guest")
    assert not has_permission("guest", "scan")

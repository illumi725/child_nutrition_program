from unittest.mock import MagicMock, patch

import pytest

from core import database as db


@pytest.fixture
def mock_connection():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


def test_delete_beneficiary_cascade_success(mock_connection):
    conn, cursor = mock_connection
    with patch.object(db, "get_db_connection", return_value=conn):
        ok, err = db.delete_beneficiary_cascade("abc123")
    assert ok is True
    assert err is None
    conn.commit.assert_called_once()
    assert cursor.execute.call_count >= 6


def test_delete_beneficiary_cascade_failure(mock_connection):
    conn, cursor = mock_connection
    cursor.execute.side_effect = [None, None, None, None, None, RuntimeError("FK violation")]
    with patch.object(db, "get_db_connection", return_value=conn):
        ok, err = db.delete_beneficiary_cascade("bad-id")
    assert ok is False
    assert "FK violation" in err
    conn.rollback.assert_called_once()


def test_generate_beneficiary_id_unique_on_second_try(mock_connection):
    conn, cursor = mock_connection
    cursor.fetchone.side_effect = [{"1": 1}, None]
    with patch.object(db, "_random_beneficiary_id", side_effect=["takenid01", "uniqueid02"]):
        bid = db.generate_beneficiary_id(cursor)
    assert bid == "uniqueid02"

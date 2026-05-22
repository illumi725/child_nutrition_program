#!/usr/bin/env python3
"""
One-time migration: hash plaintext users.access_code values with bcrypt.

Prerequisites (from backend/ directory):
  pip install -r requirements.txt
  # or: pip install bcrypt PyMySQL

Ensure db.dat exists in backend/ or core/_config.py is configured, then:
  python scripts/migrate_access_codes.py --dry-run
  python scripts/migrate_access_codes.py
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from core.password_utils import hash_access_code, is_hashed_access_code
except ModuleNotFoundError as e:
    if "bcrypt" in str(e):
        print(
            "ERROR: bcrypt is not installed in this Python environment.\n"
            "From the backend/ folder run:\n"
            "  pip install -r requirements.txt\n"
            "or:\n"
            "  pip install bcrypt\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from e
    raise

from core.database import _get_cloud_connection


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash plaintext access codes in users table.")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not UPDATE.")
    args = parser.parse_args()

    conn = _get_cloud_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id, access_code, role FROM users "
                "WHERE deleted_at IS NULL AND access_code IS NOT NULL"
            )
            rows = cursor.fetchall()

        updated = 0
        skipped = 0
        for row in rows:
            uid = row["user_id"]
            stored = row.get("access_code") or ""
            role = row.get("role", "")
            if not stored or is_hashed_access_code(stored):
                skipped += 1
                continue
            hashed = hash_access_code(stored)
            print(f"  user_id={uid} role={role} -> bcrypt hash")
            if not args.dry_run:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET access_code = %s WHERE user_id = %s",
                        (hashed, uid),
                    )
                conn.commit()
            updated += 1

        print(f"Done. updated={updated} skipped={skipped} dry_run={args.dry_run}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

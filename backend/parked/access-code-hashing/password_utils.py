"""Access code hashing and verification (supports legacy plaintext during migration)."""

from __future__ import annotations

import bcrypt

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def is_hashed_access_code(stored: str) -> bool:
    return bool(stored) and stored.startswith(_BCRYPT_PREFIXES)


def hash_access_code(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_access_code(plain: str, stored: str) -> bool:
    if not plain or not stored:
        return False
    if is_hashed_access_code(stored):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
        except ValueError:
            return False
    # Legacy plaintext (migrate with scripts/migrate_access_codes.py)
    return plain == stored

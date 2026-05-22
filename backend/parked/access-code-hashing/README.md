# Parked: Access code hashing (not enabled)

Plaintext `users.access_code` is used in production. This folder holds the bcrypt implementation for a future coordinated rollout with the web app.

## When enabling

1. Deploy web changes from `ChildFeedingProgramProject/cnp_backend/parked/access-code-hashing/`
2. Deploy desktop: restore `core/password_utils.py`, update `authenticate_user` in `database.py`
3. Run SQL `alter_users_access_code_column.sql` (web parked folder)
4. Run migration: `python scripts/migrate_access_codes.py` (dry-run first)

## Files here

- `password_utils.py` — hash/verify helpers
- `migrate_access_codes.py` — one-time DB migration
- `test_password_utils.py` — unit tests

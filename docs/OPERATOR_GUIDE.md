# HAPAG Comparator — Operator Guide

## Cloud vs Local Mode

| Mode | When to use | Behavior |
|------|-------------|----------|
| **Cloud** | Stable internet; live reconciliation | Connects to production MySQL on each action |
| **Local** | Slow/offline field work | Uses SQLite snapshot under AppData (`HAPAGComparator/hapag_local.db`) |

Switch mode in **Settings**. A restart is required after switching.

## First-time local setup

1. Open **Settings** → choose **Local Mode** → restart when prompted.
2. Run **Full Replication** (admin role) to download all tables from cloud.
3. Confirm **Last Sync** timestamp updates.

## Auto-sync (local mode)

- Default interval: 30 minutes (configurable in Settings).
- Pushes local changes to cloud and pulls remote updates (delta sync).

## Scan workflow

1. Browse to folder containing Form 5A `.xlsx` files.
2. Select files → **Scan Selected Files**.
3. Review tabs; resolve discrepancies per role permissions.
4. Use **Bulk Sync** only if your role allows it (supervisor/admin).

## Role permissions (desktop)

| Action | ADMIN | PM | PO | FPA |
|--------|:-----:|:--:|:--:|:---:|
| Use application | ✓ | ✓ | ✓ | **✗ (blocked at login)** |
| Bulk sync | ✓ | ✗ | ✗ | — |
| Delete from DB | ✓ | ✗ | ✗ | — |
| Delete Excel rows | ✓ | ✗ | ✗ | — |
| Bulk transfer | ✓ | ✗ | ✗ | — |
| Full replication | ✓ | ✗ | ✗ | — |
| Scan / sync / add / resolve | ✓ | ✓ | ✓ | — |

PM and PO are encoders. FPA accounts cannot sign in even with a valid access code.

## Logs

Application log file: `%APPDATA%/HAPAGComparator/hapag_comparator.log` (Windows) or `~/.config/HAPAGComparator/` (Linux).

## Updates

Updates are downloaded from GitHub Releases. When `checksums.txt` is published, the app verifies SHA256 before installing.

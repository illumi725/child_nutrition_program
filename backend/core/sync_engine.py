"""
SyncEngine: bidirectional synchronization between cloud MySQL and local SQLite.
"""
import logging
import sqlite3
import datetime

logger = logging.getLogger(__name__)
from PySide6.QtCore import QThread, Signal

ALL_TABLES = [
    'barangays', 'baseline_info', 'beneficiaries', 'beneficiaries_height_weight',
    'cities_municipalities', 'consecutive_absences', 'feeding_records', 'google_users',
    'incident_category', 'incidents_bank', 'op_areas', 'op_branches', 'op_divisions',
    'op_operations', 'op_regions', 'parents_beneficiaries', 'provinces', 'regions',
    'session', 'site_log', 'site_log_resolution', 'sites', 'supply_reporting',
    'user_has_branches', 'user_has_sites', 'users', 'word_bank'
]

def _get_cloud_conn():
    """Always returns a fresh cloud MySQL connection."""
    import pymysql
    from core._config import (CLOUD_DB_HOST, CLOUD_DB_USER, CLOUD_DB_PASSWORD,
                               CLOUD_DB_DATABASE, CLOUD_DB_PORT)
    return pymysql.connect(
        host=CLOUD_DB_HOST, user=CLOUD_DB_USER, password=CLOUD_DB_PASSWORD,
        database=CLOUD_DB_DATABASE, port=CLOUD_DB_PORT,
        cursorclass=pymysql.cursors.DictCursor, connect_timeout=10
    )

def _get_local_conn():
    """Returns a SQLite connection to the local database."""
    from core.app_settings import get_local_db_path
    path = get_local_db_path()
    conn = sqlite3.connect(path)
    conn.create_function("NOW", 0, lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn

def _mysql_to_sqlite_type(mysql_type: str) -> str:
    """Map MySQL types to SQLite affinity types."""
    t = mysql_type.upper()
    if any(x in t for x in ['INT', 'TINYINT', 'SMALLINT', 'MEDIUMINT', 'BIGINT']):
        return 'INTEGER'
    if any(x in t for x in ['FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL']):
        return 'REAL'
    if any(x in t for x in ['BLOB', 'BINARY', 'VARBINARY']):
        return 'BLOB'
    return 'TEXT'

def _ensure_sync_meta(local: sqlite3.Connection):
    """Create the sync metadata table if it doesn't exist."""
    local.execute("""
        CREATE TABLE IF NOT EXISTS _sync_meta (
            table_name TEXT PRIMARY KEY,
            last_synced_at TEXT
        )
    """)
    local.commit()

def _get_last_synced(local: sqlite3.Connection, table: str) -> str | None:
    row = local.execute(
        "SELECT last_synced_at FROM _sync_meta WHERE table_name = ?", (table,)
    ).fetchone()
    return row[0] if row else None

def _set_last_synced(local: sqlite3.Connection, table: str, ts: str):
    local.execute("""
        INSERT OR REPLACE INTO _sync_meta (table_name, last_synced_at) VALUES (?, ?)
    """, (table, ts))
    local.commit()

def _replicate_indexes(cloud, local: sqlite3.Connection, table: str):
    """Fetch indexes from MySQL and create them in SQLite."""
    try:
        with cloud.cursor() as c:
            c.execute(f"SHOW INDEX FROM `{table}`")
            indexes = c.fetchall()
    except Exception as e:
        logger.warning("Could not fetch indexes for %s: %s", table, e)
        return

    index_defs = {}
    for idx in indexes:
        key_name = idx['Key_name']
        if key_name == 'PRIMARY':
            continue  # Primary Key is already handled in table creation DDL
        
        if key_name not in index_defs:
            index_defs[key_name] = {
                'unique': idx['Non_unique'] == 0,
                'columns': []
            }
        index_defs[key_name]['columns'].append((idx['Seq_in_index'], idx['Column_name']))

    for key_name, info in index_defs.items():
        sorted_cols = sorted(info['columns'], key=lambda x: x[0])
        cols_str = ', '.join([f'"{col}"' for _, col in sorted_cols])
        
        unique_clause = "UNIQUE" if info['unique'] else ""
        idx_name = f"idx_{table}_{key_name}"
        
        ddl = f"CREATE {unique_clause} INDEX IF NOT EXISTS \"{idx_name}\" ON \"{table}\" ({cols_str})"
        try:
            local.execute(ddl)
        except Exception as e:
            logger.warning("Failed to execute index DDL %s: %s", ddl, e)
    local.commit()

def _create_sqlite_table_from_mysql(cloud, local: sqlite3.Connection, table: str):
    """Recreate the SQLite table schema based on live MySQL DESCRIBE."""
    with cloud.cursor() as c:
        c.execute(f"DESCRIBE `{table}`")
        cols = c.fetchall()

    col_defs = []
    pk_cols = []
    for col in cols:
        name = col['Field']
        sqlite_type = _mysql_to_sqlite_type(col['Type'])
        nullable = '' if col['Null'] == 'NO' else ''
        col_defs.append(f'"{name}" {sqlite_type}')
        if col['Key'] == 'PRI':
            pk_cols.append(f'"{name}"')

    pk_clause = f", PRIMARY KEY ({', '.join(pk_cols)})" if pk_cols else ""
    ddl = f"CREATE TABLE IF NOT EXISTS \"{table}\" ({', '.join(col_defs)}{pk_clause})"

    local.execute(f'DROP TABLE IF EXISTS "{table}"')
    local.execute(ddl)
    local.commit()
    
    # Auto-replicate all indexes and unique constraints from the live database table
    _replicate_indexes(cloud, local, table)

def _serialize_value(val):
    """Convert MySQL types to SQLite-compatible values."""
    if isinstance(val, (datetime.date, datetime.datetime)):
        return str(val)
    if isinstance(val, bytes):
        return val.decode('utf-8', errors='replace')
    return val

def _full_replicate_table(cloud, local: sqlite3.Connection, table: str) -> int:
    """Wipe and fully replicate a single table from cloud to local."""
    _create_sqlite_table_from_mysql(cloud, local, table)

    with cloud.cursor() as c:
        c.execute(f"SELECT * FROM `{table}`")
        rows = c.fetchall()

    if not rows:
        return 0

    keys = list(rows[0].keys())
    placeholders = ', '.join(['?' for _ in keys])
    col_names = ', '.join([f'"{k}"' for k in keys])
    insert_sql = f'INSERT OR REPLACE INTO "{table}" ({col_names}) VALUES ({placeholders})'

    data = [tuple(_serialize_value(row[k]) for k in keys) for row in rows]
    local.executemany(insert_sql, data)
    local.commit()
    return len(data)

def _push_table(cloud, local: sqlite3.Connection, table: str) -> int:
    """Push local changes (where updated_at > last_sync) up to the cloud."""
    last_sync = _get_last_synced(local, table)
    if not last_sync:
        return 0

    has_updated_at = local.execute(
        f"SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name='updated_at'"
    ).fetchone()[0]
    if not has_updated_at:
        return 0

    rows = local.execute(
        f'SELECT * FROM "{table}" WHERE updated_at > ?', (last_sync,)
    ).fetchall()
    if not rows:
        return 0

    keys = list(rows[0].keys())
    update_parts = ', '.join([f'`{k}` = %s' for k in keys if k != 'updated_at'])
    where_cols = [k for k in keys if 'id' in k.lower()]

    pushed = 0
    with cloud.cursor() as c:
        for row in rows:
            vals = {k: row[k] for k in keys}
            col_list = ', '.join([f'`{k}`' for k in keys])
            placeholder_list = ', '.join(['%s'] * len(keys))
            on_dup = ', '.join([f'`{k}`=VALUES(`{k}`)' for k in keys if k not in where_cols])
            sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholder_list}) ON DUPLICATE KEY UPDATE {on_dup}"
            c.execute(sql, [vals[k] for k in keys])
            pushed += 1
    cloud.commit()
    return pushed

def _pull_table(cloud, local: sqlite3.Connection, table: str) -> int:
    """Pull cloud changes (where updated_at > last_sync) into the local SQLite."""
    last_sync = _get_last_synced(local, table)
    if not last_sync:
        return 0

    try:
        with cloud.cursor() as c:
            c.execute(f"SHOW COLUMNS FROM `{table}` LIKE 'updated_at'")
            has_updated_at = c.fetchone()
        if not has_updated_at:
            return 0

        with cloud.cursor() as c:
            c.execute(f"SELECT * FROM `{table}` WHERE updated_at > %s", (last_sync,))
            rows = c.fetchall()
    except Exception:
        return 0

    if not rows:
        return 0

    keys = list(rows[0].keys())
    col_names = ', '.join([f'"{k}"' for k in keys])
    placeholders = ', '.join(['?' for _ in keys])
    sql = f'INSERT OR REPLACE INTO "{table}" ({col_names}) VALUES ({placeholders})'

    data = [tuple(_serialize_value(row[k]) for k in keys) for row in rows]
    local.executemany(sql, data)
    local.commit()
    return len(data)


class SyncWorker(QThread):
    progress = Signal(int, str)      # (percent, message)
    finished = Signal(bool, str)     # (success, summary)
    error = Signal(str)

    MODE_FULL   = 'full'   # First-run full replication
    MODE_SYNC   = 'sync'   # Bidirectional delta sync

    def __init__(self, mode=MODE_SYNC, parent=None):
        super().__init__(parent)
        self.mode = mode
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            if self.mode == self.MODE_FULL:
                self._run_full()
            else:
                self._run_sync()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False, str(e))

    def _run_full(self):
        """Full replication: cloud → local SQLite (first run or manual reset)."""
        self.progress.emit(0, "Connecting to cloud database...")
        cloud = _get_cloud_conn()
        local = _get_local_conn()
        _ensure_sync_meta(local)

        total = len(ALL_TABLES)
        total_rows = 0
        try:
            for i, table in enumerate(ALL_TABLES):
                if self._cancelled:
                    break
                pct = int((i / total) * 100)
                self.progress.emit(pct, f"Replicating table: {table}...")
                count = _full_replicate_table(cloud, local, table)
                ts = datetime.datetime.now().isoformat()
                _set_last_synced(local, table, ts)
                total_rows += count

            ts_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            from core.app_settings import set_last_synced
            set_last_synced(ts_now)
            self.progress.emit(100, "Replication complete!")
            self.finished.emit(True, f"Successfully replicated {total_rows:,} rows from {total} tables.")
        finally:
            cloud.close()
            local.close()

    def _run_sync(self):
        """Bidirectional delta sync."""
        self.progress.emit(0, "Connecting to databases...")
        cloud = _get_cloud_conn()
        local = _get_local_conn()
        _ensure_sync_meta(local)

        total = len(ALL_TABLES)
        pushed_total = 0
        pulled_total = 0
        try:
            for i, table in enumerate(ALL_TABLES):
                if self._cancelled:
                    break
                pct = int((i / total) * 100)
                self.progress.emit(pct, f"Syncing: {table}...")
                pushed = _push_table(cloud, local, table)
                pulled = _pull_table(cloud, local, table)
                ts = datetime.datetime.now().isoformat()
                _set_last_synced(local, table, ts)
                pushed_total += pushed
                pulled_total += pulled

            ts_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            from core.app_settings import set_last_synced
            set_last_synced(ts_now)
            self.progress.emit(100, "Sync complete!")
            self.finished.emit(True, f"↑ Pushed {pushed_total} rows  |  ↓ Pulled {pulled_total} rows")
        finally:
            cloud.close()
            local.close()

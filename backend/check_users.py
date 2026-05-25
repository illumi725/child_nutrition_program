"""Ad-hoc users table inspection (development only)."""

import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

from core.database import get_db_connection  # noqa: E402

conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("DESCRIBE users")
    logger.info("%s", cur.fetchall())
conn.close()

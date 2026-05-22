"""Ad-hoc local DB inspection script (development only)."""

import logging
import os
import sqlite3
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app_settings import get_local_db_path

db_path = get_local_db_path()
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT * FROM beneficiaries WHERE lastname LIKE '%Abacahin%'")
ben = cursor.fetchone()
logger.info("Beneficiary: %s", ben)

if ben:
    cursor.execute(
        "SELECT weight, height, age FROM baseline_info WHERE beneficiary_id=?",
        (ben[0],),
    )
    bl = cursor.fetchall()
    logger.info("Baseline: %s", bl)
conn.close()

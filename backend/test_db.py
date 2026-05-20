import sys
import os

# add backend path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app_settings import get_local_db_path
db_path = get_local_db_path()

import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT * FROM beneficiaries WHERE lastname LIKE '%Abacahin%'")
ben = cursor.fetchone()
print("Beneficiary:", ben)

if ben:
    # Print baseline_info
    cursor.execute("SELECT weight, height, age FROM baseline_info WHERE beneficiary_id=?", (ben[0],))
    bl = cursor.fetchall()
    print("Baseline:", bl)

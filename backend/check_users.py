from core.database import get_db_connection
conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("DESCRIBE users")
    print(cur.fetchall())
conn.close()

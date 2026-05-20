import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

# pyrefly: ignore [missing-import]
from core.database import add_beneficiary_to_db

def main():
    print("Testing add_beneficiary_to_db...")
    
    # We need a valid site_id. Let's fetch one from database.
    import pymysql
    # pyrefly: ignore [missing-import]
    from core._config import (CLOUD_DB_HOST, CLOUD_DB_USER, CLOUD_DB_PASSWORD,
                               CLOUD_DB_DATABASE, CLOUD_DB_PORT)
    connection = pymysql.connect(
        host=CLOUD_DB_HOST, user=CLOUD_DB_USER, password=CLOUD_DB_PASSWORD,
        database=CLOUD_DB_DATABASE, port=CLOUD_DB_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT site_id FROM sites LIMIT 1")
            site = cursor.fetchone()
            if not site:
                print("Error: No feeding sites found in the database. Cannot add.")
                return
            site_id = site['site_id']
            print(f"Using site_id: {site_id}")
    finally:
        connection.close()
        
    # Call add_beneficiary_to_db
    success, msg = add_beneficiary_to_db(
        site_id=site_id,
        lastname="TestLastName",
        firstname="TestFirstName",
        middlename="TestMiddleName",
        birthday="2020-01-01",
        gender="Boy",
        weight=15.5,
        height=95.0,
        date_collected="2026-05-20",
        created_by="12345678"  # A valid user_id or empty/existing
    )
    
    if success:
        print(f"Success! Beneficiary ID: {msg}")
    else:
        print(f"Failed! Error: {msg}")

if __name__ == "__main__":
    main()

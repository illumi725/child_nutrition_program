import pymysql
import datetime
import random
import string
import os

def get_db_creds():
    creds = {}
    db_dat_path = "/media/heathcliff/MyFiles/HAPAG APPROVED BASELINE-20260410T035243Z-3-001/db.dat"
    with open(db_dat_path, 'r') as f:
        for line in f:
            if '=' in line:
                key, val = line.strip().split('=', 1)
                creds[key] = val.strip('"')
    return creds

def get_db_connection():
    creds = get_db_creds()
    return pymysql.connect(
        host=creds.get('DB_HOST'), user=creds.get('DB_USERNAME'), password=creds.get('DB_PASSWORD'),
        database=creds.get('DB_DATABASE'), port=int(creds.get('DB_PORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

def generate_id():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

def test_insert():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            bid = generate_id()
            today_str = datetime.date.today().strftime('%Y-%m-%d')
            
            # Simulated item data
            item = {
                "lastname": "TEST", "firstname": "AUTO", "middlename": "", 
                "birthday": "2015-01-01", "gender": "BOY", "site_id": "87u76zvh", # Using a known site_id or picking one
                "weight": 20.5, "height": 110.0, "date_collected": "2026-04-15"
            }
            
            # Try to get a valid site_id first
            cursor.execute("SELECT site_id FROM sites LIMIT 1")
            site = cursor.fetchone()
            if site: item['site_id'] = site['site_id']

            print(f"Testing insert for beneficiary_id: {bid} in site: {item['site_id']}")
            
            sql_ben = """
            INSERT INTO beneficiaries 
            (beneficiary_id, lastname, firstname, middlename, birthday, gender, site_id, registration_date, created_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_ben, (
                bid, item['lastname'], item['firstname'], item['middlename'], item['birthday'], 
                item['gender'], item['site_id'], today_str, 'SYSTEM_AUTO'
            ))
            
            iid = generate_id()
            sql_bl = """
            INSERT INTO baseline_info 
            (info_id, beneficiary_id, weight, height, date_collected, bmifa_figure, bmifa_status, created_at, updated_at, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
            """
            cursor.execute(sql_bl, (
                iid, bid, item['weight'], item['height'], item['date_collected'], 
                17.5, 'NORMAL', 'SYSTEM_AUTO'
            ))
            
            conn.commit()
            print("Success!")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    test_insert()

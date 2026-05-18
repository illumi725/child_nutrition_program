import os
import pymysql
import datetime
from decimal import Decimal
from typing import List, Dict, Any

def get_db_creds():
    creds = {}
    import sys
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as normal Python script
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
    db_dat_path = os.path.join(base_dir, "db.dat")
    
    if not os.path.exists(db_dat_path): return creds
    with open(db_dat_path, 'r') as f:
        for line in f:
            if '=' in line:
                key, val = line.strip().split('=', 1)
                creds[key] = val.strip('"')
    return creds

def get_db_connection():
    creds = get_db_creds()
    host = creds.get('DB_HOST')
    db = creds.get('DB_DATABASE')
    return pymysql.connect(
        host=host, user=creds.get('DB_USERNAME'), password=creds.get('DB_PASSWORD'),
        database=db, port=int(creds.get('DB_PORT', 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

def fetch_beneficiaries() -> List[Dict[str, Any]]:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                b.beneficiary_id, b.lastname, b.firstname, b.middlename, b.birthday, b.gender, b.site_id,
                s.site_name, s.batch, br.barangay_name, cm.citymun_name, p.province_name,
                (SELECT weight FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as weight,
                (SELECT height FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as height,
                (SELECT age FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as age,
                (SELECT date_collected FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as date_collected,
                (SELECT bmifa_status FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as bmifa_status,
                (SELECT bmifa_figure FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as bmifa_figure,
                (SELECT wfa_status FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as wfa_status,
                (SELECT wfa_figure FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as wfa_figure,
                (SELECT hfa_status FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as hfa_status,
                (SELECT hfa_figure FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as hfa_figure,
                (SELECT wfh_status FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as wfh_status,
                (SELECT wfh_figure FROM baseline_info bl WHERE bl.beneficiary_id = b.beneficiary_id ORDER BY created_at DESC LIMIT 1) as wfh_figure
            FROM beneficiaries b
            LEFT JOIN sites s ON b.site_id = s.site_id
            LEFT JOIN barangays br ON s.barangay_code = br.barangay_code
            LEFT JOIN cities_municipalities cm ON s.citymun_code = cm.citymun_code
            LEFT JOIN provinces p ON s.province_code = p.province_code
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            for r in rows:
                if isinstance(r.get('weight'), Decimal): r['weight'] = float(r['weight'])
                if isinstance(r.get('height'), Decimal): r['height'] = float(r['height'])
                if isinstance(r.get('birthday'), (datetime.date, datetime.datetime)):
                    r['birthday'] = r['birthday'].strftime('%Y-%m-%d')
                if isinstance(r.get('date_collected'), (datetime.date, datetime.datetime)):
                    r['date_collected'] = r['date_collected'].strftime('%Y-%m-%d')
            return rows
    finally: connection.close()

def get_sites():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT s.site_id, s.site_name, s.batch, br.barangay_name, cm.citymun_name, p.province_name 
                FROM sites s
                LEFT JOIN barangays br ON s.barangay_code = br.barangay_code
                LEFT JOIN cities_municipalities cm ON s.citymun_code = cm.citymun_code
                LEFT JOIN provinces p ON s.province_code = p.province_code
                ORDER BY s.site_name
            """)
            return cursor.fetchall()
    finally: conn.close()

def sync_baseline(beneficiary_id, weight, height, date_collected, birthday):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Update the birthday in beneficiaries
            cursor.execute("UPDATE beneficiaries SET birthday = %s WHERE beneficiary_id = %s", (birthday, beneficiary_id))
            
            # 2. Get gender to calculate anthro stats
            cursor.execute("SELECT gender, birthday FROM beneficiaries WHERE beneficiary_id = %s", (beneficiary_id,))
            ben = cursor.fetchone()
            if not ben: return False
            
            ref_date = datetime.date.today()
            if date_collected:
                try: ref_date = datetime.datetime.strptime(date_collected, '%Y-%m-%d').date()
                except: pass
            
            bday_dt = datetime.datetime.strptime(birthday, '%Y-%m-%d').date()
            age_in_months = (ref_date.year - bday_dt.year) * 12 + ref_date.month - bday_dt.month
            
            try:
                from backend.anthro_utils import calculate_anthro_stats
            except ImportError:
                from anthro_utils import calculate_anthro_stats
                
            stats = calculate_anthro_stats(age_in_months, ben['gender'], weight, height)
            
            # 3. Update baseline_info
            sql = """
            UPDATE baseline_info SET 
                weight = %s, height = %s, age = %s, date_collected = %s,
                wfa_figure = %s, wfa_status = %s, 
                hfa_figure = %s, hfa_status = %s, 
                wfh_figure = %s, wfh_status = %s, 
                bmifa_figure = %s, bmifa_status = %s, 
                updated_at = NOW()
            WHERE beneficiary_id = %s ORDER BY created_at DESC LIMIT 1
            """
            cursor.execute(sql, (
                weight, height, age_in_months, date_collected, 
                stats.get('wfa_figure'), stats.get('wfa_status'),
                stats.get('hfa_figure'), stats.get('hfa_status'),
                stats.get('wfh_figure'), stats.get('wfh_status'),
                stats.get('bmifa_figure'), stats.get('bmifa_status'),
                beneficiary_id
            ))
            conn.commit()
            return True
    except Exception as e:
        print(f"[SYNC-ERROR] {e}")
        return False
    finally: conn.close()

def update_birthday_db(beneficiary_id, new_birthday):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Update the birthday in beneficiaries
            cursor.execute("UPDATE beneficiaries SET birthday = %s WHERE beneficiary_id = %s", (new_birthday, beneficiary_id))
            
            # 2. Get latest baseline info to recalculate anthro
            cursor.execute("""
                SELECT bl.info_id, bl.weight, bl.height, bl.date_collected, b.gender 
                FROM baseline_info bl
                JOIN beneficiaries b ON bl.beneficiary_id = b.beneficiary_id
                WHERE bl.beneficiary_id = %s
                ORDER BY bl.created_at DESC LIMIT 1
            """, (beneficiary_id,))
            
            item = cursor.fetchone()
            if item and item.get('weight') and item.get('height'):
                ref_date = datetime.date.today()
                if item.get('date_collected'):
                    try: ref_date = datetime.datetime.strptime(item['date_collected'], '%Y-%m-%d').date()
                    except: pass
                
                bday_dt = datetime.datetime.strptime(new_birthday, '%Y-%m-%d').date()
                age_in_months = (ref_date.year - bday_dt.year) * 12 + ref_date.month - bday_dt.month
                
                try:
                    from backend.anthro_utils import calculate_anthro_stats
                except ImportError:
                    from anthro_utils import calculate_anthro_stats
                    
                stats = calculate_anthro_stats(age_in_months, item['gender'], item['weight'], item['height'])
                
                # 3. Update baseline_info
                sql = """
                UPDATE baseline_info SET 
                    age = %s,
                    wfa_figure = %s, wfa_status = %s, 
                    hfa_figure = %s, hfa_status = %s, 
                    wfh_figure = %s, wfh_status = %s, 
                    bmifa_figure = %s, bmifa_status = %s, 
                    updated_at = NOW()
                WHERE info_id = %s
                """
                cursor.execute(sql, (
                    age_in_months,
                    stats.get('wfa_figure'), stats.get('wfa_status'),
                    stats.get('hfa_figure'), stats.get('hfa_status'),
                    stats.get('wfh_figure'), stats.get('wfh_status'),
                    stats.get('bmifa_figure'), stats.get('bmifa_status'),
                    item['info_id']
                ))
                
            conn.commit()
            return True
    except Exception as e:
        print(f"[BDAY-SYNC-ERROR] {e}")
        return False
    finally: conn.close()

def update_name_db(beneficiary_id, lastname, firstname, middlename):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE beneficiaries 
                SET lastname = %s, firstname = %s, middlename = %s 
                WHERE beneficiary_id = %s
            """, (lastname, firstname, middlename, beneficiary_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"[NAME-SYNC-ERROR] {e}")
        return False
    finally: conn.close()

def get_surname_dictionary():
    """
    Fetches all unique lastnames and middlenames from the database to create a dictionary of valid surnames.
    This is used to intelligently parse compound first names vs middle names.
    """
    conn = get_db_connection()
    surnames = set()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT lastname FROM beneficiaries WHERE lastname IS NOT NULL AND lastname != ''")
            for row in cursor.fetchall():
                surnames.add(row['lastname'].strip().upper())
                
            cursor.execute("SELECT DISTINCT middlename FROM beneficiaries WHERE middlename IS NOT NULL AND middlename != ''")
            for row in cursor.fetchall():
                surnames.add(row['middlename'].strip().upper())
    except Exception as e:
        print(f"[SURNAME-DICT-ERROR] {e}")
    finally:
        conn.close()
    return surnames

def generate_beneficiary_id():
    import random
    import string
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

def authenticate_user(access_code):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, firstname, lastname, role FROM users WHERE access_code = %s AND deleted_at IS NULL", (access_code,))
            return cursor.fetchone()
    except Exception as e:
        print(f"[AUTH-ERROR] {e}")
        return None
    finally:
        conn.close()

def check_email_exists(email):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE email = %s AND deleted_at IS NULL", (email,))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"[AUTH-ERROR] {e}")
        return False
    finally:
        conn.close()

def add_beneficiary_to_db(site_id, lastname, firstname, middlename, birthday, gender, weight, height, date_collected, created_by):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            beneficiary_id = generate_beneficiary_id()
            reg_date = datetime.date.today().strftime('%Y-%m-%d')

            
            # Insert into beneficiaries
            sql_ben = """
            INSERT INTO beneficiaries (beneficiary_id, lastname, firstname, middlename, birthday, gender, registration_date, site_id, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_ben, (beneficiary_id, lastname, firstname, middlename, birthday, gender.upper(), reg_date, site_id, created_by))
            
            # Insert into baseline_info
            if weight and height:
                ref_date = datetime.date.today()
                if date_collected:
                    try: ref_date = datetime.datetime.strptime(date_collected, '%Y-%m-%d').date()
                    except: pass
                
                bday_dt = datetime.datetime.strptime(birthday, '%Y-%m-%d').date()
                age_in_months = (ref_date.year - bday_dt.year) * 12 + ref_date.month - bday_dt.month
                
                try:
                    from backend.anthro_utils import calculate_anthro_stats
                except ImportError:
                    from anthro_utils import calculate_anthro_stats
                    
                stats = calculate_anthro_stats(age_in_months, gender.upper(), weight, height)
                
                sql_bl = """
                INSERT INTO baseline_info (
                    beneficiary_id, weight, height, age, date_collected,
                    wfa_figure, wfa_status, hfa_figure, hfa_status,
                    wfh_figure, wfh_status, bmifa_figure, bmifa_status,
                    created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_bl, (
                    beneficiary_id, weight, height, age_in_months, date_collected,
                    stats.get('wfa_figure'), stats.get('wfa_status'),
                    stats.get('hfa_figure'), stats.get('hfa_status'),
                    stats.get('wfh_figure'), stats.get('wfh_status'),
                    stats.get('bmifa_figure'), stats.get('bmifa_status'),
                    created_by
                ))
            
            conn.commit()
            return True, beneficiary_id
    except Exception as e:
        print(f"[ADD-BENEFICIARY-ERROR] {e}")
        return False, str(e)
    finally:
        conn.close()


def get_beneficiary_related_counts(beneficiary_id):
    """Returns record counts for all related tables for a given beneficiary_id."""
    conn = get_db_connection()
    try:
        counts = {}
        with conn.cursor() as cursor:
            tables = [
                ("feeding_records",          "feeding_records"),
                ("baseline_info",            "baseline_info"),
                ("beneficiaries_height_weight", "height_weight_records"),
                ("parents_beneficiaries",    "parent_links"),
                ("consecutive_absences",     "absence_records"),
            ]
            for table, label in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) AS cnt FROM `{table}` WHERE beneficiary_id = %s", (beneficiary_id,))
                    counts[label] = cursor.fetchone()['cnt']
                except Exception:
                    counts[label] = "N/A"
        return counts
    finally:
        conn.close()


def delete_beneficiary_cascade(beneficiary_id):
    """Hard-deletes a beneficiary and all related records in the correct dependency order."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Delete child tables first, then the parent
            for table in [
                "feeding_records",
                "baseline_info",
                "beneficiaries_height_weight",
                "parents_beneficiaries",
                "consecutive_absences",
            ]:
                try:
                    cursor.execute(f"DELETE FROM `{table}` WHERE beneficiary_id = %s", (beneficiary_id,))
                except Exception as e:
                    print(f"[CASCADE-DELETE] Warning on {table}: {e}")
            cursor.execute("DELETE FROM beneficiaries WHERE beneficiary_id = %s", (beneficiary_id,))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def find_beneficiaries_by_name(lastname: str, firstname: str):
    """
    Returns all beneficiary records whose lastname AND firstname match (case-insensitive).
    Includes related record counts for each match.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    b.beneficiary_id, b.lastname, b.firstname, b.middlename,
                    b.birthday, b.gender, s.site_name,
                    (SELECT COUNT(*) FROM feeding_records       fr WHERE fr.beneficiary_id = b.beneficiary_id) AS feeding_records,
                    (SELECT COUNT(*) FROM baseline_info         bi WHERE bi.beneficiary_id = b.beneficiary_id) AS baseline_info,
                    (SELECT COUNT(*) FROM beneficiaries_height_weight hw WHERE hw.beneficiary_id = b.beneficiary_id) AS height_weight_records,
                    (SELECT COUNT(*) FROM parents_beneficiaries pb WHERE pb.beneficiary_id = b.beneficiary_id) AS parent_links,
                    (SELECT COUNT(*) FROM consecutive_absences  ca WHERE ca.beneficiary_id = b.beneficiary_id) AS absence_records
                FROM beneficiaries b
                LEFT JOIN sites s ON b.site_id = s.site_id
                WHERE UPPER(TRIM(b.lastname))  = UPPER(TRIM(%s))
                  AND UPPER(TRIM(b.firstname)) = UPPER(TRIM(%s))
            """, (lastname, firstname))
            rows = cursor.fetchall()
            for r in rows:
                if isinstance(r.get('birthday'), (datetime.date, datetime.datetime)):
                    r['birthday'] = r['birthday'].strftime('%Y-%m-%d')
            return rows
    finally:
        conn.close()


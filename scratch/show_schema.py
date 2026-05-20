import pymysql

def get_db_creds():
    creds = {}
    with open('db.dat', 'r') as f:
        for line in f:
            if '=' in line:
                key, val = line.strip().split('=', 1)
                creds[key] = val.strip('"')
    return creds

creds = get_db_creds()
connection = pymysql.connect(
    host=creds.get('DB_HOST'),
    user=creds.get('DB_USERNAME'),
    password=creds.get('DB_PASSWORD'),
    database=creds.get('DB_DATABASE'),
    port=int(creds.get('DB_PORT', 3306)),
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        cursor.execute("SHOW CREATE TABLE baseline_info")
        print("baseline_info:")
        print(cursor.fetchone()['Create Table'])
        
        print("\n" + "="*50 + "\n")
        
        cursor.execute("SHOW CREATE TABLE beneficiaries")
        print("beneficiaries:")
        print(cursor.fetchone()['Create Table'])
finally:
    connection.close()

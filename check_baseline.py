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
        cursor.execute("DESCRIBE baseline_info")
        print("Columns:", [row['Field'] for row in cursor.fetchall()])
        
        cursor.execute("SELECT * FROM baseline_info LIMIT 3")
        for row in cursor.fetchall():
            print(row)
finally:
    connection.close()

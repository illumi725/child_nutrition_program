import pymysql

def main():
    # parse db.dat
    creds = {}
    with open('db.dat', 'r') as f:
        for line in f:
            if '=' in line:
                key, val = line.strip().split('=', 1)
                creds[key] = val.strip('"')

    print(f"Connecting to {creds.get('DB_HOST')}...")
    
    # Connect to the database
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
            # Create a new record
            sql = "SELECT * FROM beneficiaries LIMIT 5"
            cursor.execute(sql)
            result = cursor.fetchall()
            print(f"Successfully connected and queried the 'beneficiaries' table. Found {len(result)} records.")
            for row in result:
                print(row)
    finally:
        connection.close()

if __name__ == '__main__':
    main()

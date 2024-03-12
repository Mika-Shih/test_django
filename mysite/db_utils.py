import psycopg2

def connect_to_database():
    host = "localhost"
    dbname = "postgres_all"
    user = "postgres"
    password = "123456789"
    sslmode = "allow"
    conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(host, user, dbname, password, sslmode)     
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    def close_database():
        conn.commit()
        cursor.close()
        conn.close()    
    return conn, cursor, close_database
'''
INNER JOIN B ON A.character = B.master

LEFT JOIN A ON B.master = A.character
'''
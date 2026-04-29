import mysql.connector

try:
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password=""
    )

    print("MYSQL OK")

except Exception as e:
    print("ERROR:", e)
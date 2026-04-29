import mysql.connector
from config import *

def get_db():

    try:

        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )

        return conn

    except mysql.connector.Error as e:
        print("MYSQL ERROR:", e)
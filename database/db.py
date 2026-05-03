from contextlib import contextmanager

import mysql.connector
from config import *
from database.extensions import db


def get_db():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )

        return conn

    except mysql.connector.Error as e:
        print("MYSQL ERROR:", e)


def get_session():
    return db.session


@contextmanager
def session_scope():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise

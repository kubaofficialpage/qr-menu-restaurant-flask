from sqlalchemy import create_engine, text

from config import SQLALCHEMY_DATABASE_URI


try:
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("DB OK")
except Exception as exc:
    print("ERROR:", exc)
import os
from urllib.parse import quote_plus

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "qrmenu")


def build_sqlalchemy_database_uri():
    user = quote_plus(DB_USER)
    password = quote_plus(DB_PASSWORD)
    host = DB_HOST
    database = DB_NAME
    return f"mysql+mysqlconnector://{user}:{password}@{host}/{database}?charset=utf8mb4"


SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    build_sqlalchemy_database_uri(),
)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

from contextlib import contextmanager
from database.extensions import db


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

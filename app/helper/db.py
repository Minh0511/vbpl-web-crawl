import time
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from setting import setting

_logger = logging.getLogger(__name__)

db_engine = create_engine(setting.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
LocalSession = sessionmaker(autocommit=True, autoflush=True, bind=db_engine, expire_on_commit=False)


def open_db_session() -> Session:
    return LocalSession()


def db_session():
    session = LocalSession()
    try:
        yield session
    finally:
        session.close()

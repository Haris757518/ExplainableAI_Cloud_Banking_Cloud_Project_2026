from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from common.config import get_settings

class Base(DeclarativeBase):
    pass

settings=get_settings()
connect_args={"check_same_thread": False} if settings.observed_database_url.startswith("sqlite") else {}
engine=create_engine(settings.observed_database_url, future=True, connect_args={**connect_args, **({"timeout": 15} if connect_args else {})}, pool_pre_ping=True)
if settings.observed_database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, record):
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=15000')
        cursor.close()
SessionLocal=sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # create_all does not add indexes to an existing table.
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from common.config import get_settings

class Base(DeclarativeBase):
    pass

settings=get_settings()
connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine=create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal=sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

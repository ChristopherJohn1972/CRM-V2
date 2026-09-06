import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()


def database_url():
    url = os.getenv("CRM_DATABASE_URL")
    if url:
        return url
    host = os.getenv("CRM_DB_HOST", "127.0.0.1")
    port = os.getenv("CRM_DB_PORT", "3306")
    name = os.getenv("CRM_DB_NAME", "crm_v2")
    user = os.getenv("CRM_DB_USER", "root")
    password = os.getenv("CRM_DB_PASSWORD", "")
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{name}?charset=utf8mb4"
    )


engine = create_engine(
    database_url(),
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

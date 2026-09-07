import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()


def database_url():
    url = os.getenv("DATABASE_URL") or os.getenv("CRM_DATABASE_URL")
    if url:
        return url
    host = os.getenv("CRM_DB_HOST", "127.0.0.1")
    port = os.getenv("CRM_DB_PORT", "5432")
    name = os.getenv("CRM_DB_NAME", "crm_v2")
    user = os.getenv("CRM_DB_USER", "postgres")
    password = os.getenv("CRM_DB_PASSWORD", "")
    sslmode = os.getenv("CRM_DB_SSLMODE", "require")
    return (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{name}?sslmode={sslmode}"
    )


engine = create_engine(
    database_url(),
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    pool_timeout=10,
    connect_args={"connect_timeout": 10},
)


@event.listens_for(engine, "connect")
def set_connection_defaults(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET statement_timeout = '10s'")
    cursor.execute("SET lock_timeout = '5s'")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

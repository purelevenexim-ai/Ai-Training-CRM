from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL") or (
    "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "pureleven"),
        pw=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "pureleven-postgres"),
        port=os.getenv("POSTGRES_PORT", 5432),
        db=os.getenv("POSTGRES_DB", "pureleven"),
    )
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

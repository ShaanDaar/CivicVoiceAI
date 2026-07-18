import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database path (SQLite used for the prototype stage as specified in AGENTS.md)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "civicvoice.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Connect args check_same_thread is required only for SQLite
engine = create_engine(
    # Use sqlite implementation
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency generator for FastAPI to grab a DB session and close it afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

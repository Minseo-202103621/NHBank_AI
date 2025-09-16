"""Database engine and session management.

This module initialises the SQLAlchemy engine and session factory based on
the configured `DB_URL`. The `init_db` function should be called once at
startup to create the database tables defined in `models.py`.  The
`get_db` generator yields a session for each request and ensures that it is
closed after use.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import get_settings
from .models import Base


engine = None
SessionLocal = None


def init_db() -> None:
    """Initialise the database engine and create tables.

    This function reads the database URL from the settings, constructs the
    SQLAlchemy engine, and binds it to a session factory. It also creates
    all tables defined on the declarative Base. It should be idempotent.
    """

    global engine, SessionLocal
    settings = get_settings()
    database_url = settings.db_url
    connect_args = {}
    # SQLite requires special connect args for multithreaded operation
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(database_url, connect_args=connect_args, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a new database session per request.

    When used as a FastAPI dependency, this generator creates a session
    connected to the configured database and then closes it at the end of
    the request lifecycle.  If `init_db` has not been called yet it will
    automatically initialise the engine and sessionmaker.
    """

    global SessionLocal
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
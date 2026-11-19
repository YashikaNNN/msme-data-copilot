from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

engine = None
SessionLocal = None


class Base(DeclarativeBase):
    pass


def _enable_sqlite_fk(dbapi_conn, _connection_record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
    inspector = inspect(conn)
    if table not in inspector.get_table_names():
        return
    existing = {item["name"] for item in inspector.get_columns(table)}
    if column not in existing:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def ensure_auth_columns(bind) -> None:
    """Add business isolation columns on existing databases without a full rebuild."""

    with bind.begin() as conn:
        _ensure_column(conn, "datasets", "business_id", "business_id INTEGER")
        _ensure_column(conn, "chat_sessions", "business_id", "business_id INTEGER")
        _ensure_column(conn, "activity_events", "business_id", "business_id INTEGER")


def init_db() -> None:
    """Create the engine and ensure tables exist.

    Alembic is the migration path for PostgreSQL. create_all keeps local
    startup and tests aligned with the current models.
    """

    global engine, SessionLocal
    from app.config import get_settings

    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_fk)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    from app import models  # noqa: F401

    Base.metadata.create_all(engine)
    ensure_auth_columns(engine)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

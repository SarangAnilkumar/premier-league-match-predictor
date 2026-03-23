from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from pl_ingestion.database.db_config import DatabaseSettings


def _ensure_parent_dir(db_path: str) -> None:
    path = Path(db_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(settings: DatabaseSettings) -> Engine:
    _ensure_parent_dir(settings.db_path)
    engine = create_engine(
        settings.sqlalchemy_url(),
        echo=settings.echo,
        # Needed for local development when using multiple threads (or async later).
        connect_args={"check_same_thread": False} if settings.sqlalchemy_url().startswith("sqlite") else {},
        future=True,
    )

    # Ensure SQLite foreign key constraints are enforced.
    if settings.sqlalchemy_url().startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


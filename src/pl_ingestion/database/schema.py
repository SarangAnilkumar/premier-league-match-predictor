from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text

from pl_ingestion.database.models import Base

def _sqlite_add_column_if_missing(engine: Engine, table_name: str, column_name: str, ddl: str) -> None:
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns(table_name)}
    if column_name in columns:
        return
    with engine.begin() as conn:
        conn.execute(text(ddl))


def create_schema(engine: Engine) -> None:
    """
    Create all tables for the current schema (SQLite-first).

    Notes:
    - For local development we also attempt lightweight column additions for SQLite
      so schema updates don’t require manual DB deletion every time.
    - Production should move to migrations.
    """

    Base.metadata.create_all(bind=engine)

    # Lightweight SQLite schema evolution (best-effort).
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "ingestion_runs" not in inspector.get_table_names():
        return

    # Add columns if missing (db may have been created from an older schema).
    _sqlite_add_column_if_missing(
        engine,
        "ingestion_runs",
        "run_key",
        "ALTER TABLE ingestion_runs ADD COLUMN run_key TEXT",
    )
    _sqlite_add_column_if_missing(
        engine,
        "ingestion_runs",
        "run_type",
        "ALTER TABLE ingestion_runs ADD COLUMN run_type TEXT",
    )
    _sqlite_add_column_if_missing(
        engine,
        "ingestion_runs",
        "records_written",
        "ALTER TABLE ingestion_runs ADD COLUMN records_written INTEGER",
    )

    _sqlite_add_column_if_missing(
        engine,
        "ingestion_runs",
        "fetched_from_api",
        "ALTER TABLE ingestion_runs ADD COLUMN fetched_from_api INTEGER",
    )
    _sqlite_add_column_if_missing(
        engine,
        "ingestion_runs",
        "cache_hit",
        "ALTER TABLE ingestion_runs ADD COLUMN cache_hit INTEGER",
    )

    # Fixture lineups schema additions (for lineup ingestion).
    if "fixture_lineups" in inspector.get_table_names():
        for column_name, ddl in [
            ("formation", "ALTER TABLE fixture_lineups ADD COLUMN formation TEXT"),
            ("player_name", "ALTER TABLE fixture_lineups ADD COLUMN player_name TEXT"),
            ("grid", "ALTER TABLE fixture_lineups ADD COLUMN grid TEXT"),
            ("lineup_type", "ALTER TABLE fixture_lineups ADD COLUMN lineup_type TEXT"),
        ]:
            _sqlite_add_column_if_missing(engine, "fixture_lineups", column_name, ddl)

    # Ensure unique constraint for run_key (required for deterministic upserts).
    # SQLite can’t add constraints via ALTER TABLE; create a unique index instead.
    indexes = {idx["name"] for idx in inspector.get_indexes("ingestion_runs")}
    if "ux_ingestion_runs_run_key" not in indexes:
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE UNIQUE INDEX ux_ingestion_runs_run_key ON ingestion_runs (run_key)"))
        except Exception:
            # If run_key contains duplicates, unique index creation will fail;
            # in that scenario the user should re-init the DB.
            pass



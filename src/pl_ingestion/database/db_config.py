from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class DatabaseSettings:
    """
    Database configuration loaded from environment variables.
    """

    # SQLite path for local development. Example: data/pl_ingestion.sqlite
    db_path: str

    # SQLAlchemy echo (useful for local debugging)
    echo: bool

    @staticmethod
    def from_env() -> "DatabaseSettings":
        db_path = os.getenv("PL_DB_PATH", None) or os.getenv("DB_PATH", None) or "data/pl_ingestion.sqlite"
        echo = (os.getenv("DB_ECHO", "false").strip().lower() in {"1", "true", "yes", "y"})
        return DatabaseSettings(db_path=db_path, echo=echo)

    def sqlalchemy_url(self) -> str:
        # Use SQLite file for now (developer-friendly, zero setup).
        return f"sqlite:///{self.db_path}"


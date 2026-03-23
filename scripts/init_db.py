from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pl_ingestion.database.db_config import DatabaseSettings
from pl_ingestion.database.connection import create_db_engine
from pl_ingestion.database.schema import create_schema


def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    settings = DatabaseSettings.from_env()
    engine = create_db_engine(settings)
    create_schema(engine)

    logging.getLogger(__name__).info("Database initialized at: %s", settings.db_path)


if __name__ == "__main__":
    main()


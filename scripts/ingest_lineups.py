from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pl_ingestion.api_football_client import APIFootballClient
from pl_ingestion.config import Settings
from pl_ingestion.database.db_config import DatabaseSettings
from pl_ingestion.database.connection import create_db_engine, make_session_factory
from pl_ingestion.database.schema import create_schema
from pl_ingestion.ingestion.fixture_lineups_ingestor import FixtureLineupsIngestor


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest API-Football fixture lineups into SQLite.")
    parser.add_argument(
        "--fixture-ids",
        required=True,
        help="Comma-separated fixture IDs to ingest (e.g. --fixture-ids 1208021,1208022).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refetching lineups even if DB already contains lineup rows for the fixture.",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        help="Write compact JSON (for smaller raw payloads).",
    )
    return parser.parse_args()


def parse_fixture_ids(value: str) -> List[int]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    fixture_ids: list[int] = []
    for p in parts:
        fixture_ids.append(int(p))
    return fixture_ids


def main() -> None:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

    settings = Settings.from_env()
    setup_logging(settings.log_level)

    args = parse_args()
    fixture_ids = parse_fixture_ids(args.fixture_ids)

    client = APIFootballClient(
        base_url=settings.api_football_base_url,
        api_key=settings.api_football_api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )

    db_settings = DatabaseSettings.from_env()
    engine = create_db_engine(db_settings)
    create_schema(engine)
    session_factory = make_session_factory(engine)

    ingestor = FixtureLineupsIngestor(
        settings=settings,
        client=client,
        session_factory=session_factory,
    )

    results = ingestor.ingest(
        fixture_ids=fixture_ids,
        force_refresh=args.force_refresh,
        pretty_json=not args.no_pretty,
    )

    used_cache_count = sum(1 for r in results if r.used_cache)
    logging.getLogger(__name__).info(
        "Lineups ingestion complete: total=%s used_cache=%s fetched=%s",
        len(results),
        used_cache_count,
        len(results) - used_cache_count,
    )


if __name__ == "__main__":
    main()


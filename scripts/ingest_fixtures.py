from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# Allow running without installing the package: add ./src to PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pl_ingestion.api_football_client import APIFootballClient
from pl_ingestion.config import Settings
from pl_ingestion.ingestion.fixtures_ingestor import FixturesIngestor
from pl_ingestion.database.db_config import DatabaseSettings
from pl_ingestion.database.connection import create_db_engine, make_session_factory
from pl_ingestion.database.schema import create_schema


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest API-Football Premier League fixtures.")
    parser.add_argument("--season", default=None, help="Season year to fetch (overrides env).")
    parser.add_argument(
        "--status",
        default=None,
        help=(
            "Optional fixture status filter (API parameter). "
            "Example: FT-AET-PEN for completed matches."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write raw JSON (overrides default).",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        help="Write compact JSON (for smaller files).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force fetching fixtures from the external API even if SQLite already has cached data.",
    )
    return parser.parse_args()


def main() -> None:
    # Loads local .env if present; production can provide env vars directly.
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

    settings = Settings.from_env()
    setup_logging(settings.log_level)

    args = parse_args()
    output_dir: Optional[Path] = Path(args.output_dir) if args.output_dir else None

    client = APIFootballClient(
        base_url=settings.api_football_base_url,
        api_key=settings.api_football_api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )

    db_settings = DatabaseSettings.from_env()
    engine = create_db_engine(db_settings)
    # Ensure schema exists (and performs lightweight SQLite evolution).
    create_schema(engine)
    session_factory = make_session_factory(engine)

    ingestor = FixturesIngestor(settings=settings, client=client, session_factory=session_factory)
    result = ingestor.ingest(
        season=args.season,
        status=args.status,
        output_dir=output_dir,
        pretty_json=not args.no_pretty,
        force_refresh=args.force_refresh,
    )

    logging.getLogger(__name__).info(
        "Ingestion complete: saved_path=%s used_cache=%s cleaned_path=%s",
        result.saved_path,
        result.used_cache,
        result.cleaned_path,
    )


if __name__ == "__main__":
    main()


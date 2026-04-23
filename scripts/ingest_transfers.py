from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pl_ingestion.api_football_client import APIFootballClient
from pl_ingestion.config import Settings
from pl_ingestion.database.connection import create_db_engine, make_session_factory
from pl_ingestion.database.db_config import DatabaseSettings
from pl_ingestion.database.schema import create_schema
from pl_ingestion.ingestion.transfers_ingestor import TransfersIngestor


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest API-Football transfers into SQLite.")
    parser.add_argument("--season", default=None, help="Season year to build transfer slice for (overrides env).")
    parser.add_argument(
        "--raw-path",
        default=None,
        help=(
            "Optional path to an existing saved raw transfers JSON file to load from. "
            "When provided, no external API calls are made."
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
        "--sleep-seconds-between-requests",
        type=float,
        default=0.0,
        help="Sleep after each team-level transfer request to reduce rate-limit pressure.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

    settings = Settings.from_env()
    setup_logging(settings.log_level)

    args = parse_args()
    output_dir: Optional[Path] = Path(args.output_dir) if args.output_dir else None
    raw_path: Optional[Path] = Path(args.raw_path) if args.raw_path else None

    client = APIFootballClient(
        base_url=settings.api_football_base_url,
        api_key=settings.api_football_api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )

    db_settings = DatabaseSettings.from_env()
    engine = create_db_engine(db_settings)
    create_schema(engine)
    session_factory = make_session_factory(engine)

    ingestor = TransfersIngestor(
        settings=settings,
        client=client,
        session_factory=session_factory,
    )

    if raw_path is not None:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        # Reuse internal ingest flow but skip API calls by directly invoking loader path.
        # The raw file format is a list of {"team_id": ..., "payload": {...}}.
        from pl_ingestion.transform.transfers_transformer import transform_transfers  # noqa: E402
        from pl_ingestion.database.connection import session_scope  # noqa: E402
        from pl_ingestion.database.transfers_loader import load_transfers_to_db  # noqa: E402

        season_to_use = args.season or settings.api_football_season
        source_name = "api_football"
        endpoint = "transfers"
        run_type = "transfers"
        run_key = f"{source_name}:{endpoint}:{run_type}:league_id={settings.api_football_league_id}:season={season_to_use}"

        transfer_rows = []
        for item in raw if isinstance(raw, list) else []:
            payload = item.get("payload") if isinstance(item, dict) else None
            if isinstance(payload, dict):
                transfer_rows.extend(transform_transfers(payload))

        with session_scope(session_factory) as session:
            write_result = load_transfers_to_db(
                session,
                source_name=source_name,
                endpoint=endpoint,
                run_type=run_type,
                run_key=run_key,
                season=season_to_use,
                raw_payload_path=raw_path,
                transfer_rows=transfer_rows,
            )

        logging.getLogger(__name__).info(
            "Transfers loaded from raw: season=%s rows=%s teams_upserted=%s players_upserted=%s saved_path=%s",
            season_to_use,
            int(write_result.get("transfers_upserted", 0)),
            int(write_result.get("teams_upserted", 0)),
            int(write_result.get("players_upserted", 0)),
            raw_path,
        )
        return

    result = ingestor.ingest(
        season=args.season,
        output_dir=output_dir,
        pretty_json=not args.no_pretty,
        sleep_seconds_between_requests=args.sleep_seconds_between_requests,
    )

    logging.getLogger(__name__).info(
        "Transfers ingestion complete: season=%s team_count=%s records_written=%s saved_path=%s",
        result.season,
        result.team_count,
        result.records_written,
        result.saved_path,
    )


if __name__ == "__main__":
    main()

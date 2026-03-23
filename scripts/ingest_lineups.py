from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pl_ingestion.api_football_client import APIFootballClient
from pl_ingestion.config import Settings
from pl_ingestion.database.db_config import DatabaseSettings
from pl_ingestion.database.connection import create_db_engine, make_session_factory
from pl_ingestion.database.schema import create_schema
from pl_ingestion.ingestion.fixture_lineups_ingestor import FixtureLineupsIngestor
from pl_ingestion.database.connection import session_scope
from pl_ingestion.selection.fixtures_selector import (
    select_fixture_ids_by_round,
    select_fixture_ids_by_team,
    select_fixture_ids_first_n_in_season,
)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest API-Football fixture lineups into SQLite.")
    parser.add_argument(
        "--fixture-ids",
        required=False,
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
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Process fixture IDs in chunks of this size (for progress + safety).",
    )

    parser.add_argument(
        "--sleep-seconds-between-requests",
        type=float,
        default=0.0,
        help="Sleep this many seconds after each API-backed fixture lineups request (useful to avoid rate limits).",
    )
    parser.add_argument(
        "--sleep-seconds-between-batches",
        type=float,
        default=0.0,
        help="Sleep this many seconds after each batch completes.",
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=None,
        help="Stop cleanly after this many fixture_ids fail (status=error).",
    )

    # Fixture selection helpers (DB-first).
    parser.add_argument(
        "--season",
        type=str,
        default=None,
        help="Select fixtures from this season (e.g. 2024). Required for selection helpers.",
    )
    parser.add_argument(
        "--first-n",
        type=int,
        default=None,
        help="Select first N fixtures in --season (by date_utc then fixture_id).",
    )
    parser.add_argument(
        "--round",
        type=str,
        default=None,
        help="Select fixtures matching this round value in --season (exact match against fixtures.round).",
    )
    parser.add_argument(
        "--team-id",
        type=int,
        default=None,
        help="Select fixtures where this team is either home or away (requires --season).",
    )
    parser.add_argument(
        "--team-name",
        type=str,
        default=None,
        help="Select fixtures where this team name matches Team.name (requires --season).",
    )
    return parser.parse_args()


def parse_fixture_ids(value: str) -> List[int]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    fixture_ids: list[int] = []
    for p in parts:
        fixture_ids.append(int(p))
    return fixture_ids


def _unique_preserve_order(items: list[int]) -> list[int]:
    # Simple stable de-dupe for fixture_id lists.
    seen: set[int] = set()
    out: list[int] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _select_fixture_ids_from_db(
    *,
    session_factory,
    args: argparse.Namespace,
) -> list[int]:
    if not args.season:
        raise ValueError("Missing --season. It is required when not using --fixture-ids.")

    selection_modes = [
        ("first_n", args.first_n is not None),
        ("round", args.round is not None),
        ("team", args.team_id is not None or args.team_name is not None),
    ]
    enabled = [name for name, on in selection_modes if on]
    if len(enabled) != 1:
        raise ValueError(
            f"Specify exactly one selection mode when not using --fixture-ids. Got: {enabled}"
        )

    season = args.season
    with session_scope(session_factory) as session:
        if enabled[0] == "first_n":
            if args.first_n is None:
                raise ValueError("--first-n must be set when using first-n selection mode.")
            return select_fixture_ids_first_n_in_season(session, season=season, first_n=args.first_n)
        if enabled[0] == "round":
            if not args.round:
                raise ValueError("--round must be set when using round selection mode.")
            return select_fixture_ids_by_round(session, season=season, round_value=args.round)
        if enabled[0] == "team":
            if args.team_id is None and not args.team_name:
                raise ValueError("Either --team-id or --team-name must be set for team selection mode.")
            return select_fixture_ids_by_team(
                session,
                season=season,
                team_id=args.team_id,
                team_name=args.team_name,
            )

    raise RuntimeError("Unexpected selection mode configuration.")


def main() -> None:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

    settings = Settings.from_env()
    setup_logging(settings.log_level)

    args = parse_args()

    client = APIFootballClient(
        base_url=settings.api_football_base_url,
        api_key=settings.api_football_api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )

    db_settings = DatabaseSettings.from_env()
    engine = create_db_engine(db_settings)
    create_schema(engine)
    session_factory = make_session_factory(engine)

    # Decide the fixture ID list to ingest.
    if args.fixture_ids:
        # If explicit fixture ids are provided, avoid ambiguity with selection flags.
        if any(
            x is not None
            for x in [args.season, args.first_n, args.round, args.team_id, args.team_name]
        ):
            raise ValueError("Do not combine --fixture-ids with DB selection flags (--season/--first-n/--round/--team-id/--team-name).")
        fixture_ids = parse_fixture_ids(args.fixture_ids)
    else:
        fixture_ids = _select_fixture_ids_from_db(session_factory=session_factory, args=args)

    fixture_ids = _unique_preserve_order(fixture_ids)

    ingestor = FixtureLineupsIngestor(
        settings=settings,
        client=client,
        session_factory=session_factory,
    )

    results = ingestor.ingest(
        fixture_ids=fixture_ids,
        force_refresh=args.force_refresh,
        batch_size=args.batch_size,
        pretty_json=not args.no_pretty,
        sleep_seconds_between_requests=args.sleep_seconds_between_requests,
        sleep_seconds_between_batches=args.sleep_seconds_between_batches,
        max_failures=args.max_failures,
    )

    used_cache_count = sum(1 for r in results if r.used_cache)
    error_count = sum(1 for r in results if r.status == "error")
    processed_fixture_ids = [r.fixture_id for r in results]
    processed_set = set(processed_fixture_ids)
    not_completed_fixture_ids = [fid for fid in fixture_ids if fid not in processed_set]
    logging.getLogger(__name__).info(
        "Lineups ingestion complete: total=%s processed=%s used_cache=%s fetched=%s errors=%s failures=%s remaining=%s",
        len(results),
        len(processed_fixture_ids),
        used_cache_count,
        len(results) - used_cache_count - error_count,
        error_count,
        error_count,
        len(not_completed_fixture_ids),
    )

    if not_completed_fixture_ids:
        preview = not_completed_fixture_ids[:50]
        suffix = "" if len(not_completed_fixture_ids) <= len(preview) else f" (+{len(not_completed_fixture_ids) - len(preview)} more)"
        logging.getLogger(__name__).warning(
            "Lineups ingestion stopped before completing %s fixture_ids (preview): %s%s",
            len(not_completed_fixture_ids),
            ",".join(str(x) for x in preview),
            suffix,
        )


if __name__ == "__main__":
    main()


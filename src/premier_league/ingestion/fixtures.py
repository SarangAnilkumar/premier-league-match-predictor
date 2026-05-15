from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import sessionmaker, Session

from premier_league.clients.api_football import APIFootballClient, FixturesQuery
from premier_league.config import Settings
from premier_league.ingestion.fixtures_cache import decide_fixtures_refresh
from premier_league.transform.fixtures import transform_fixtures
from premier_league.io.artifacts import coerce_output_dir, save_json
from premier_league.paths import FIXTURES_CLEANED_JSON
from premier_league.database.connection import session_scope
from premier_league.database.loaders.fixtures import load_fixtures_to_db, record_fixtures_cache_hit_run


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FixturesIngestResult:
    """
    Returned by ingestion so the runner can log/act on outcomes.
    """

    season: str
    league_id: int
    saved_path: Path
    cleaned_path: Path
    raw_response_keys: Optional[list[str]] = None
    used_cache: bool = False


class FixturesIngestor:
    def __init__(
        self,
        *,
        settings: Settings,
        client: APIFootballClient,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.settings = settings
        self.client = client
        self.session_factory = session_factory

    def ingest(
        self,
        *,
        season: Optional[str] = None,
        status: Optional[str] = None,
        output_dir: Optional[Path] = None,
        pretty_json: bool = True,
        force_refresh: bool = False,
    ) -> FixturesIngestResult:
        season_to_use = season or self.settings.api_football_season
        query = FixturesQuery(
            league_id=self.settings.api_football_league_id,
            season=season_to_use,
            status=status,
        )

        # Keep processed output path deterministic for downstream analytics/ML.
        cleaned_path = FIXTURES_CLEANED_JSON

        out_dir = coerce_output_dir(output_dir)
        out_path = out_dir / f"fixtures_league_{query.league_id}_season_{query.season}.json"

        run_type = "fixtures"
        endpoint = "fixtures"
        source_name = "api_football"
        status_key = status or "ALL"
        run_key = f"{source_name}:{endpoint}:{run_type}:league_id={query.league_id}:season={query.season}:status={status_key}"

        # Decide whether to call the external API based on cached DB state.
        with session_scope(self.session_factory) as session:
            decision = decide_fixtures_refresh(
                session=session,
                league_id=query.league_id,
                season=query.season,
                force_refresh=force_refresh,
            )

            if not decision.should_fetch:
                raw_payload_path = out_path if out_path.exists() else None
                record_fixtures_cache_hit_run(
                    session,
                    run_key=run_key,
                    source_name=source_name,
                    endpoint=endpoint,
                    run_type=run_type,
                    league_id=query.league_id,
                    season=query.season,
                    raw_payload_path=raw_payload_path,
                )

                return FixturesIngestResult(
                    season=query.season,
                    league_id=query.league_id,
                    saved_path=out_path,
                    cleaned_path=cleaned_path,
                    used_cache=True,
                )

        # Production-minded error handling: surface errors but keep logs useful.
        try:
            raw: Dict[str, Any] = self.client.get_fixtures(query)
        except Exception:
            logger.exception(
                "Failed to fetch fixtures for league_id=%s season=%s status=%s",
                query.league_id,
                query.season,
                query.status,
            )
            raise

        save_json(raw, out_path, pretty=pretty_json)

        cleaned = transform_fixtures(raw)
        save_json(cleaned, cleaned_path, pretty=pretty_json)

        # Load into SQLite after transformation so the DB becomes the system of record.
        with session_scope(self.session_factory) as session:
            load_fixtures_to_db(
                session,
                source_name=source_name,
                endpoint=endpoint,
                run_type=run_type,
                run_key=run_key,
                season=query.season,
                league_id=query.league_id,
                raw_payload_path=out_path,
                cleaned_fixtures=cleaned,
            )

        return FixturesIngestResult(
            season=query.season,
            league_id=query.league_id,
            saved_path=out_path,
            cleaned_path=cleaned_path,
            raw_response_keys=list(raw.keys()),
            used_cache=False,
        )


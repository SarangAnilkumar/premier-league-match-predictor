from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pl_ingestion.api_football_client import APIFootballClient, FixtureLineupsQuery
from pl_ingestion.config import Settings
from pl_ingestion.database.connection import session_scope
from pl_ingestion.database.lineups_loader import (
    record_fixture_lineups_cache_hit_run,
    upsert_fixture_lineups,
)
from pl_ingestion.database.models import Fixture
from pl_ingestion.ingestion.fixture_lineups_cache_service import decide_fixture_lineups_refresh
from pl_ingestion.transform.lineups_transformer import transform_lineups
from pl_ingestion.utils import save_json


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FixtureLineupsIngestResult:
    fixture_id: int
    used_cache: bool
    raw_payload_path: Optional[Path]
    records_written: Optional[int]


class FixtureLineupsIngestor:
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
        fixture_ids: list[int],
        force_refresh: bool,
        pretty_json: bool = True,
    ) -> list[FixtureLineupsIngestResult]:
        results: list[FixtureLineupsIngestResult] = []

        for fixture_id in fixture_ids:
            endpoint = "fixtures/lineups"
            run_type = "fixture_lineups"
            source_name = "api_football"
            run_key = f"{source_name}:{endpoint}:{run_type}:fixture_id={fixture_id}"

            raw_payload_path = (
                Path("data") / "raw" / "api_football" / f"lineups_fixture_{fixture_id}.json"
            )

            # Cache decision.
            with session_scope(self.session_factory) as session:
                decision = decide_fixture_lineups_refresh(
                    session=session,
                    fixture_id=fixture_id,
                    force_refresh=force_refresh,
                )

                if not decision.should_fetch:
                    fixture_row = session.execute(select(Fixture).where(Fixture.fixture_id == fixture_id)).scalar_one_or_none()
                    season = getattr(fixture_row, "season", None) if fixture_row else None
                    league_id = getattr(fixture_row, "league_id", None) if fixture_row else None

                    record_fixture_lineups_cache_hit_run(
                        session,
                        run_key=run_key,
                        source_name=source_name,
                        endpoint=endpoint,
                        run_type=run_type,
                        fixture_id=fixture_id,
                        season=season,
                        league_id=league_id,
                        raw_payload_path=raw_payload_path if raw_payload_path.exists() else None,
                    )

                    results.append(
                        FixtureLineupsIngestResult(
                            fixture_id=fixture_id,
                            used_cache=True,
                            raw_payload_path=raw_payload_path if raw_payload_path.exists() else None,
                            records_written=0,
                        )
                    )
                    continue

            # API-backed load.
            query = FixtureLineupsQuery(fixture_id=fixture_id)
            try:
                raw: Dict[str, Any] = self.client.get_fixture_lineups(query)
            except Exception:
                logger.exception("Failed to fetch fixture lineups fixture_id=%s", fixture_id)
                raise

            save_json(raw, raw_payload_path, pretty=pretty_json)

            lineup_records = transform_lineups(raw, fixture_id=fixture_id)

            # DB upsert.
            with session_scope(self.session_factory) as session:
                # Loader will infer season/league + map team IDs by name/side.
                records = upsert_fixture_lineups(
                    session,
                    source_name=source_name,
                    endpoint=endpoint,
                    run_type=run_type,
                    run_key=run_key,
                    fixture_id=fixture_id,
                    raw_payload_path=raw_payload_path,
                    lineup_records=lineup_records,
                )

                results.append(
                    FixtureLineupsIngestResult(
                        fixture_id=fixture_id,
                        used_cache=False,
                        raw_payload_path=raw_payload_path,
                        records_written=records.get("records_written"),
                    )
                )

        return results


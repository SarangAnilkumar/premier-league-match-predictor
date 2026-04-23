from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from pl_ingestion.api_football_client import APIFootballClient, TransfersQuery
from pl_ingestion.config import Settings
from pl_ingestion.database.connection import session_scope
from pl_ingestion.database.models import Fixture
from pl_ingestion.database.transfers_loader import load_transfers_to_db
from pl_ingestion.transform.transfers_transformer import transform_transfers
from pl_ingestion.utils import coerce_output_dir, save_json


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransfersIngestResult:
    season: str
    team_count: int
    saved_path: Path
    records_written: int
    raw_response_count: int


class TransfersIngestor:
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

    def _select_season_team_ids(self, *, season: str) -> list[int]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(Fixture.home_team_id, Fixture.away_team_id).where(
                    Fixture.season == season,
                    or_(Fixture.home_team_id.is_not(None), Fixture.away_team_id.is_not(None)),
                )
            ).all()

        team_ids: set[int] = set()
        for home_id, away_id in rows:
            if isinstance(home_id, int):
                team_ids.add(home_id)
            if isinstance(away_id, int):
                team_ids.add(away_id)
        return sorted(team_ids)

    def ingest(
        self,
        *,
        season: Optional[str] = None,
        output_dir: Optional[Path] = None,
        pretty_json: bool = True,
        sleep_seconds_between_requests: float = 0.0,
    ) -> TransfersIngestResult:
        season_to_use = season or self.settings.api_football_season
        team_ids = self._select_season_team_ids(season=season_to_use)
        if not team_ids:
            raise ValueError(
                f"No teams found in fixtures table for season={season_to_use}. "
                "Ingest fixtures first for this season."
            )

        out_dir = coerce_output_dir(output_dir)
        out_path = out_dir / f"transfers_league_{self.settings.api_football_league_id}_season_{season_to_use}.json"

        source_name = "api_football"
        endpoint = "transfers"
        run_type = "transfers"
        run_key = (
            f"{source_name}:{endpoint}:{run_type}:"
            f"league_id={self.settings.api_football_league_id}:season={season_to_use}"
        )

        raw_payloads: list[dict[str, Any]] = []
        all_rows: list[dict[str, Any]] = []
        for i, team_id in enumerate(team_ids):
            payload = self.client.get_transfers(TransfersQuery(team_id=team_id))
            raw_payloads.append({"team_id": team_id, "payload": payload})
            all_rows.extend(transform_transfers(payload))

            if sleep_seconds_between_requests > 0 and i < len(team_ids) - 1:
                time.sleep(sleep_seconds_between_requests)

        save_json(raw_payloads, out_path, pretty=pretty_json)

        with session_scope(self.session_factory) as session:
            write_result = load_transfers_to_db(
                session,
                source_name=source_name,
                endpoint=endpoint,
                run_type=run_type,
                run_key=run_key,
                season=season_to_use,
                raw_payload_path=out_path,
                transfer_rows=all_rows,
            )

        return TransfersIngestResult(
            season=season_to_use,
            team_count=len(team_ids),
            saved_path=out_path,
            records_written=int(write_result.get("records_written", 0)),
            raw_response_count=len(raw_payloads),
        )

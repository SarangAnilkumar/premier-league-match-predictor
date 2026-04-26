from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from pl_ingestion.database.fixtures_loader import _upsert_ingestion_run
from pl_ingestion.database.models import Player, Team, Transfer


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


def _upsert_transfer_teams_and_players(
    session: Session,
    *,
    source_name: str,
    raw_payload_path: Optional[Path],
    rows: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Ensure reference rows exist so transfer FK constraints can't fail.
    Transfers can reference clubs/players outside the fixtures/lineups universe.
    """
    now = _utcnow()
    payload_path_str = str(raw_payload_path) if raw_payload_path else None

    team_by_id: dict[int, dict[str, Any]] = {}
    player_by_id: dict[int, dict[str, Any]] = {}

    for r in rows:
        from_id = r.get("from_team_id")
        to_id = r.get("to_team_id")
        if isinstance(from_id, int):
            team_by_id.setdefault(from_id, {"id": from_id, "name": r.get("from_team_name")})
        if isinstance(to_id, int):
            team_by_id.setdefault(to_id, {"id": to_id, "name": r.get("to_team_name")})

        pid = r.get("player_id")
        if isinstance(pid, int):
            player_by_id.setdefault(pid, {"id": pid, "name": r.get("player_name")})

    teams_written = 0
    if team_by_id:
        stmt = sqlite_insert(Team).values(
            [
                {
                    "id": t["id"],
                    "name": t.get("name"),
                    "source_name": source_name,
                    "ingested_at": now,
                    "last_refreshed_at": now,
                    "raw_payload_path": payload_path_str,
                    "updated_at": now,
                }
                for t in team_by_id.values()
            ]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "source_name": stmt.excluded.source_name,
                "ingested_at": stmt.excluded.ingested_at,
                "last_refreshed_at": stmt.excluded.last_refreshed_at,
                "raw_payload_path": stmt.excluded.raw_payload_path,
                "updated_at": now,
            },
        )
        session.execute(stmt)
        teams_written = len(team_by_id)

    players_written = 0
    if player_by_id:
        stmt = sqlite_insert(Player).values(
            [
                {
                    "id": p["id"],
                    "name": p.get("name"),
                    "source_name": source_name,
                    "ingested_at": now,
                    "last_refreshed_at": now,
                    "raw_payload_path": payload_path_str,
                    "updated_at": now,
                }
                for p in player_by_id.values()
            ]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "source_name": stmt.excluded.source_name,
                "ingested_at": stmt.excluded.ingested_at,
                "last_refreshed_at": stmt.excluded.last_refreshed_at,
                "raw_payload_path": stmt.excluded.raw_payload_path,
                "updated_at": now,
            },
        )
        session.execute(stmt)
        players_written = len(player_by_id)

    return {"teams_upserted": teams_written, "players_upserted": players_written}


def load_transfers_to_db(
    session: Session,
    *,
    source_name: str,
    endpoint: str,
    run_type: str,
    run_key: str,
    season: str,
    raw_payload_path: Optional[Path],
    transfer_rows: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Replace transfer rows for a given season/source with newly ingested rows.
    """
    started_at = _utcnow()
    _upsert_ingestion_run(
        session,
        run_key=run_key,
        source_name=source_name,
        endpoint=endpoint,
        run_type=run_type,
        league_id=None,
        season=season,
        status="running",
        started_at=started_at,
        completed_at=None,
        error_message=None,
        raw_payload_path=raw_payload_path,
        records_written=None,
        fetched_from_api=1,
        cache_hit=0,
    )

    try:
        # Prevent duplicates across repeated team-level pulls.
        unique_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
        for row in transfer_rows:
            if row.get("season") != season:
                continue
            key = (
                row.get("season"),
                row.get("transfer_date"),
                row.get("player_id"),
                row.get("from_team_id"),
                row.get("to_team_id"),
                row.get("in_out"),
                row.get("fee_amount"),
            )
            unique_rows[key] = row

        payload_path_str = str(raw_payload_path) if raw_payload_path else None
        now = _utcnow()

        # Ensure referenced teams/players exist to satisfy FKs.
        ref_result = _upsert_transfer_teams_and_players(
            session,
            source_name=source_name,
            raw_payload_path=raw_payload_path,
            rows=list(unique_rows.values()),
        )

        # Rebuild season partition for idempotency.
        session.execute(
            delete(Transfer).where(
                Transfer.season == season,
                Transfer.source_name == source_name,
            )
        )

        transfers_written = 0
        rows_to_write = list(unique_rows.values())
        if rows_to_write:
            stmt = sqlite_insert(Transfer).values(
                [
                    {
                        "season": r.get("season"),
                        "transfer_period": r.get("transfer_period"),
                        "transfer_date": r.get("transfer_date"),
                        "player_id": r.get("player_id"),
                        "from_team_id": r.get("from_team_id"),
                        "to_team_id": r.get("to_team_id"),
                        "player_name": r.get("player_name"),
                        "in_out": r.get("in_out"),
                        "fee_amount": r.get("fee_amount"),
                        "source_name": source_name,
                        "ingested_at": now,
                        "last_refreshed_at": now,
                        "raw_payload_path": payload_path_str,
                        "updated_at": now,
                    }
                    for r in rows_to_write
                ]
            )
            session.execute(stmt)
            transfers_written = len(rows_to_write)

        completed_at = _utcnow()
        _upsert_ingestion_run(
            session,
            run_key=run_key,
            source_name=source_name,
            endpoint=endpoint,
            run_type=run_type,
            league_id=None,
            season=season,
            status="success",
            started_at=started_at,
            completed_at=completed_at,
            error_message=None,
            raw_payload_path=raw_payload_path,
            records_written=transfers_written,
            fetched_from_api=1,
            cache_hit=0,
        )

        return {
            "teams_upserted": int(ref_result.get("teams_upserted", 0)),
            "players_upserted": int(ref_result.get("players_upserted", 0)),
            "transfers_upserted": transfers_written,
            "records_written": transfers_written,
        }
    except Exception as e:
        completed_at = _utcnow()
        _upsert_ingestion_run(
            session,
            run_key=run_key,
            source_name=source_name,
            endpoint=endpoint,
            run_type=run_type,
            league_id=None,
            season=season,
            status="error",
            started_at=started_at,
            completed_at=completed_at,
            error_message=str(e),
            raw_payload_path=raw_payload_path,
            records_written=None,
            fetched_from_api=1,
            cache_hit=0,
        )
        raise

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from pl_ingestion.database.fixtures_loader import _upsert_ingestion_run
from pl_ingestion.database.models import Fixture, FixtureLineup, Player, Team


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


def _grid_to_db_value(grid: Any) -> Optional[str]:
    if grid is None:
        return None
    if isinstance(grid, str):
        return grid
    # Transformer already stringifies in most cases; keep best-effort.
    return str(grid)


def _upsert_players(
    session: Session,
    *,
    source_name: str,
    raw_payload_path: Optional[Path],
    players: list[dict[str, Any]],
) -> int:
    if not players:
        return 0

    now = _utcnow()
    payload_path_str = str(raw_payload_path) if raw_payload_path else None

    stmt = sqlite_insert(Player).values(
        [
            {
                "id": p["player_id"],
                "name": p.get("player_name"),
                "position": p.get("player_position"),
                "short_position": None,
                "source_name": source_name,
                "ingested_at": now,
                "last_refreshed_at": now,
                "raw_payload_path": payload_path_str,
                "updated_at": now,
            }
            for p in players
        ]
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": stmt.excluded.name,
            "position": stmt.excluded.position,
            "source_name": stmt.excluded.source_name,
            "ingested_at": stmt.excluded.ingested_at,
            "last_refreshed_at": stmt.excluded.last_refreshed_at,
            "raw_payload_path": stmt.excluded.raw_payload_path,
            "updated_at": now,
        },
    )

    session.execute(stmt)
    return len(players)


def _resolve_team_id(
    *,
    fixture_row: Optional[Fixture],
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    home_team_name: Optional[str],
    away_team_name: Optional[str],
    lineup_team_id: Optional[int],
    lineup_team_name: Optional[str],
    lineup_team_side: Optional[str],
) -> Optional[int]:
    if isinstance(lineup_team_id, int):
        return lineup_team_id

    side = (lineup_team_side or "").strip().lower()
    if side == "home":
        return home_team_id
    if side == "away":
        return away_team_id

    # Fallback to matching by team name if we have one.
    if lineup_team_name and home_team_name and lineup_team_name == home_team_name:
        return home_team_id
    if lineup_team_name and away_team_name and lineup_team_name == away_team_name:
        return away_team_id

    return None


def upsert_fixture_lineups(
    session: Session,
    *,
    source_name: str,
    endpoint: str,
    run_type: str,
    run_key: str,
    fixture_id: int,
    raw_payload_path: Optional[Path],
    lineup_records: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Upsert players and fixture_lineups for a single fixture, and record ingestion status.
    """
    started_at = _utcnow()
    _upsert_ingestion_run(
        session,
        run_key=run_key,
        source_name=source_name,
        endpoint=endpoint,
        run_type=run_type,
        league_id=None,
        season=None,
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
        fixture_row = session.execute(select(Fixture).where(Fixture.fixture_id == fixture_id)).scalar_one_or_none()
        home_team_id: Optional[int] = getattr(fixture_row, "home_team_id", None) if fixture_row else None
        away_team_id: Optional[int] = getattr(fixture_row, "away_team_id", None) if fixture_row else None
        season: Optional[str] = getattr(fixture_row, "season", None) if fixture_row else None
        league_id: Optional[int] = getattr(fixture_row, "league_id", None) if fixture_row else None

        # Load team names for mapping by team_name (best-effort).
        home_team_name: Optional[str] = None
        away_team_name: Optional[str] = None
        if isinstance(home_team_id, int):
            home_team_name = session.execute(select(Team.name).where(Team.id == home_team_id)).scalar_one_or_none()
        if isinstance(away_team_id, int):
            away_team_name = session.execute(select(Team.name).where(Team.id == away_team_id)).scalar_one_or_none()

        # Upsert players first (only for records that have player_id).
        players = []
        seen_player_ids: set[int] = set()
        for rec in lineup_records:
            pid = rec.get("player_id")
            if not isinstance(pid, int) or pid in seen_player_ids:
                continue
            seen_player_ids.add(pid)
            players.append(
                {
                    "player_id": pid,
                    "player_name": rec.get("player_name"),
                    "player_position": rec.get("player_position"),
                }
            )

        players_written = _upsert_players(
            session,
            source_name=source_name,
            raw_payload_path=raw_payload_path,
            players=players,
        )

        now = _utcnow()
        payload_path_str = str(raw_payload_path) if raw_payload_path else None

        fixture_lineup_rows = []
        for rec in lineup_records:
            # For idempotent upserts we require a stable player_id.
            # If the API payload lacks a player id, we skip that record.
            pid = rec.get("player_id")
            if not isinstance(pid, int):
                continue

            resolved_team_id = _resolve_team_id(
                fixture_row=fixture_row,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_team_name=home_team_name,
                away_team_name=away_team_name,
                lineup_team_id=rec.get("team_id"),
                lineup_team_name=rec.get("team_name"),
                lineup_team_side=rec.get("team_side"),
            )

            fixture_lineup_rows.append(
                {
                    "fixture_id": fixture_id,
                    "player_id": pid,
                    "team_id": resolved_team_id,
                    "team_side": rec.get("team_side"),
                    "formation": rec.get("formation"),
                    "player_name": rec.get("player_name"),
                    # Underlying column names in SQLite are `shirt_number` and `position`.
                    "shirt_number": rec.get("player_number"),
                    "position": rec.get("player_position"),
                    "grid": _grid_to_db_value(rec.get("grid")),
                    "lineup_type": rec.get("lineup_type"),
                    "source_name": source_name,
                    "ingested_at": now,
                    "last_refreshed_at": now,
                    "raw_payload_path": payload_path_str,
                    "updated_at": now,
                }
            )

        stmt = sqlite_insert(FixtureLineup).values(fixture_lineup_rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["fixture_id", "player_id", "team_id"],
            set_={
                "team_side": stmt.excluded.team_side,
                "formation": stmt.excluded.formation,
                "player_name": stmt.excluded.player_name,
                "shirt_number": stmt.excluded.shirt_number,
                "position": stmt.excluded.position,
                "grid": stmt.excluded.grid,
                "lineup_type": stmt.excluded.lineup_type,
                "source_name": stmt.excluded.source_name,
                "ingested_at": stmt.excluded.ingested_at,
                "last_refreshed_at": stmt.excluded.last_refreshed_at,
                "raw_payload_path": stmt.excluded.raw_payload_path,
                "updated_at": now,
            },
        )

        session.execute(stmt)
        fixture_lineups_written = len(fixture_lineup_rows)

        completed_at = _utcnow()
        _upsert_ingestion_run(
            session,
            run_key=run_key,
            source_name=source_name,
            endpoint=endpoint,
            run_type=run_type,
            league_id=league_id,
            season=season,
            status="success",
            started_at=started_at,
            completed_at=completed_at,
            error_message=None,
            raw_payload_path=raw_payload_path,
            records_written=players_written + fixture_lineups_written,
            fetched_from_api=1,
            cache_hit=0,
        )

        return {
            "players_upserted": players_written,
            "fixture_lineups_upserted": fixture_lineups_written,
            "records_written": players_written + fixture_lineups_written,
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
            season=None,
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


def record_fixture_lineups_cache_hit_run(
    session: Session,
    *,
    run_key: str,
    source_name: str,
    endpoint: str,
    run_type: str,
    fixture_id: int,
    season: Optional[str],
    league_id: Optional[int],
    raw_payload_path: Optional[Path],
) -> None:
    started_at = _utcnow()
    completed_at = _utcnow()

    _upsert_ingestion_run(
        session,
        run_key=run_key,
        source_name=source_name,
        endpoint=endpoint,
        run_type=run_type,
        league_id=league_id,
        season=season,
        status="cache_hit",
        started_at=started_at,
        completed_at=completed_at,
        error_message=None,
        raw_payload_path=raw_payload_path,
        records_written=0,
        fetched_from_api=0,
        cache_hit=1,
    )


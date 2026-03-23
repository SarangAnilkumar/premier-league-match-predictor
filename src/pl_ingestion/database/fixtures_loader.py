from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from pl_ingestion.database.models import Fixture, IngestionRun, Team


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


def _parse_iso_datetime(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            # Example: 2024-08-16T19:00:00+00:00
            return dt.datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _bool_to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    return None


def _upsert_teams(
    session: Session,
    *,
    teams: Iterable[dict[str, Any]],
    source_name: str,
    raw_payload_path: Optional[Path],
) -> int:
    teams_list = list(teams)
    if not teams_list:
        return 0

    now = _utcnow()
    payload_path_str = str(raw_payload_path) if raw_payload_path else None

    stmt = sqlite_insert(Team).values(
        [
            {
                "id": t["id"],
                "name": t.get("name"),
                "short_name": t.get("short_name"),
                "country": t.get("country"),
                "source_name": source_name,
                "ingested_at": now,
                "last_refreshed_at": now,
                "raw_payload_path": payload_path_str,
                "updated_at": now,
            }
            for t in teams_list
        ]
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": stmt.excluded.name,
            "short_name": stmt.excluded.short_name,
            "country": stmt.excluded.country,
            "source_name": stmt.excluded.source_name,
            "ingested_at": stmt.excluded.ingested_at,
            "last_refreshed_at": stmt.excluded.last_refreshed_at,
            "raw_payload_path": stmt.excluded.raw_payload_path,
            "updated_at": now,
        },
    )

    session.execute(stmt)
    return len(teams_list)


def _upsert_fixtures(
    session: Session,
    *,
    fixtures: Iterable[dict[str, Any]],
    source_name: str,
    raw_payload_path: Optional[Path],
) -> int:
    fixtures_list = list(fixtures)
    if not fixtures_list:
        return 0

    now = _utcnow()
    payload_path_str = str(raw_payload_path) if raw_payload_path else None

    stmt = sqlite_insert(Fixture).values(
        [
            {
                "fixture_id": f["fixture_id"],
                "season": f.get("season"),
                "league_id": f.get("league_id"),
                "league_name": f.get("league_name"),
                "round": f.get("round"),
                "timezone": f.get("timezone"),
                "date_utc": _parse_iso_datetime(f.get("date_utc")),
                "timestamp": f.get("timestamp"),
                "referee": f.get("referee"),
                "status_long": f.get("status_long"),
                "status_short": f.get("status_short"),
                "elapsed_minutes": f.get("elapsed_minutes"),
                "venue_id": f.get("venue_id"),
                "venue_name": f.get("venue_name"),
                "venue_city": f.get("venue_city"),
                "home_team_id": f.get("home_team_id"),
                "away_team_id": f.get("away_team_id"),
                "home_team_name": f.get("home_team_name"),
                "away_team_name": f.get("away_team_name"),
                "home_team_winner": _bool_to_int(f.get("home_team_winner")),
                "away_team_winner": _bool_to_int(f.get("away_team_winner")),
                "home_goals": f.get("home_goals"),
                "away_goals": f.get("away_goals"),
                "halftime_home_goals": f.get("halftime_home_goals"),
                "halftime_away_goals": f.get("halftime_away_goals"),
                "fulltime_home_goals": f.get("fulltime_home_goals"),
                "fulltime_away_goals": f.get("fulltime_away_goals"),
                "extratime_home_goals": f.get("extratime_home_goals"),
                "extratime_away_goals": f.get("extratime_away_goals"),
                "penalty_home_goals": f.get("penalty_home_goals"),
                "penalty_away_goals": f.get("penalty_away_goals"),
                "match_result": f.get("match_result"),
                "source_name": source_name,
                "ingested_at": now,
                "last_refreshed_at": now,
                "raw_payload_path": payload_path_str,
                "updated_at": now,
            }
            for f in fixtures_list
        ]
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["fixture_id"],
        set_={
            "season": stmt.excluded.season,
            "league_id": stmt.excluded.league_id,
            "league_name": stmt.excluded.league_name,
            "round": stmt.excluded.round,
            "timezone": stmt.excluded.timezone,
            "date_utc": stmt.excluded.date_utc,
            "timestamp": stmt.excluded.timestamp,
            "referee": stmt.excluded.referee,
            "status_long": stmt.excluded.status_long,
            "status_short": stmt.excluded.status_short,
            "elapsed_minutes": stmt.excluded.elapsed_minutes,
            "venue_id": stmt.excluded.venue_id,
            "venue_name": stmt.excluded.venue_name,
            "venue_city": stmt.excluded.venue_city,
            "home_team_id": stmt.excluded.home_team_id,
            "away_team_id": stmt.excluded.away_team_id,
            "home_team_name": stmt.excluded.home_team_name,
            "away_team_name": stmt.excluded.away_team_name,
            "home_team_winner": stmt.excluded.home_team_winner,
            "away_team_winner": stmt.excluded.away_team_winner,
            "home_goals": stmt.excluded.home_goals,
            "away_goals": stmt.excluded.away_goals,
            "halftime_home_goals": stmt.excluded.halftime_home_goals,
            "halftime_away_goals": stmt.excluded.halftime_away_goals,
            "fulltime_home_goals": stmt.excluded.fulltime_home_goals,
            "fulltime_away_goals": stmt.excluded.fulltime_away_goals,
            "extratime_home_goals": stmt.excluded.extratime_home_goals,
            "extratime_away_goals": stmt.excluded.extratime_away_goals,
            "penalty_home_goals": stmt.excluded.penalty_home_goals,
            "penalty_away_goals": stmt.excluded.penalty_away_goals,
            "match_result": stmt.excluded.match_result,
            "source_name": stmt.excluded.source_name,
            "ingested_at": stmt.excluded.ingested_at,
            "last_refreshed_at": stmt.excluded.last_refreshed_at,
            "raw_payload_path": stmt.excluded.raw_payload_path,
            "updated_at": now,
        },
    )

    session.execute(stmt)
    return len(fixtures_list)


def _upsert_ingestion_run(
    session: Session,
    *,
    run_key: str,
    source_name: str,
    endpoint: str,
    run_type: str,
    league_id: Optional[int],
    season: Optional[str],
    status: str,
    started_at: dt.datetime,
    completed_at: Optional[dt.datetime],
    error_message: Optional[str],
    raw_payload_path: Optional[Path],
    records_written: Optional[int],
    fetched_from_api: Optional[int],
    cache_hit: Optional[int],
) -> None:
    now = _utcnow()
    payload_path_str = str(raw_payload_path) if raw_payload_path else None

    stmt = sqlite_insert(IngestionRun).values(
        {
            "run_key": run_key,
            "source_name": source_name,
            "endpoint": endpoint,
            "run_type": run_type,
            "league_id": league_id,
            "season": season,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "error_message": error_message,
            "raw_payload_path": payload_path_str,
            "fetched_from_api": fetched_from_api,
            "cache_hit": cache_hit,
            "ingested_at": now,
            "last_refreshed_at": completed_at,
            "updated_at": now,
        }
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["run_key"],
        set_={
            "source_name": stmt.excluded.source_name,
            "endpoint": stmt.excluded.endpoint,
            "run_type": stmt.excluded.run_type,
            "league_id": stmt.excluded.league_id,
            "season": stmt.excluded.season,
            "status": stmt.excluded.status,
            "started_at": stmt.excluded.started_at,
            "completed_at": stmt.excluded.completed_at,
            "error_message": stmt.excluded.error_message,
            "raw_payload_path": stmt.excluded.raw_payload_path,
            "records_written": records_written,
            "ingested_at": stmt.excluded.ingested_at,
            "last_refreshed_at": stmt.excluded.last_refreshed_at,
            "fetched_from_api": stmt.excluded.fetched_from_api,
            "cache_hit": stmt.excluded.cache_hit,
            "updated_at": now,
        },
    )

    session.execute(stmt)


def load_fixtures_to_db(
    session: Session,
    *,
    source_name: str,
    endpoint: str,
    run_type: str,
    run_key: str,
    season: str,
    league_id: int,
    raw_payload_path: Optional[Path],
    cleaned_fixtures: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Upsert reference data (teams) and event data (fixtures), plus ingestion run tracking.
    """

    started_at = _utcnow()
    _upsert_ingestion_run(
        session,
        run_key=run_key,
        source_name=source_name,
        endpoint=endpoint,
        run_type=run_type,
        league_id=league_id,
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
        # Teams are derived from fixture home/away teams.
        team_by_id: dict[int, dict[str, Any]] = {}
        for f in cleaned_fixtures:
            home_id = f.get("home_team_id")
            away_id = f.get("away_team_id")
            if isinstance(home_id, int):
                team_by_id[home_id] = {"id": home_id, "name": f.get("home_team_name")}
            if isinstance(away_id, int):
                team_by_id[away_id] = {"id": away_id, "name": f.get("away_team_name")}

        teams = list(team_by_id.values())

        teams_written = _upsert_teams(
            session,
            teams=teams,
            source_name=source_name,
            raw_payload_path=raw_payload_path,
        )

        fixtures_written = _upsert_fixtures(
            session,
            fixtures=cleaned_fixtures,
            source_name=source_name,
            raw_payload_path=raw_payload_path,
        )

        records_written = teams_written + fixtures_written

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
            records_written=records_written,
            fetched_from_api=1,
            cache_hit=0,
        )

        return {"teams_upserted": teams_written, "fixtures_upserted": fixtures_written, "records_written": records_written}
    except Exception as e:
        completed_at = _utcnow()
        _upsert_ingestion_run(
            session,
            run_key=run_key,
            source_name=source_name,
            endpoint=endpoint,
            run_type=run_type,
            league_id=league_id,
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


def record_fixtures_cache_hit_run(
    session: Session,
    *,
    run_key: str,
    source_name: str,
    endpoint: str,
    run_type: str,
    league_id: Optional[int],
    season: Optional[str],
    raw_payload_path: Optional[Path],
) -> None:
    """
    Upsert an `ingestion_runs` row for a cache-hit run where we skipped the
    external API.
    """
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


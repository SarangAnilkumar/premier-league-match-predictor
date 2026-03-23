from __future__ import annotations

from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from pl_ingestion.database.models import Fixture, Team


def _resolve_team_id(
    session: Session,
    *,
    team_id: Optional[int],
    team_name: Optional[str],
) -> int:
    if isinstance(team_id, int):
        return team_id

    if team_name:
        stmt = (
            select(Team.id)
            .where(Team.name == team_name)
            .order_by(Team.id.asc())
            .limit(2)
        )
        ids = [r[0] for r in session.execute(stmt).all()]
        if not ids:
            raise ValueError(f"No team found in DB for team_name={team_name!r}")
        if len(ids) > 1:
            raise ValueError(
                f"Ambiguous team_name={team_name!r} matched multiple teams: {ids}"
            )
        return ids[0]

    raise ValueError("Either team_id or team_name must be provided for team selection.")


def select_fixture_ids_first_n_in_season(
    session: Session,
    *,
    season: str,
    first_n: int,
) -> list[int]:
    if first_n <= 0:
        return []

    stmt = (
        select(Fixture.fixture_id)
        .where(Fixture.season == season)
        .order_by(Fixture.date_utc.asc(), Fixture.fixture_id.asc())
        .limit(first_n)
    )
    return [r[0] for r in session.execute(stmt).all()]


def select_fixture_ids_by_round(
    session: Session,
    *,
    season: str,
    round_value: str,
) -> list[int]:
    stmt = (
        select(Fixture.fixture_id)
        .where(and_(Fixture.season == season, Fixture.round == round_value))
        .order_by(Fixture.date_utc.asc(), Fixture.fixture_id.asc())
    )
    return [r[0] for r in session.execute(stmt).all()]


def select_fixture_ids_by_team(
    session: Session,
    *,
    season: str,
    team_id: Optional[int] = None,
    team_name: Optional[str] = None,
) -> list[int]:
    resolved_team_id = _resolve_team_id(
        session, team_id=team_id, team_name=team_name
    )

    stmt = (
        select(Fixture.fixture_id)
        .where(
            and_(
                Fixture.season == season,
                or_(
                    Fixture.home_team_id == resolved_team_id,
                    Fixture.away_team_id == resolved_team_id,
                ),
            )
        )
        .order_by(Fixture.date_utc.asc(), Fixture.fixture_id.asc())
    )
    return [r[0] for r in session.execute(stmt).all()]


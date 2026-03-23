from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pl_ingestion.database.models import Fixture


@dataclass(frozen=True)
class FixturesCacheDecision:
    should_fetch: bool
    cached_fixture_count: int


def decide_fixtures_refresh(
    *,
    session: Session,
    league_id: int,
    season: str,
    force_refresh: bool,
) -> FixturesCacheDecision:
    """
    Cache-first decision logic for fixtures ingestion.

    Current strategy:
    - if fixtures exist for the (league_id, season) and force_refresh is False:
        skip external API call
    - otherwise: fetch from external provider
    """
    stmt = (
        select(func.count(Fixture.fixture_id))
        .where(Fixture.league_id == league_id)
        .where(Fixture.season == season)
    )
    cached_fixture_count = int(session.execute(stmt).scalar() or 0)

    if cached_fixture_count > 0 and not force_refresh:
        return FixturesCacheDecision(should_fetch=False, cached_fixture_count=cached_fixture_count)

    return FixturesCacheDecision(should_fetch=True, cached_fixture_count=cached_fixture_count)


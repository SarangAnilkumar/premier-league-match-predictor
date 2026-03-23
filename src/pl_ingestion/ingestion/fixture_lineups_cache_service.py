from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pl_ingestion.database.models import FixtureLineup


@dataclass(frozen=True)
class FixtureLineupsCacheDecision:
    should_fetch: bool
    cached_lineup_rows: int


def decide_fixture_lineups_refresh(
    *,
    session: Session,
    fixture_id: int,
    force_refresh: bool,
) -> FixtureLineupsCacheDecision:
    """
    Cache-first decision logic for fixture lineups.

    Current strategy:
    - If lineup rows exist for fixture_id and force_refresh is False:
        skip external API call
    - Otherwise: fetch from the external provider
    """
    stmt = select(func.count(FixtureLineup.id)).where(FixtureLineup.fixture_id == fixture_id)
    cached_lineup_rows = int(session.execute(stmt).scalar() or 0)

    if cached_lineup_rows > 0 and not force_refresh:
        return FixtureLineupsCacheDecision(
            should_fetch=False,
            cached_lineup_rows=cached_lineup_rows,
        )

    return FixtureLineupsCacheDecision(
        should_fetch=True,
        cached_lineup_rows=cached_lineup_rows,
    )


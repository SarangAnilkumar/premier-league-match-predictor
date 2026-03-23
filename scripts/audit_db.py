from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Any, Iterable

import sys
from pathlib import Path

from sqlalchemy import and_, func, exists, or_, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pl_ingestion.database.connection import (  # noqa: E402
    create_db_engine,
    make_session_factory,
    session_scope,
)
from pl_ingestion.database.db_config import DatabaseSettings  # noqa: E402
from pl_ingestion.database.models import Fixture, FixtureLineup, IngestionRun, Player, Team  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit SQLite DB health and ingestion coverage.")
    parser.add_argument(
        "--top-formations",
        type=int,
        default=10,
        help="How many top formations to show (by lineup row count).",
    )
    parser.add_argument(
        "--recent-error-runs",
        type=int,
        default=50,
        help="How many recent failed ingestion runs to scan for inferred fixture_ids.",
    )
    return parser.parse_args()


@dataclass(frozen=True)
class AuditCounts:
    total_teams: int
    total_fixtures: int
    total_players: int
    total_fixture_lineups: int
    total_ingestion_runs: int


def _scalar_int(session, stmt: Any) -> int:
    value = session.execute(stmt).scalar()
    return int(value or 0)


def _grouped_count_rows(session, stmt: Any) -> list[tuple[Any, ...]]:
    rows = session.execute(stmt).all()
    return [tuple(r) for r in rows]


def _format_int(n: int) -> str:
    return f"{n:,}"


def _format_float(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}"


def _ordered_unique(seq: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for x in seq:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def audit_db(
    *,
    session_factory,
    top_formations: int,
    recent_error_runs: int,
) -> None:
    with session_scope(session_factory) as session:
        # --- Core table counts ---
        total_teams = _scalar_int(session, select(func.count(Team.id)))
        total_fixtures = _scalar_int(session, select(func.count(Fixture.fixture_id)))
        total_players = _scalar_int(session, select(func.count(Player.id)))
        total_fixture_lineups = _scalar_int(session, select(func.count(FixtureLineup.id)))
        total_ingestion_runs = _scalar_int(session, select(func.count(IngestionRun.id)))

        counts = AuditCounts(
            total_teams=total_teams,
            total_fixtures=total_fixtures,
            total_players=total_players,
            total_fixture_lineups=total_fixture_lineups,
            total_ingestion_runs=total_ingestion_runs,
        )

        print("DB Audit Report (SQLite)")
        print("=" * 80)
        print("\nA) Core table counts")
        print(f"  total teams: {_format_int(counts.total_teams)}")
        print(f"  total fixtures: {_format_int(counts.total_fixtures)}")
        print(f"  total players: {_format_int(counts.total_players)}")
        print(f"  total fixture_lineups: {_format_int(counts.total_fixture_lineups)}")
        print(f"  total ingestion_runs: {_format_int(counts.total_ingestion_runs)}")

        # --- Lineup coverage metrics ---
        fixtures_with_any_lineups = _scalar_int(
            session,
            select(func.count(func.distinct(FixtureLineup.fixture_id))),
        )

        fixtures_no_lineup_coverage = max(0, counts.total_fixtures - fixtures_with_any_lineups)

        avg_rows_per_covered_fixture = (
            (counts.total_fixture_lineups / fixtures_with_any_lineups)
            if fixtures_with_any_lineups > 0
            else 0.0
        )

        # Coverage by home/away team ids (best-effort; if home/away ids are NULL,
        # the corresponding coverage will be treated as absent).
        has_home = exists(
            select(1).select_from(FixtureLineup).where(
                and_(
                    FixtureLineup.fixture_id == Fixture.fixture_id,
                    FixtureLineup.team_id == Fixture.home_team_id,
                )
            )
        )
        has_away = exists(
            select(1).select_from(FixtureLineup).where(
                and_(
                    FixtureLineup.fixture_id == Fixture.fixture_id,
                    FixtureLineup.team_id == Fixture.away_team_id,
                )
            )
        )

        fixtures_both_teams_covered = _scalar_int(
            session,
            select(func.count()).select_from(Fixture).where(and_(has_home, has_away)),
        )
        fixtures_only_one_team_covered = _scalar_int(
            session,
            select(func.count())
            .select_from(Fixture)
            .where(or_(has_home, has_away))
            .where(~and_(has_home, has_away)),
        )

        print("\nB) Lineup coverage metrics")
        print(f"  fixtures with any lineup rows: {_format_int(fixtures_with_any_lineups)}")
        print(f"  fixtures with both teams covered: {_format_int(fixtures_both_teams_covered)}")
        print(f"  fixtures with only one team covered: {_format_int(fixtures_only_one_team_covered)}")
        print(f"  fixtures with no lineup coverage: {_format_int(fixtures_no_lineup_coverage)}")
        print(
            f"  avg lineup rows per covered fixture: {_format_float(avg_rows_per_covered_fixture)}"
        )

        # --- Formation quality metrics ---
        unique_formations = _scalar_int(
            session,
            select(func.count(func.distinct(FixtureLineup.formation))).where(
                FixtureLineup.formation.is_not(None)
            ),
        )
        lineup_rows_missing_formation = _scalar_int(
            session,
            select(func.count()).where(FixtureLineup.formation.is_(None)),
        )
        fixtures_with_starting_formation = _scalar_int(
            session,
            select(func.count(func.distinct(FixtureLineup.fixture_id))).where(
                and_(
                    FixtureLineup.lineup_type == "starting_xi",
                    FixtureLineup.formation.is_not(None),
                )
            ),
        )

        top_formations_rows = _grouped_count_rows(
            session,
            select(FixtureLineup.formation, func.count().label("c"))
            .where(FixtureLineup.formation.is_not(None))
            .group_by(FixtureLineup.formation)
            .order_by(func.count().desc(), FixtureLineup.formation.asc())
            .limit(top_formations),
        )
        top_formations_list = [(str(f), int(c)) for f, c in top_formations_rows]

        print("\nC) Formation quality metrics")
        print(f"  unique formations: {_format_int(unique_formations)}")
        print(f"  lineup rows missing formation: {_format_int(lineup_rows_missing_formation)}")
        print(
            f"  fixtures with at least one starting formation: {_format_int(fixtures_with_starting_formation)}"
        )
        print(f"  top formations by count (limit={top_formations}):")
        if top_formations_list:
            for formation, c in top_formations_list:
                print(f"    - {formation}: {_format_int(c)}")
        else:
            print("    - (none)")

        # --- Player quality metrics ---
        lineup_rows_missing_player_id = _scalar_int(
            session,
            select(func.count()).where(FixtureLineup.player_id.is_(None)),
        )
        distinct_players_referenced = _scalar_int(
            session,
            select(func.count(func.distinct(FixtureLineup.player_id))).where(
                FixtureLineup.player_id.is_not(None)
            ),
        )

        print("\nD) Player quality metrics")
        print(f"  lineup rows missing player_id: {_format_int(lineup_rows_missing_player_id)}")
        print(f"  distinct players referenced in fixture_lineups: {_format_int(distinct_players_referenced)}")

        # --- Ingestion run quality ---
        by_status_rows = _grouped_count_rows(
            session,
            select(IngestionRun.status, func.count().label("c"))
            .group_by(IngestionRun.status)
            .order_by(func.count().desc(), IngestionRun.status.asc()),
        )
        by_endpoint_rows = _grouped_count_rows(
            session,
            select(IngestionRun.endpoint, IngestionRun.run_type, func.count().label("c"))
            .group_by(IngestionRun.endpoint, IngestionRun.run_type)
            .order_by(func.count().desc(), IngestionRun.endpoint.asc(), IngestionRun.run_type.asc()),
        )

        print("\nE) Ingestion run quality")
        print("  ingestion_runs grouped by status:")
        for status, c in by_status_rows:
            print(f"    - {status}: {_format_int(int(c))}")
        if not by_status_rows:
            print("    - (none)")

        print("\n  ingestion_runs grouped by endpoint/run_type:")
        for endpoint, run_type, c in by_endpoint_rows:
            print(f"    - {endpoint} | {run_type}: {_format_int(int(c))}")
        if not by_endpoint_rows:
            print("    - (none)")

        # Recent failed fixture_ids (best-effort parsing from run_key).
        # Example lineups run_key:
        #   api_football:fixtures/lineups:fixture_lineups:fixture_id=123
        fixture_id_re = re.compile(r"fixture_id=(\\d+)")
        recent_error_rows = session.execute(
            select(IngestionRun.run_key, IngestionRun.endpoint, IngestionRun.run_type)
            .where(IngestionRun.status == "error")
            .order_by(IngestionRun.id.desc())
            .limit(recent_error_runs)
        ).all()

        inferred_fixture_ids: list[int] = []
        for run_key, endpoint, run_type in recent_error_rows:
            if "fixture_id=" not in (run_key or ""):
                continue
            match = fixture_id_re.search(run_key or "")
            if not match:
                continue
            inferred_fixture_ids.append(int(match.group(1)))

        inferred_fixture_ids = _ordered_unique(inferred_fixture_ids)
        print("\n  recent failed fixture_ids (inferred from ingestion_runs.run_key):")
        if inferred_fixture_ids:
            preview = inferred_fixture_ids[:50]
            suffix = "" if len(inferred_fixture_ids) <= len(preview) else f" (+{len(inferred_fixture_ids) - len(preview)} more)"
            print(f"    - {', '.join(str(x) for x in preview)}{suffix}")
        else:
            print("    - (none inferred)")


def main() -> None:
    args = parse_args()
    db_settings = DatabaseSettings.from_env()
    engine = create_db_engine(db_settings)
    session_factory = make_session_factory(engine)

    audit_db(
        session_factory=session_factory,
        top_formations=args.top_formations,
        recent_error_runs=args.recent_error_runs,
    )


if __name__ == "__main__":
    main()


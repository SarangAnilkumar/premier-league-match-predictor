from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pl_ingestion.database.models import Fixture, FixtureLineup, Team


def _is_starting_lineup_type(lineup_type: Optional[str]) -> bool:
    """
    Transformer stores lineup_type values like:
    - "starting_xi"
    - "substitutes"

    Treat anything starting with "starting" as starting.
    """
    if lineup_type is None:
        return False
    lt = lineup_type.strip().lower()
    return lt in {"starting", "starting_xi"} or lt.startswith("starting")


def _datetime_to_utc_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        # Preserve timezone if present; JSON output stays deterministic.
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def _compute_result_from_goals(
    goals_for: Optional[int], goals_against: Optional[int]
) -> Tuple[int, int, int]:
    """
    Returns (wins, draws, losses) where only one of them can be 1 for each fixture.
    If either score is missing, returns (0, 0, 0).
    """
    if goals_for is None or goals_against is None:
        return (0, 0, 0)
    if goals_for > goals_against:
        return (1, 0, 0)
    if goals_against > goals_for:
        return (0, 0, 1)
    return (0, 1, 0)


def build_fixture_formations_primary(session: Session) -> list[dict[str, Any]]:
    """
    Build analytics-ready formation rows for each (fixture_id, team_id) that has
    lineup coverage.

    Output is derived from:
    - `fixtures` (match metadata + goals)
    - `fixture_lineups` (formation + team_id)

    Important:
    - If lineup data is missing for one team, we only output rows for teams we have.
    - If team_id can’t be mapped to the fixture (home/away mismatch), the row is skipped.
    """
    lineup_counts_stmt = (
        select(
            FixtureLineup.fixture_id,
            FixtureLineup.team_id,
            FixtureLineup.formation,
            func.count().label("row_count"),
        )
        .where(FixtureLineup.team_id.is_not(None))
        .group_by(FixtureLineup.fixture_id, FixtureLineup.team_id, FixtureLineup.formation)
    )
    lineup_counts = session.execute(lineup_counts_stmt).all()

    # Choose deterministic formation per (fixture_id, team_id): mode by row count,
    # tie-break by lexicographic formation string.
    best_formation: dict[tuple[int, int], Optional[str]] = {}
    best_count: dict[tuple[int, int], int] = {}

    for fixture_id, team_id, formation, row_count in lineup_counts:
        key = (int(fixture_id), int(team_id))
        formation_str = formation if formation is not None else None
        row_count_int = int(row_count)

        if key not in best_count:
            best_count[key] = row_count_int
            best_formation[key] = formation_str
            continue

        if row_count_int > best_count[key]:
            best_count[key] = row_count_int
            best_formation[key] = formation_str
            continue

        if row_count_int == best_count[key]:
            # Deterministic tie-break: None < any string
            current = best_formation[key]
            curr_sort = "" if current is None else str(current)
            new_sort = "" if formation_str is None else str(formation_str)
            if new_sort < curr_sort:
                best_formation[key] = formation_str

    if not best_formation:
        return []

    fixture_ids = sorted({k[0] for k in best_formation.keys()})
    team_ids = sorted({k[1] for k in best_formation.keys()})

    fixtures_stmt = select(
        Fixture.fixture_id,
        Fixture.season,
        Fixture.round,
        Fixture.date_utc,
        Fixture.home_team_id,
        Fixture.away_team_id,
        Fixture.home_goals,
        Fixture.away_goals,
        Fixture.match_result,
    ).where(Fixture.fixture_id.in_(fixture_ids))

    fixture_rows = session.execute(fixtures_stmt).all()
    fixture_by_id = {int(r.fixture_id): r for r in fixture_rows}

    # Collect opponent team ids so we can resolve team names deterministically.
    opponent_team_ids: set[int] = set()
    for fixture in fixture_rows:
        if fixture.home_team_id is not None:
            opponent_team_ids.add(int(fixture.home_team_id))
        if fixture.away_team_id is not None:
            opponent_team_ids.add(int(fixture.away_team_id))

    all_team_ids = sorted({*team_ids, *opponent_team_ids})
    team_stmt = select(Team.id, Team.name).where(Team.id.in_(all_team_ids))
    teams = session.execute(team_stmt).all()
    team_name_by_id = {int(tid): name for tid, name in teams}

    # Build output rows.
    output: list[dict[str, Any]] = []
    for (fixture_id, team_id) in sorted(best_formation.keys()):
        fixture = fixture_by_id.get(fixture_id)
        if fixture is None:
            continue

        if fixture.home_team_id is not None and int(fixture.home_team_id) == team_id:
            opponent_id = int(fixture.away_team_id) if fixture.away_team_id is not None else None
            goals_for = fixture.home_goals
            goals_against = fixture.away_goals
        elif fixture.away_team_id is not None and int(fixture.away_team_id) == team_id:
            opponent_id = int(fixture.home_team_id) if fixture.home_team_id is not None else None
            goals_for = fixture.away_goals
            goals_against = fixture.home_goals
        else:
            # Avoid inventing: lineup team_id didn't match fixture home/away mapping.
            continue

        output.append(
            {
                "fixture_id": fixture_id,
                "season": fixture.season,
                "round": fixture.round,
                "date_utc": _datetime_to_utc_iso(fixture.date_utc),
                "team_id": team_id,
                "team_name": team_name_by_id.get(team_id),
                "opponent_team_id": opponent_id,
                "opponent_team_name": team_name_by_id.get(opponent_id) if opponent_id is not None else None,
                "formation": best_formation[(fixture_id, team_id)],
                "match_result": fixture.match_result,
                "goals_for": goals_for,
                "goals_against": goals_against,
            }
        )

    return output


def build_starting_formations(session: Session) -> list[dict[str, Any]]:
    """
    Starting XI only dataset.

    Includes only fixture/team/formation rows where lineup_type indicates a starting lineup.
    One row per (fixture_id, team_id, formation).
    """
    # Prefer exact matches first for speed/determinism.
    stmt = (
        select(FixtureLineup.fixture_id, FixtureLineup.team_id, FixtureLineup.formation)
        .where(FixtureLineup.team_id.is_not(None))
        .where(FixtureLineup.formation.is_not(None))
        .where(FixtureLineup.lineup_type.is_not(None))
        .where(FixtureLineup.lineup_type.in_(["starting", "starting_xi"]))
        .distinct()
    )
    rows = session.execute(stmt).all()

    # Fallback if stored lineup_type values differ (best-effort).
    if not rows:
        stmt2 = (
            select(
                FixtureLineup.fixture_id,
                FixtureLineup.team_id,
                FixtureLineup.formation,
                FixtureLineup.lineup_type,
            )
            .where(FixtureLineup.team_id.is_not(None))
            .where(FixtureLineup.formation.is_not(None))
            .where(FixtureLineup.lineup_type.is_not(None))
        )
        all_rows = session.execute(stmt2).all()
        rows = [(fid, tid, form) for fid, tid, form, lt in all_rows if _is_starting_lineup_type(lt)]

    if not rows:
        return []

    unique = sorted({(int(fid), int(tid), str(form)) for fid, tid, form in rows}, key=lambda k: (k[0], k[1], k[2]))
    fixture_ids = sorted({fid for fid, _, _ in unique})
    team_ids = sorted({tid for _, tid, _ in unique})

    fixtures_stmt = select(
        Fixture.fixture_id,
        Fixture.season,
        Fixture.round,
        Fixture.date_utc,
        Fixture.home_team_id,
        Fixture.away_team_id,
        Fixture.home_goals,
        Fixture.away_goals,
        Fixture.match_result,
    ).where(Fixture.fixture_id.in_(fixture_ids))
    fixture_rows = session.execute(fixtures_stmt).all()
    fixture_by_id = {int(r.fixture_id): r for r in fixture_rows}

    team_stmt = select(Team.id, Team.name).where(Team.id.in_(team_ids))
    team_rows = session.execute(team_stmt).all()
    team_name_by_id = {int(tid): name for tid, name in team_rows}

    output: list[dict[str, Any]] = []
    for fixture_id, team_id, formation in unique:
        fixture = fixture_by_id.get(fixture_id)
        if fixture is None:
            continue

        if fixture.home_team_id is not None and int(fixture.home_team_id) == team_id:
            goals_for = fixture.home_goals
            goals_against = fixture.away_goals
        elif fixture.away_team_id is not None and int(fixture.away_team_id) == team_id:
            goals_for = fixture.away_goals
            goals_against = fixture.home_goals
        else:
            continue

        output.append(
            {
                "fixture_id": fixture_id,
                "team_id": team_id,
                "team_name": team_name_by_id.get(team_id),
                "formation": formation,
                "match_result": fixture.match_result,
                "goals_for": goals_for,
                "goals_against": goals_against,
            }
        )

    return output


def build_formation_usage_full(session: Session) -> list[dict[str, Any]]:
    """
    Full formation usage from *all* formations present in fixture_lineups.

    Aggregation is performed over distinct (fixture_id, team_id, formation) occurrences
    to avoid inflating counts because fixture_lineups stores one row per player.
    """
    distinct_stmt = (
        select(FixtureLineup.fixture_id, FixtureLineup.team_id, FixtureLineup.formation)
        .where(FixtureLineup.team_id.is_not(None))
        .where(FixtureLineup.formation.is_not(None))
        .distinct()
    )
    rows = session.execute(distinct_stmt).all()
    if not rows:
        return []

    unique = {(int(fid), int(tid), str(form)) for fid, tid, form in rows}
    fixture_ids = sorted({fid for fid, _, _ in unique})
    team_ids = sorted({tid for _, tid, _ in unique})

    fixtures_stmt = select(
        Fixture.fixture_id,
        Fixture.home_team_id,
        Fixture.away_team_id,
        Fixture.home_goals,
        Fixture.away_goals,
        Fixture.match_result,
    ).where(Fixture.fixture_id.in_(fixture_ids))
    fixture_rows = session.execute(fixtures_stmt).all()
    fixture_by_id = {int(r.fixture_id): r for r in fixture_rows}

    team_stmt = select(Team.id, Team.name).where(Team.id.in_(team_ids))
    team_rows = session.execute(team_stmt).all()
    team_name_by_id = {int(tid): name for tid, name in team_rows}

    agg: dict[tuple[int, Optional[str], str], dict[str, Any]] = {}
    for fixture_id, team_id, formation in sorted(unique, key=lambda k: (k[1], k[2], k[0])):
        fixture = fixture_by_id.get(fixture_id)
        if fixture is None:
            continue

        home_id = int(fixture.home_team_id) if fixture.home_team_id is not None else None
        away_id = int(fixture.away_team_id) if fixture.away_team_id is not None else None
        is_home = home_id == team_id
        is_away = away_id == team_id
        if not is_home and not is_away:
            continue

        gf = fixture.home_goals if is_home else fixture.away_goals
        ga = fixture.away_goals if is_home else fixture.home_goals

        mr = fixture.match_result
        win, draw, loss = 0, 0, 0
        if mr == "draw":
            draw = 1
        elif mr == "home_win":
            win = 1 if is_home else 0
            loss = 1 if is_away else 0
        elif mr == "away_win":
            win = 1 if is_away else 0
            loss = 1 if is_home else 0
        else:
            continue

        key = (team_id, team_name_by_id.get(team_id), formation)
        if key not in agg:
            agg[key] = {
                "team_id": team_id,
                "team_name": team_name_by_id.get(team_id),
                "formation": formation,
                "appearances": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
            }

        row = agg[key]
        row["appearances"] += 1
        row["wins"] += win
        row["draws"] += draw
        row["losses"] += loss
        if isinstance(gf, int):
            row["goals_for"] += gf
        if isinstance(ga, int):
            row["goals_against"] += ga

    output: list[dict[str, Any]] = []
    for key in sorted(agg.keys(), key=lambda k: ((k[1] or ""), k[2], k[0])):
        output.append(agg[key])
    return output


def _team_relative_result_label(goals_for: Optional[int], goals_against: Optional[int]) -> Optional[str]:
    if goals_for is None or goals_against is None:
        return None
    wins, draws, losses = _compute_result_from_goals(goals_for, goals_against)
    if wins == 1:
        return "win"
    if draws == 1:
        return "draw"
    if losses == 1:
        return "loss"
    return None


def build_formation_matchups(
    session: Session,
    *,
    starting_lineup_types: tuple[str, ...] = ("starting", "starting_xi"),
) -> list[dict[str, Any]]:
    """
    Build formation matchups using starting-XI only.

    Each row represents one team's tactical matchup in a fixture:
    - team_formation: selected starting formation for `team_id` in the fixture
    - opponent_formation: selected starting formation for the opponent in the fixture

    Selection:
    - choose a single deterministic formation per (fixture_id, team_id) by "mode"
      using row counts from fixture_lineups (one row per player -> count is stable).
    - if either home/away side lacks starting formation coverage for the fixture,
      the fixture is skipped (no invented rows).
    """
    # Count starting formations per (fixture_id, team_id, formation).
    starting_counts_stmt = (
        select(
            FixtureLineup.fixture_id,
            FixtureLineup.team_id,
            FixtureLineup.formation,
            func.count().label("row_count"),
        )
        .where(FixtureLineup.team_id.is_not(None))
        .where(FixtureLineup.formation.is_not(None))
        .where(FixtureLineup.lineup_type.is_not(None))
        .where(FixtureLineup.lineup_type.in_(list(starting_lineup_types)))
        .group_by(FixtureLineup.fixture_id, FixtureLineup.team_id, FixtureLineup.formation)
    )
    starting_counts = session.execute(starting_counts_stmt).all()

    if not starting_counts:
        return []

    # Deterministically choose ONE formation per (fixture_id, team_id).
    best_formation: dict[tuple[int, int], Optional[str]] = {}
    best_count: dict[tuple[int, int], int] = {}
    for fixture_id, team_id, formation, row_count in starting_counts:
        key = (int(fixture_id), int(team_id))
        formation_str = str(formation) if formation is not None else None
        row_count_int = int(row_count)

        if key not in best_count:
            best_count[key] = row_count_int
            best_formation[key] = formation_str
            continue

        if row_count_int > best_count[key]:
            best_count[key] = row_count_int
            best_formation[key] = formation_str
            continue

        if row_count_int == best_count[key]:
            # Deterministic tie-break by lexicographic formation string.
            current = best_formation[key]
            curr_sort = "" if current is None else str(current)
            new_sort = "" if formation_str is None else str(formation_str)
            if new_sort < curr_sort:
                best_formation[key] = formation_str

    fixture_ids = sorted({k[0] for k in best_formation.keys()})

    fixtures_stmt = select(
        Fixture.fixture_id,
        Fixture.season,
        Fixture.round,
        Fixture.date_utc,
        Fixture.home_team_id,
        Fixture.away_team_id,
        Fixture.home_goals,
        Fixture.away_goals,
        Fixture.match_result,
    ).where(Fixture.fixture_id.in_(fixture_ids))

    fixture_rows = session.execute(fixtures_stmt).all()
    fixture_by_id = {int(r.fixture_id): r for r in fixture_rows}

    # Only output fixtures where BOTH sides have selected starting formations.
    qualifying_fixture_ids: list[int] = []
    team_ids: set[int] = set()
    for fid in fixture_ids:
        fx = fixture_by_id.get(fid)
        if fx is None:
            continue
        if fx.home_team_id is None or fx.away_team_id is None:
            continue
        home_id = int(fx.home_team_id)
        away_id = int(fx.away_team_id)
        if (fid, home_id) not in best_formation or (fid, away_id) not in best_formation:
            continue
        qualifying_fixture_ids.append(fid)
        team_ids.add(home_id)
        team_ids.add(away_id)

    if not qualifying_fixture_ids:
        return []

    team_stmt = select(Team.id, Team.name).where(Team.id.in_(sorted(team_ids)))
    team_rows = session.execute(team_stmt).all()
    team_name_by_id = {int(tid): name for tid, name in team_rows}

    output: list[dict[str, Any]] = []
    for fid in sorted(qualifying_fixture_ids, key=lambda x: (str(fixture_by_id[x].date_utc or ""), x)):
        fx = fixture_by_id.get(fid)
        if fx is None:
            continue

        if fx.home_goals is None or fx.away_goals is None:
            # Match result relative to goals requires both sides to have goals.
            continue

        home_id = int(fx.home_team_id)
        away_id = int(fx.away_team_id)

        home_formation = best_formation[(fid, home_id)]
        away_formation = best_formation[(fid, away_id)]
        if home_formation is None or away_formation is None:
            continue

        # Home team row.
        home_match_result = _team_relative_result_label(fx.home_goals, fx.away_goals)
        if home_match_result is not None:
            output.append(
                {
                    "fixture_id": fid,
                    "season": fx.season,
                    "round": fx.round,
                    "date_utc": _datetime_to_utc_iso(fx.date_utc),
                    "team_id": home_id,
                    "team_name": team_name_by_id.get(home_id),
                    "team_formation": home_formation,
                    "opponent_team_id": away_id,
                    "opponent_team_name": team_name_by_id.get(away_id),
                    "opponent_formation": away_formation,
                    "match_result": home_match_result,  # win/draw/loss (team-relative)
                    "goals_for": fx.home_goals,
                    "goals_against": fx.away_goals,
                    # Debugging: fixture-level result (home_win/away_win/draw).
                    "fixture_match_result": fx.match_result,
                }
            )

        # Away team row.
        away_match_result = _team_relative_result_label(fx.away_goals, fx.home_goals)
        if away_match_result is not None:
            output.append(
                {
                    "fixture_id": fid,
                    "season": fx.season,
                    "round": fx.round,
                    "date_utc": _datetime_to_utc_iso(fx.date_utc),
                    "team_id": away_id,
                    "team_name": team_name_by_id.get(away_id),
                    "team_formation": away_formation,
                    "opponent_team_id": home_id,
                    "opponent_team_name": team_name_by_id.get(home_id),
                    "opponent_formation": home_formation,
                    "match_result": away_match_result,  # win/draw/loss (team-relative)
                    "goals_for": fx.away_goals,
                    "goals_against": fx.home_goals,
                    "fixture_match_result": fx.match_result,
                }
            )

    # Deterministic final sorting.
    output.sort(key=lambda r: (str(r.get("date_utc") or ""), int(r["fixture_id"]), int(r["team_id"])))
    return output


def build_formation_matchup_summary(session: Session) -> list[dict[str, Any]]:
    """
    Summarize formation matchups by (team_formation, opponent_formation).
    """
    matchups = build_formation_matchups(session)
    if not matchups:
        return []

    agg: dict[tuple[str, str], dict[str, Any]] = {}
    for row in matchups:
        key = (str(row["team_formation"]), str(row["opponent_formation"]))
        if key not in agg:
            agg[key] = {
                "team_formation": row["team_formation"],
                "opponent_formation": row["opponent_formation"],
                "matches": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
            }

        agg_row = agg[key]
        agg_row["matches"] += 1

        mr = row.get("match_result")
        if mr == "win":
            agg_row["wins"] += 1
        elif mr == "draw":
            agg_row["draws"] += 1
        elif mr == "loss":
            agg_row["losses"] += 1

        gf = row.get("goals_for")
        ga = row.get("goals_against")
        if isinstance(gf, int):
            agg_row["goals_for"] += gf
        if isinstance(ga, int):
            agg_row["goals_against"] += ga

    output: list[dict[str, Any]] = []
    for key in sorted(agg.keys(), key=lambda k: (k[0], k[1])):
        row = agg[key]
        matches = int(row["matches"])
        wins = int(row["wins"])
        goals_for = int(row["goals_for"])
        goals_against = int(row["goals_against"])

        row["win_rate"] = round((wins / matches) * 100, 6) if matches > 0 else 0.0
        row["average_goals_for"] = round(goals_for / matches, 6) if matches > 0 else 0.0
        row["average_goals_against"] = round(goals_against / matches, 6) if matches > 0 else 0.0
        output.append(row)

    return output


def build_formation_usage_primary(session: Session) -> list[dict[str, Any]]:
    """
    Primary (backward compatible) formation usage.

    Aggregates over the primary fixture formations dataset, which selects a single
    deterministic formation per (fixture_id, team_id).
    """
    fixture_formations = build_fixture_formations_primary(session)
    if not fixture_formations:
        return []

    # Group key: (team_id, formation)
    agg: dict[tuple[int, Optional[str]], dict[str, Any]] = {}

    for row in fixture_formations:
        key = (int(row["team_id"]), row.get("formation"))
        team_id, formation = key

        if key not in agg:
            agg[key] = {
                "team_id": team_id,
                "team_name": row.get("team_name"),
                "formation": formation,
                "matches_with_formation": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
            }

        gf = row.get("goals_for")
        ga = row.get("goals_against")

        agg_row = agg[key]
        agg_row["matches_with_formation"] += 1

        wins, draws, losses = _compute_result_from_goals(
            gf if isinstance(gf, int) else None,
            ga if isinstance(ga, int) else None,
        )
        agg_row["wins"] += wins
        agg_row["draws"] += draws
        agg_row["losses"] += losses

        if isinstance(gf, int):
            agg_row["goals_for"] += gf
        if isinstance(ga, int):
            agg_row["goals_against"] += ga

    # Finalize win_rate and deterministic sorting.
    output: list[dict[str, Any]] = []
    for key in sorted(agg.keys(), key=lambda k: (agg[k]["team_name"] or "", str(agg[k]["formation"] or ""))):
        row = agg[key]
        matches = int(row["matches_with_formation"])
        wins = int(row["wins"])
        row["win_rate"] = round((wins / matches) * 100, 6) if matches > 0 else 0.0
        output.append(row)

    return output


# Backward-compatible aliases: older scripts may import these names.
build_fixture_formations = build_fixture_formations_primary
build_formation_usage_summary = build_formation_usage_primary


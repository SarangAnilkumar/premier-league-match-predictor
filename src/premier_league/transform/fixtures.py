from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get(d: Optional[dict], key: str) -> Any:
    if not d:
        return None
    return d.get(key)


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        # Prevent bools from being treated as ints.
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return None


def transform_fixtures(raw_response: dict) -> list[dict]:
    """
    Normalize the API-Football fixtures payload into a clean, analytics-friendly
    list of dicts (one dict per fixture).
    """

    response_list = raw_response.get("response") if isinstance(raw_response, dict) else None
    if not isinstance(response_list, list):
        return []

    processed: list[dict] = []

    # Season is present both in response.parameters and in fixture.league.season;
    # we prefer per-fixture for consistency, but keep this as fallback.
    fallback_season = (
        _get(raw_response.get("parameters"), "season")
        if isinstance(raw_response.get("parameters"), dict)
        else None
    )

    for fixture_wrapper in response_list:
        if not isinstance(fixture_wrapper, dict):
            continue

        fixture = fixture_wrapper.get("fixture") if isinstance(fixture_wrapper.get("fixture"), dict) else {}
        league = fixture_wrapper.get("league") if isinstance(fixture_wrapper.get("league"), dict) else {}
        teams = fixture_wrapper.get("teams") if isinstance(fixture_wrapper.get("teams"), dict) else {}
        goals = fixture_wrapper.get("goals") if isinstance(fixture_wrapper.get("goals"), dict) else {}
        score = fixture_wrapper.get("score") if isinstance(fixture_wrapper.get("score"), dict) else {}

        home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
        away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

        halftime = score.get("halftime") if isinstance(score.get("halftime"), dict) else {}
        fulltime = score.get("fulltime") if isinstance(score.get("fulltime"), dict) else {}
        extratime = score.get("extratime") if isinstance(score.get("extratime"), dict) else {}
        penalty = score.get("penalty") if isinstance(score.get("penalty"), dict) else {}

        home_goals = _safe_int(goals.get("home"))
        away_goals = _safe_int(goals.get("away"))

        # Match result is based on full-time goals (API field `goals`).
        if home_goals is None or away_goals is None:
            match_result: Optional[str] = None
        elif home_goals > away_goals:
            match_result = "home_win"
        elif away_goals > home_goals:
            match_result = "away_win"
        else:
            match_result = "draw"

        season = league.get("season", fallback_season)

        processed.append(
            {
                "fixture_id": _safe_int(fixture.get("id")),
                "referee": fixture.get("referee"),
                "timezone": fixture.get("timezone"),
                # API date is already UTC ISO-8601 in this payload.
                "date_utc": fixture.get("date"),
                "timestamp": _safe_int(fixture.get("timestamp")),
                "season": season,
                "league_id": _safe_int(league.get("id")),
                "league_name": league.get("name"),
                "round": league.get("round"),
                "venue_id": _safe_int(_get(fixture.get("venue"), "id")),
                "venue_name": _get(fixture.get("venue"), "name"),
                "venue_city": _get(fixture.get("venue"), "city"),
                "status_long": _get(fixture.get("status"), "long"),
                "status_short": _get(fixture.get("status"), "short"),
                "elapsed_minutes": _safe_int(_get(fixture.get("status"), "elapsed")),
                "home_team_id": _safe_int(_get(home, "id")),
                "home_team_name": _get(home, "name"),
                "away_team_id": _safe_int(_get(away, "id")),
                "away_team_name": _get(away, "name"),
                "home_team_winner": _safe_bool(_get(home, "winner")),
                "away_team_winner": _safe_bool(_get(away, "winner")),
                "home_goals": home_goals,
                "away_goals": away_goals,
                "halftime_home_goals": _safe_int(_get(halftime, "home")),
                "halftime_away_goals": _safe_int(_get(halftime, "away")),
                "fulltime_home_goals": _safe_int(_get(fulltime, "home")),
                "fulltime_away_goals": _safe_int(_get(fulltime, "away")),
                "extratime_home_goals": _safe_int(_get(extratime, "home")),
                "extratime_away_goals": _safe_int(_get(extratime, "away")),
                "penalty_home_goals": _safe_int(_get(penalty, "home")),
                "penalty_away_goals": _safe_int(_get(penalty, "away")),
                "match_result": match_result,
            }
        )

    return processed


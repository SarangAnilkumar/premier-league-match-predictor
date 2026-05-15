from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional


def _maybe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return None
        # Common patterns: "7", "07", "".
        try:
            return int(v)
        except ValueError:
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stringify_grid(grid: Any) -> Optional[str]:
    if grid is None:
        return None
    if isinstance(grid, (dict, list)):
        return json.dumps(grid, ensure_ascii=False)
    return str(grid)


def _extract_player_entry(player_entry: Any) -> dict[str, Any]:
    """
    Best-effort extraction from lineup player objects.

    API responses can vary slightly; this keeps the transformer defensive.
    """
    entry: Dict[str, Any] = player_entry if isinstance(player_entry, dict) else {}

    # Some payloads nest player metadata under entry["player"].
    nested_player = entry.get("player") if isinstance(entry.get("player"), dict) else None

    # ID
    player_id = (
        entry.get("id")
        or entry.get("player_id")
        or (nested_player.get("id") if isinstance(nested_player, dict) else None)
        or entry.get("playerId")
        or entry.get("playerID")
    )
    player_id = _maybe_int(player_id)

    # Name
    player_name: Optional[str] = None
    if isinstance(entry.get("player"), str):
        player_name = entry.get("player")
    elif isinstance(nested_player, dict):
        player_name = nested_player.get("name") or nested_player.get("full_name")
    player_name = player_name or entry.get("name") or entry.get("playerName")

    # Number
    player_number = _maybe_int(
        entry.get("number")
        or entry.get("shirtNumber")
        or entry.get("shirt_number")
        or (nested_player.get("number") if isinstance(nested_player, dict) else None)
    )

    # Position (API uses `pos`)
    player_position: Optional[str] = (
        entry.get("position")
        or entry.get("player_position")
        or entry.get("pos")
        or (nested_player.get("pos") if isinstance(nested_player, dict) else None)
    )

    # Grid
    grid = entry.get("grid") or entry.get("coordinates") or (nested_player.get("grid") if isinstance(nested_player, dict) else None)

    return {
        "player_id": player_id,
        "player_name": player_name,
        "player_number": player_number,
        "player_position": player_position,
        "grid": _stringify_grid(grid),
    }


def _iterate_team_lineups(team_obj: dict[str, Any]) -> Iterable[tuple[str, Any]]:
    """
    Yields (lineup_type, players_list) for a team.
    """
    start_xi = team_obj.get("startXI") or team_obj.get("startXI") or team_obj.get("startXIPlayers")
    substitutes = team_obj.get("substitutes") or team_obj.get("substitute") or team_obj.get("substitutesPlayers")

    if isinstance(start_xi, list):
        yield ("starting_xi", start_xi)
    if isinstance(substitutes, list):
        yield ("substitutes", substitutes)


def transform_lineups(raw_response: dict, *, fixture_id: int) -> list[dict]:
    """
    Normalize API-Football fixture lineups payload into a list of player lineup records.

    Output records are intended for DB loading (players + fixture_lineups).
    """
    if not isinstance(raw_response, dict):
        return []

    processed: list[dict] = []

    # API responses can be either:
    # - top-level "response": list of team objects
    # - top-level "api": {"lineups"/"lineUps": {...}}
    response_list = raw_response.get("response")
    if isinstance(response_list, list):
        team_objects = response_list
    else:
        api_obj = raw_response.get("api")
        lineups_obj = None
        if isinstance(api_obj, dict):
            lineups_obj = api_obj.get("lineups") or api_obj.get("lineUps")

        # If we can't find lineups, return empty.
        if not isinstance(lineups_obj, dict):
            return []

        # lineups_obj may be keyed by team name or home/away identifiers.
        team_objects = []
        for team_key, team_value in lineups_obj.items():
            if isinstance(team_value, dict):
                team_value = dict(team_value)  # shallow copy for safety
                team_value.setdefault("team_key", team_key)
                team_objects.append(team_value)

    for team_entry in team_objects:
        if not isinstance(team_entry, dict):
            continue

        # Team identification (best-effort)
        team_id = None
        team_name: Optional[str] = None
        team_side: Optional[str] = None

        # Case 1: team object has nested "team"
        if isinstance(team_entry.get("team"), dict):
            team_id = _maybe_int(team_entry["team"].get("id"))
            team_name = team_entry["team"].get("name") or team_entry["team"].get("full_name")

        # Case 2: keyed response (team_key stored in team_entry)
        if team_name is None:
            team_name = team_entry.get("team_name") or team_entry.get("name")

        team_key = team_entry.get("team_key")
        if isinstance(team_key, str) and team_key.strip().lower() in {"home", "away"}:
            team_side = team_key.strip().lower()

        formation = team_entry.get("formation") or team_entry.get("Formation")

        # Some payloads nest lineup data inside the team object; others use keys at the same level.
        team_lineup_obj = team_entry

        for lineup_type, players_list in _iterate_team_lineups(team_lineup_obj):
            for player_entry in players_list:
                player_data = _extract_player_entry(player_entry)

                processed.append(
                    {
                        "fixture_id": fixture_id,
                        "team_id": team_id,
                        "team_name": team_name,
                        "team_side": team_side,
                        "formation": formation,
                        "lineup_type": lineup_type,
                        **player_data,
                    }
                )

    return processed


from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        try:
            return int(v)
        except ValueError:
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_fee_amount(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip().replace(",", "")
    if not text:
        return None

    # Handles common API strings such as:
    # "€45M", "€2.5M", "€850K", "1500000", "Free"
    match = re.search(r"(\d+(?:\.\d+)?)\s*([MKmk]?)", text)
    if not match:
        return None

    number = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "m":
        number *= 1_000_000
    elif suffix == "k":
        number *= 1_000
    return int(number)


def _normalize_transfer_type_and_fee(raw_type: Any) -> tuple[Optional[str], Optional[int]]:
    """
    API-Football's `type` field is overloaded:
    - semantic transfer labels: "Loan", "Free", "Return from loan", etc.
    - fee-like strings: "€ 16.5M", "250K", ...

    Normalize into:
    - in_out: categorical transfer label for analytics
    - fee_amount: integer numeric fee when present
    """
    if not isinstance(raw_type, str):
        return None, None

    value = raw_type.strip()
    if not value:
        return None, None

    parsed_fee = _parse_fee_amount(value)
    if parsed_fee is not None:
        # Keep transfer label categorical; avoid fee strings polluting `in_out`.
        return "Transfer", parsed_fee

    return value, None


def _infer_transfer_period(date_value: Optional[str]) -> Optional[str]:
    if not date_value:
        return None
    try:
        dt = datetime.fromisoformat(date_value)
    except ValueError:
        return None
    # Simple heuristic for European windows.
    if dt.month in {6, 7, 8, 9}:
        return "Summer"
    return "Winter"


def _infer_season(date_value: Optional[str]) -> Optional[str]:
    if not date_value:
        return None
    try:
        dt = datetime.fromisoformat(date_value)
    except ValueError:
        return None
    # EPL-like season boundary: July belongs to new season year.
    return str(dt.year if dt.month >= 7 else dt.year - 1)


def transform_transfers(raw_response: dict) -> list[dict[str, Any]]:
    """
    Normalize API-Football transfers payload into a flat list of transfer rows.
    """
    response = raw_response.get("response") if isinstance(raw_response, dict) else None
    if not isinstance(response, list):
        return []

    rows: list[dict[str, Any]] = []
    for entry in response:
        if not isinstance(entry, dict):
            continue
        player = entry.get("player") if isinstance(entry.get("player"), dict) else {}
        player_id = _safe_int(player.get("id"))
        player_name = player.get("name")

        transfers = entry.get("transfers")
        if not isinstance(transfers, list):
            continue

        for t in transfers:
            if not isinstance(t, dict):
                continue
            teams = t.get("teams") if isinstance(t.get("teams"), dict) else {}
            team_in = teams.get("in") if isinstance(teams.get("in"), dict) else {}
            team_out = teams.get("out") if isinstance(teams.get("out"), dict) else {}

            transfer_type = t.get("type")
            transfer_date = t.get("date")
            normalized_type, fee_amount = _normalize_transfer_type_and_fee(transfer_type)

            rows.append(
                {
                    "season": _infer_season(transfer_date),
                    "transfer_period": _infer_transfer_period(transfer_date),
                    "transfer_date": transfer_date,
                    "player_id": player_id,
                    "player_name": player_name,
                    "from_team_id": _safe_int(team_out.get("id")),
                    "from_team_name": team_out.get("name"),
                    "to_team_id": _safe_int(team_in.get("id")),
                    "to_team_name": team_in.get("name"),
                    "in_out": normalized_type,
                    "fee_amount": fee_amount,
                }
            )

    return rows

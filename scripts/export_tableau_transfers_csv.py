from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "pl_ingestion.sqlite"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "tableau_transfers_flat.csv"


def _format_fee_short(value: Any) -> str:
    if value is None:
        return ""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return ""

    if amount >= 1_000_000:
        shown = amount / 1_000_000
        text = f"{shown:.1f}".rstrip("0").rstrip(".")
        return f"€ {text}M"
    if amount >= 1_000:
        shown = amount / 1_000
        text = f"{shown:.1f}".rstrip("0").rstrip(".")
        return f"€ {text}K"
    return f"€ {amount}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export transfer data from SQLite into a Tableau-friendly flat CSV."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to SQLite DB file (default: data/pl_ingestion.sqlite).",
    )
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to output CSV (default: data/processed/tableau_transfers_flat.csv).",
    )
    parser.add_argument(
        "--season",
        default=None,
        help="Optional season filter (e.g. 2024). If omitted, exports all seasons.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db_path)
    output_path = Path(args.output_path)
    season = args.season

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    query = """
    SELECT
      t.season,
      t.transfer_period,
      t.transfer_date,
      strftime('%Y-%m', date(t.transfer_date)) AS transfer_month,
      strftime('%Y-W%W', date(t.transfer_date)) AS transfer_week,
      CASE strftime('%w', date(t.transfer_date))
        WHEN '0' THEN 'Sunday'
        WHEN '1' THEN 'Monday'
        WHEN '2' THEN 'Tuesday'
        WHEN '3' THEN 'Wednesday'
        WHEN '4' THEN 'Thursday'
        WHEN '5' THEN 'Friday'
        WHEN '6' THEN 'Saturday'
        ELSE NULL
      END AS transfer_day_of_week,
      t.player_id,
      p.name AS player_name,
      t.from_team_id,
      ft.name AS from_team_name,
      t.to_team_id,
      tt.name AS to_team_name,
      CASE
        WHEN LOWER(TRIM(COALESCE(t.in_out, ''))) IN ('', '-', 'n/a') THEN 'Unknown'
        WHEN LOWER(TRIM(t.in_out)) = 'back from loan' THEN 'Return from loan'
        WHEN LOWER(TRIM(t.in_out)) IN ('free transfer', 'free agent') THEN 'Free'
        ELSE t.in_out
      END AS transfer_type,
      CASE
        WHEN
          t.to_team_id IS NOT NULL
          AND EXISTS (
            SELECT 1
            FROM fixtures f
            WHERE f.season = t.season
              AND (f.home_team_id = t.to_team_id OR f.away_team_id = t.to_team_id)
          )
          AND t.from_team_id IS NOT NULL
          AND EXISTS (
            SELECT 1
            FROM fixtures f
            WHERE f.season = t.season
              AND (f.home_team_id = t.from_team_id OR f.away_team_id = t.from_team_id)
          )
          THEN 'Internal PL'
        WHEN
          t.to_team_id IS NOT NULL
          AND EXISTS (
            SELECT 1
            FROM fixtures f
            WHERE f.season = t.season
              AND (f.home_team_id = t.to_team_id OR f.away_team_id = t.to_team_id)
          )
          THEN 'Incoming to PL'
        WHEN
          t.from_team_id IS NOT NULL
          AND EXISTS (
            SELECT 1
            FROM fixtures f
            WHERE f.season = t.season
              AND (f.home_team_id = t.from_team_id OR f.away_team_id = t.from_team_id)
          )
          THEN 'Outgoing from PL'
        ELSE 'External/Unknown'
      END AS movement_direction,
      t.fee_amount AS fee_amount_numeric
    FROM transfers t
    LEFT JOIN players p ON t.player_id = p.id
    LEFT JOIN teams ft ON t.from_team_id = ft.id
    LEFT JOIN teams tt ON t.to_team_id = tt.id
    """
    params: tuple[str, ...] = ()
    if season:
        query += " WHERE t.season = ?"
        params = (season,)
    query += " ORDER BY t.season, player_name, from_team_name, to_team_name"

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    finally:
        conn.close()

    output_rows: list[list[Any]] = []
    for row in rows:
        row_dict = dict(zip(cols, row))
        fee_numeric = row_dict.get("fee_amount_numeric")
        row_dict["fee_amount"] = _format_fee_short(fee_numeric)
        output_rows.append([row_dict.get(c) for c in cols] + [row_dict["fee_amount"]])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols + ["fee_amount"])
        writer.writerows(output_rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()

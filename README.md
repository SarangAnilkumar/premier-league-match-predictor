# Premier League Tactical Analytics Pipeline

API-Football ingestion pipeline for Premier League data with SQLite persistence, deterministic transforms, and reproducible analytics outputs.

## Scope

Implemented:

- Fixtures ingestion (`GET /fixtures`) with raw save, cleaned transform, and DB upsert
- Fixture lineups ingestion (`GET /fixtures/lineups`) for selected fixture IDs
- Transfers ingestion (`GET /transfers`) for league teams in a target season
- Schema-managed SQLite warehouse with ingestion run tracking
- Formation analytics read models (JSON outputs)
- Transfer dashboard export (`tableau_transfers_flat.csv`)

Not implemented:

- Standings ingestion
- API service layer (FastAPI/Flask)
- Automated tests/CI

## Architecture

```text
API-Football
  -> scripts/ingest_*.py
    -> src/pl_ingestion/api_football_client.py
    -> src/pl_ingestion/ingestion/*
    -> src/pl_ingestion/transform/*
    -> src/pl_ingestion/database/*
      -> SQLite (data/pl_ingestion.sqlite)
      -> ingestion_runs

SQLite
  -> scripts/build_formation_analytics.py
    -> data/processed/api_football/*.json

SQLite
  -> scripts/export_tableau_transfers_csv.py
    -> data/processed/tableau_transfers_flat.csv
```

Key modules:

- `src/pl_ingestion/config.py`
- `src/pl_ingestion/api_football_client.py`
- `src/pl_ingestion/ingestion/`
- `src/pl_ingestion/transform/`
- `src/pl_ingestion/database/`
- `src/pl_ingestion/analytics/formation_aggregator.py`
- `scripts/`

## Pipeline Run Order

```bash
# 1) environment + deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `API_FOOTBALL_API_KEY` in `.env`.

```bash
# 2) initialize schema
python3 scripts/init_db.py

# 3) ingest fixtures (season)
python3 scripts/ingest_fixtures.py --season 2024

# 4) ingest lineups (controlled subset)
python3 scripts/ingest_lineups.py --season 2024 --first-n 20 --batch-size 5

# 5) ingest transfers
python3 scripts/ingest_transfers.py --season 2024 --sleep-seconds-between-requests 0.5

# 6) build formation read models
python3 scripts/build_formation_analytics.py

# 7) export transfer dashboard flat file
python3 scripts/export_tableau_transfers_csv.py

# 8) audit health
python3 scripts/audit_db.py
```

## Data Contracts (Generated Locally)

Raw API payloads:

- `data/raw/api_football/fixtures_league_<league_id>_season_<season>.json`
- `data/raw/api_football/lineups_fixture_<fixture_id>.json`
- `data/raw/api_football/transfers_league_<league_id>_season_<season>.json`

Processed/read-model outputs:

- `data/processed/api_football/fixtures_cleaned.json`
- `data/processed/api_football/starting_formations.json`
- `data/processed/api_football/formation_usage_full.json`
- `data/processed/api_football/formation_usage_primary.json`
- `data/processed/api_football/formation_usage_summary.json`
- `data/processed/api_football/fixture_formations.json`
- `data/processed/api_football/fixture_formations_primary.json`
- `data/processed/api_football/formation_matchups.json`
- `data/processed/api_football/formation_matchup_summary.json`
- `data/processed/tableau_transfers_flat.csv`

Note: `data/` outputs are generated locally and not expected to be fully tracked in git.

## Operational Notes

- Cache-first behavior reduces unnecessary API calls; use `--force-refresh` when needed.
- Request pacing flags are available on ingestion scripts to respect API limits.
- Transfer ingestion can be reprocessed from previously saved raw payloads via `--raw-path`.

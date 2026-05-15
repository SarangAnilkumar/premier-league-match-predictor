# Architecture (Current Ingestion Foundation)

> Visual diagram: [architecture-diagram.html](./architecture-diagram.html)

## High-Level Flow
1. **Load settings** from environment variables (`src/premier_league/config.py`)
2. **Call API-Football** via an HTTP client with retries (`src/premier_league/clients/api_football.py`)
3. **Persist raw JSON** to disk for inspection (`src/premier_league/io/artifacts.py` + fixtures ingestor)
4. **Transform raw payload** into a normalized list of fixtures (`src/premier_league/transform/fixtures.py`)
5. **Persist cleaned JSON** to a separate processed location
6. **Upsert fixtures into SQLite** (reference `teams` + event `fixtures`) and record an `ingestion_runs` entry
7. **(Optional) Ingest fixture lineups** for a controlled subset of fixture IDs into SQLite (reference `players` + event `fixture_lineups`) and record an `ingestion_runs` entry

## DB-Backed Foundation (Implemented)
The project includes a SQLite + SQLAlchemy database foundation under `src/premier_league/database/`.

- `scripts/db_init.py` creates the schema locally.
- ORM models define reference/master tables (`teams`, `players`), event tables (`fixtures`, `fixture_lineups`, `transfers`), and an ingestion tracking table (`ingestion_runs`).

## Cache-First Direction (Implemented for Fixtures and Fixture Lineups)
API-Football has a 100 requests/day limit.

Fixtures ingestion is cache-first: before calling the external API, the pipeline checks SQLite for existing fixtures for the requested `(league_id, season)`.
If fixtures are already present and `--force-refresh` is not provided, the API call is skipped and the ingestion run is recorded as a cache hit.

Fixture lineups ingestion is also cache-first: before calling the external API for a given `fixture_id`, the pipeline checks whether `fixture_lineups` rows already exist for that fixture (unless `--force-refresh` is provided).

## Code Structure
- `src/premier_league/config.py` — API and logging settings (`Settings.from_env()`)
- `src/premier_league/paths.py` — canonical artifact paths (DB, exports, read models)
- `src/premier_league/clients/api_football.py` — HTTP client (`APIFootballClient`)
- `src/premier_league/ingestion/fixtures.py` — `FixturesIngestor`
- `src/premier_league/ingestion/fixtures_cache.py` — cache-first decision for fixtures
- `src/premier_league/ingestion/lineups.py` — `FixtureLineupsIngestor`
- `src/premier_league/ingestion/lineups_cache.py` — cache-first decision for lineups
- `src/premier_league/ingestion/transfers.py` — `TransfersIngestor`
- `src/premier_league/transform/fixtures.py` — `transform_fixtures()`
- `src/premier_league/transform/lineups.py` — `transform_lineups()`
- `src/premier_league/transform/transfers.py` — `transform_transfers()`
- `src/premier_league/database/loaders/` — upsert loaders for fixtures, lineups, transfers
- `src/premier_league/analytics/formations.py` — formation read-model builders
- `src/premier_league/selection/fixture_ids.py` — DB-only fixture selection helpers

## CLI Entry Points
| Script | Purpose |
|--------|---------|
| `scripts/db_init.py` | Create SQLite schema |
| `scripts/ingest_fixtures.py` | Fixtures ETL (`--force-refresh`) |
| `scripts/ingest_lineups.py` | Lineups ETL (controlled subsets) |
| `scripts/ingest_transfers.py` | Transfers ETL (`--raw-path` supported) |
| `scripts/export_formation_read_models.py` | DB → formation JSON read models |
| `scripts/export_transfers_csv.py` | DB → `data/exports/transfers_flat.csv` |
| `scripts/db_audit.py` | SQLite health report |

## Data Artifacts
- Raw fixtures payload:
  - `data/raw/api_football/fixtures_league_<league_id>_season_<season>.json`
- Cleaned fixtures payload:
  - `data/processed/api_football/fixtures_normalized.json`
- Formation read models:
  - `data/processed/read_models/formations/*.json`
- Transfer export:
  - `data/exports/transfers_flat.csv`
- Database:
  - `data/premier_league.db` (override via `PREMIER_LEAGUE_DB_PATH`, `PL_DB_PATH`, or `DB_PATH`)

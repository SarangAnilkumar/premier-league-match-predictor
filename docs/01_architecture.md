# Architecture (Current Ingestion Foundation)

## High-Level Flow
1. **Load settings** from environment variables (`src/pl_ingestion/config.py`)
2. **Call API-Football** via an HTTP client with retries (`src/pl_ingestion/api_football_client.py`)
3. **Persist raw JSON** to disk for inspection (`src/pl_ingestion/utils.py` + fixtures ingestor)
4. **Transform raw payload** into a normalized list of fixtures (`src/pl_ingestion/transform/fixtures_transformer.py`)
5. **Persist cleaned JSON** to a separate processed location
6. **Upsert fixtures into SQLite** (reference `teams` + event `fixtures`) and record an `ingestion_runs` entry
7. **(Optional) Ingest fixture lineups** for a controlled subset of fixture IDs into SQLite (reference `players` + event `fixture_lineups`) and record an `ingestion_runs` entry

## DB-Backed Foundation (Implemented)
The project now includes an initial SQLite + SQLAlchemy database foundation under `src/pl_ingestion/database/`.

- `scripts/init_db.py` creates the schema locally.
- ORM models define reference/master tables (`teams`, `players`), event tables (`fixtures`, `fixture_lineups`, `transfers`), and an ingestion tracking table (`ingestion_runs`).

## Cache-First Direction (Implemented for Fixtures and Fixture Lineups)
API-Football has a 100 requests/day limit.

Fixtures ingestion is now cache-first: before calling the external API, the pipeline checks SQLite for existing fixtures for the requested `(league_id, season)`.
If fixtures are already present and `--force-refresh` is not provided, the API call is skipped and the ingestion run is recorded as a cache hit.

Fixture lineups ingestion is also cache-first: before calling the external API for a given `fixture_id`, the pipeline checks whether `fixture_lineups` rows already exist for that fixture (unless `--force-refresh` is provided).

## Code Structure
- `src/pl_ingestion/config.py`
  - `Settings.from_env()` loads:
    - base URL
    - league ID
    - season
    - request timeout
    - API key (from env; not hardcoded)
- `src/pl_ingestion/api_football_client.py`
  - `APIFootballClient.get_fixtures(...)` (GET `/fixtures`)
  - Adds authentication header `x-apisports-key`
  - Configures retries for transient HTTP failures
- `src/pl_ingestion/ingestion/fixtures_ingestor.py`
  - `FixturesIngestor.ingest(...)` orchestrates:
    - raw fetch → raw save
    - raw → cleaned transformation
    - cleaned save
    - cleaned fixtures → DB upsert (teams, fixtures) + `ingestion_runs`
- `src/pl_ingestion/ingestion/fixtures_cache_service.py`
  - `decide_fixtures_refresh(...)` implements the cache-first decision logic (presence-based for now)
- `src/pl_ingestion/ingestion/fixture_lineups_cache_service.py`
  - `decide_fixture_lineups_refresh(...)` implements the cache-first decision logic (presence-based for now)
- `src/pl_ingestion/transform/fixtures_transformer.py`
  - `transform_fixtures(raw_response: dict) -> list[dict]`
  - Extracts and normalizes fixture fields, including derived `match_result`
- `src/pl_ingestion/transform/lineups_transformer.py`
  - `transform_lineups(raw_response: dict, fixture_id=...) -> list[dict]`
  - Extracts and normalizes lineup fields (formation, player info, lineup_type, etc.)
- `scripts/ingest_fixtures.py`
  - CLI runner for ingestion (loads `.env` if present)
- `src/pl_ingestion/database/`
  - Initial DB schema + connection management (SQLite-first)
- `src/pl_ingestion/database/fixtures_loader.py`
  - Upserts `teams`, `fixtures`, and updates `ingestion_runs`
- `src/pl_ingestion/database/lineups_loader.py`
  - Upserts `players`, `fixture_lineups`, and updates `ingestion_runs`
- `scripts/ingest_fixtures.py`
  - CLI runner supports `--force-refresh` to override cached data
- `scripts/ingest_lineups.py`
  - CLI runner supports `--fixture-ids` and `--force-refresh` to ingest lineups for a controlled subset
- `scripts/init_db.py`
  - Creates the DB tables locally

## Data Artifacts
- Raw fixtures payload:
  - `data/raw/api_football/fixtures_league_<league_id>_season_<season>.json`
- Cleaned fixtures payload:
  - `data/processed/api_football/fixtures_cleaned.json`


# Database Schema (Current)

## Why SQLite first
- Zero operational setup for local development (single file DB).
- Great fit for early-stage ingestion validation, transformation checks, and portfolio demonstration.
- Keeps the “system of record” close to the ingestion pipeline while API-Football request limits are tight.

## Where the DB lives
- Default DB path (can be overridden via env):
  - `data/pl_ingestion.sqlite` (override via `PL_DB_PATH` or `DB_PATH`)
- DB is initialized by:
  - `scripts/init_db.py`

## Database module
- `src/pl_ingestion/database/`
  - `db_config.py`: DB path/loading from environment
  - `connection.py`: SQLAlchemy engine + session helpers
  - `models.py`: ORM model definitions + indexes/constraints
  - `schema.py`: runs `Base.metadata.create_all(...)`

## Tables (by category)

### Reference / master tables
- `teams`
  - Stores team identifiers and basic metadata.
  - Includes ingestion/cache tracking fields (e.g., `ingested_at`, `last_refreshed_at`, `source_name`, `raw_payload_path`).
- `players`
  - Stores player identifiers and basic metadata.
  - Includes ingestion/cache tracking fields.

### Event tables
- `fixtures`
  - Stores normalized fixture/match results (one row per `fixture_id`).
  - Contains match outcome fields and goal breakdown fields, plus caching/ingestion metadata.
  - Foreign keys:
    - `home_team_id` -> `teams.id`
    - `away_team_id` -> `teams.id`
- `fixture_lineups`
  - Stores player appearances for a fixture.
  - Stores tactical context (where provided by the API), including:
    - `formation`
    - `lineup_type` (e.g., starting XI vs substitutes)
    - `grid` (best-effort grid/co-ordinate info)
  - Stores player metadata for tactical analysis, including:
    - `player_name`
    - `player_number`
    - `player_position`
  - Foreign keys:
    - `fixture_id` -> `fixtures.fixture_id`
    - `player_id` -> `players.id`
    - `team_id` -> `teams.id` (nullable until team/lineup ingestion is added)
- `transfers`
  - Stores transfer events for players between teams.
  - Foreign keys:
    - `player_id` -> `players.id` (nullable until players/transfers ingestion is added)
    - `from_team_id`/`to_team_id` -> `teams.id`

### Ingestion tracking
- `ingestion_runs`
  - Tracks ingestion runs and caching metadata.
  - Captures:
    - `source_name`, `endpoint`, `run_type`, optional `league_id`/`season`
    - deterministic `run_key` for idempotent upserts
    - `status`, `started_at`, `completed_at`
    - `error_message` on failure
    - `raw_payload_path` pointing to the stored raw JSON (when used by the ingestor)
    - best-effort `records_written` (varies by run type; fixtures loader writes teams+fixtures, lineups loader writes players+fixture_lineups)

## Notes
- The ingestion scripts currently still write raw + cleaned JSON to disk.
- The fixtures ingestion pipeline now upserts:
  - `teams` (derived from home/away teams)
  - `fixtures` (derived from cleaned fixtures)
  - `ingestion_runs` (loader status + metadata)
- Cache-first API gating is implemented for fixtures and fixture lineups using a presence-based strategy (and `--force-refresh` to override).

## Analytics Read Model (Formations)
- Formation analytics datasets are derived from:
  - `fixtures` (match metadata + goals)
  - `fixture_lineups` (formation + lineup coverage)
  - `teams` (team names)
- Current artifacts are built by `scripts/build_formation_analytics.py` and saved to:
  - `data/processed/api_football/formation_usage_summary.json`
  - `data/processed/api_football/fixture_formations.json`


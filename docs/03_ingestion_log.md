# Ingestion Logging

## What exists now
- The CLI runner (`scripts/ingest_fixtures.py`) configures Python logging via `logging.basicConfig(...)`.
- The log level is controlled by `LOG_LEVEL` loaded from the environment (see `src/pl_ingestion/config.py`).
- The API client (`src/pl_ingestion/api_football_client.py`) logs:
  - an `info` message when fetching fixtures
- The fixtures ingestor (`src/pl_ingestion/ingestion/fixtures_ingestor.py`) logs:
  - a full stack trace (`logger.exception(...)`) if fetching fails, then re-raises
- JSON saving is logged (`src/pl_ingestion/utils.py`) with the output file path.

## Where logs go
- By default, logs are emitted to stdout/stderr via Python’s standard logging configuration.

## Not yet implemented (planned)
- Persistent log files (e.g., rotating file handler)
- Correlation IDs for multi-step ingestion runs
- Structured logging (JSON logs) suitable for log aggregation

## Database-based ingestion tracking (Implemented Foundation)
- The schema now includes `ingestion_runs` table (`src/pl_ingestion/database/models.py`).
- This table is designed to capture:
  - source name / endpoint
  - league_id and season (when applicable)
  - run status and timestamps
  - error message (if applicable)
  - `raw_payload_path` pointing at the saved raw JSON
- Cache-first flags:
  - `fetched_from_api` (1/0)
  - `cache_hit` (1/0)

## Wired (fixtures ingestion)
- The fixtures ingestion CLI (`scripts/ingest_fixtures.py`) now also creates/updates an `ingestion_runs` row in SQLite.
- `FixturesIngestor` updates ingestion status:
  - `cache_hit` when fixtures already exist in SQLite and `--force-refresh` is not set
  - `running` at the start of an API-backed load
  - `success` after teams/fixtures upserts
  - `error` (with `error_message`) if loading fails
- The DB write happens after transformation and cleaned JSON persistence.

## Wired (fixture lineups ingestion)
- The lineups ingestion CLI (`scripts/ingest_lineups.py`) ingests a controlled subset of `fixture_id`s.
- The CLI supports batching via `--batch-size` to process large fixture lists in safe chunks with clearer progress reporting.
- The ingestor emits aggregate run counters (total requested, cache hits/skips, API fetches, successful writes, and any failed/skipped `fixture_id`s).
- For each fixture, the pipeline checks SQLite for existing `fixture_lineups` rows:
  - if present and `--force-refresh` is not set, it records `ingestion_runs.status=cache_hit` and skips the API call
  - otherwise, it fetches lineups from API-Football, saves raw lineup JSON, transforms it, and upserts `players` + `fixture_lineups`
- In API-backed runs, `ingestion_runs.fetched_from_api` is set to `1` and `cache_hit` to `0`.

## Analytics dataset build (Implemented for formations)
- A local-only analytics step exists to build formation-based datasets from SQLite:
  - `scripts/build_formation_analytics.py`
- This step:
  - uses only the existing database tables (`fixtures`, `fixture_lineups`, `teams`)
  - does not call the external API
  - writes deterministic JSON artifacts to `data/processed/api_football/`.

### Formation datasets produced
- `starting_formations.json` (starting XI only; one row per fixture/team)
- `formation_usage_full.json` (aggregated over all distinct formations observed in `fixture_lineups`)
- `formation_usage_primary.json` and legacy aliases:
  - `formation_usage_summary.json` (alias of the primary dataset)
- `fixture_formations_primary.json` and legacy alias:
  - `fixture_formations.json` (alias of the primary fixture formation dataset)


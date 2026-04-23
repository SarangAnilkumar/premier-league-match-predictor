# Next Steps

## 0. Improve freshness strategy (beyond presence)
Cache-first API gating for fixtures and fixture lineups is now implemented using a simple presence-based strategy:
- Fixtures: if fixtures already exist in SQLite for the requested `(league_id, season)` and `--force-refresh` is not set, the external API call is skipped.
- Fixture lineups: if `fixture_lineups` rows already exist for the requested `fixture_id` and `--force-refresh` is not set, the external API call is skipped.

Next milestone:
- Add a staleness/TTL strategy (e.g., refresh if `fixtures.last_refreshed_at` is older than a threshold).
- Record richer cache metadata in `fixtures` / `ingestion_runs` (as planned) to drive incremental refresh decisions.

## 1. Extend ingestion beyond fixtures
Current progress:
- Fixture lineups ingestion is implemented for a controlled subset of `fixture_id`s (`scripts/ingest_lineups.py`), including formation + lineup_type and upserting players referenced in lineups.
- The CLI supports batching of fixture IDs via `--batch-size` to reduce operational risk with tight API limits.

Implemented additions:
- Transfers ingestion is implemented via `scripts/ingest_transfers.py` (GET `/transfers?team=<team_id>` for all teams found in `fixtures` for the requested season).
  - Important: transfers can reference non-Premier-League clubs, so the loader upserts referenced `teams`/`players` before inserting into `transfers` to satisfy FK constraints.
  - For request-efficiency, `scripts/ingest_transfers.py` also supports loading from an already-saved raw JSON file via `--raw-path` (no API calls).

Planned additions (engineering steps, not implemented yet):
- Enrich match data with additional attributes needed for analytics/ML.
- Add ingestion modules for:
  - teams/standings
  - (more) transfers enrichment (fees/currencies, better date parsing, league scoping)

## 2. Request-efficiency improvements
To respect API request/day constraints:
- Implement caching and incremental ingestion (avoid refetching unchanged seasons/results).
- Enforce DB-first strategy so analytics can reuse stored data without repeated API calls.

## 3. Extend DB loaders
Fixtures DB loading is implemented (upsert into `teams` and `fixtures`, plus `ingestion_runs` tracking).

DB loaders implemented:
- `transfers` loader exists and is wired by `scripts/ingest_transfers.py`.

## Tactical Analytics Read Models
Formation analytics datasets are now implemented as a local-only read model:
- `scripts/build_formation_analytics.py`
- outputs:
  - `data/processed/api_football/starting_formations.json`
  - `data/processed/api_football/formation_usage_full.json`
  - `data/processed/api_football/formation_usage_primary.json` (legacy alias: `formation_usage_summary.json`)
  - `data/processed/api_football/fixture_formations_primary.json` (legacy alias: `fixture_formations.json`)
  - `data/processed/api_football/formation_matchups.json`
  - `data/processed/api_football/formation_matchup_summary.json`

Next milestone:
- wire additional derived datasets needed by the frontend (without touching API limits).

## 4. Operational hardening
- Add persistent ingestion logs and run metadata tracking.
- Add unit tests for transformation logic (defensive handling of missing/null nested fields).
- Extend the DB audit/report script (`scripts/audit_db.py`) to add more targeted invariants as the DB volume grows.
- Add rate-limit-aware backoff/retry policy at the ingestion layer (beyond payload validation) to reduce error frequency as volumes grow.
- Next step is to add adaptive pacing (e.g., automatically increase sleep after repeated rateLimit payloads) on top of the fixed CLI throttles.

## 5. Frontend integration readiness
- After DB-first loading exists, expose data to the frontend via a backend API (FastAPI is planned later; not part of this phase).


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

Planned additions (engineering steps, not implemented yet):
- Enrich match data with additional attributes needed for analytics/ML.
- Add ingestion modules for:
  - teams/standings
  - transfers

## 2. Request-efficiency improvements
To respect API request/day constraints:
- Implement caching and incremental ingestion (avoid refetching unchanged seasons/results).
- Enforce DB-first strategy so analytics can reuse stored data without repeated API calls.

## 3. Extend DB loaders
Fixtures DB loading is implemented (upsert into `teams` and `fixtures`, plus `ingestion_runs` tracking).

Next milestone is to add DB loaders for additional datasets as ingestion expands:
- transfers

## 4. Operational hardening
- Add persistent ingestion logs and run metadata tracking.
- Add unit tests for transformation logic (defensive handling of missing/null nested fields).

## 5. Frontend integration readiness
- After DB-first loading exists, expose data to the frontend via a backend API (FastAPI is planned later; not part of this phase).


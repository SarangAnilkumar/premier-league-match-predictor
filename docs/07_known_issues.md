# Known Issues / Constraints

## Legacy Dashboard Dependencies

- The existing HTML dashboard (`SarangAnilkumar_34662774_Code.html`) was built around CSV-derived data.
- The migration is ongoing; the dashboard still reflects the earlier CSV workflow.

## API Limitations for Formations

- The current fixtures ingestion uses `GET /fixtures` for a league+season.
- Formations are not provided directly by this endpoint in the current ingestion pipeline.
- Fixture lineups ingestion uses `GET /fixtures/lineups` for a specific `fixture_id`, which includes formation data.
- Future enhancement will require additional data sources/endpoints or enriched match-level detail.

## Request Limit and Cache-First Wiring

- API-Football has a 100 requests/day limit.
- The fixtures and fixture lineups ingestion pipelines now upsert data into SQLite, including ingestion tracking metadata.
- Cache-first *API gating* is now implemented for:
  - external API is skipped when fixtures already exist for `(league_id, season)` and `--force-refresh` is not set.
  - `ingestion_runs.status` is set to `cache_hit` for skipped runs.
  - external API is skipped when `fixture_lineups` rows already exist for a given `fixture_id` and `--force-refresh` is not set.
- Current freshness strategy is presence-based only; it does not yet implement a TTL/staleness threshold beyond `--force-refresh`.

## Batching / Partial Runs

- `scripts/ingest_lineups.py` supports `--batch-size` for chunked processing of larger fixture id lists.
- The ingestion continues past failures for individual `fixture_id`s and logs failures while recording error statuses in `ingestion_runs`.

## Current Scope

- `scripts/audit_db.py` provides a non-invasive SQLite health report (counts + coverage + completeness metrics) to validate schema/cache/loader behavior as you ingest more data.
- Fixtures ingestion is implemented end-to-end (raw save + cleaned transform + DB upsert for teams/fixtures + ingestion tracking).
- Fixture lineups ingestion is implemented for a controlled subset of `fixture_id`s via `scripts/ingest_lineups.py` (raw save + transform + DB upsert for players/fixture_lineups + ingestion tracking), with cache-first behavior.
- Standings, transfers ingestion into the database are not yet implemented.


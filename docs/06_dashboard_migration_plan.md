# Dashboard Migration Plan (DB-First)

## Current Situation
- The ingestion system has moved to:
  - API-Football → raw JSON → cleaned JSON → SQLite upserts
  - cache-first ingestion behavior to reduce external API calls

## Migration Strategy
1. Replace ad-hoc/static visual data inputs with DB-derived “read model” outputs.
2. Build derived datasets in repeatable scripts that:
   - use only the local SQLite database (no external API calls)
   - produce deterministic, sorted JSON outputs
3. Point analytics/dashboard layers at the processed artifacts produced by these scripts.

## Implemented Read Models (First)
- Formation-based analytics datasets are now generated from the database:
  - `data/processed/api_football/starting_formations.json`
  - `data/processed/api_football/formation_usage_full.json`
  - `data/processed/api_football/formation_usage_primary.json` (legacy alias: `formation_usage_summary.json`)
  - `data/processed/api_football/fixture_formations_primary.json` (legacy alias: `fixture_formations.json`)
- New tactical matchup read models:
  - `data/processed/api_football/formation_matchups.json`
  - `data/processed/api_football/formation_matchup_summary.json`

## Next Steps
- Ensure downstream dashboards consume processed DB-derived artifacts as their single source of truth.
- Extend the read model approach to additional tactical datasets (as lineups/players/transfers ingestion grows).


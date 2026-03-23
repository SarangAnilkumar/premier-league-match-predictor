# Dashboard Migration Plan (DB-First)

## Current Situation
- The legacy dashboard (`SarangAnilkumar_34662774_Code.html`) was originally built around static CSV datasets.
- The ingestion system has moved to:
  - API-Football → raw JSON → cleaned JSON → SQLite upserts
  - cache-first ingestion behavior to reduce external API calls

## Migration Strategy
1. Replace CSV-driven visualizations with DB-derived “read model” JSON.
2. Build derived datasets in repeatable scripts that:
   - use only the local SQLite database (no external API calls)
   - produce deterministic, sorted JSON outputs
3. Point frontend visualization code at the processed JSON artifacts produced by these scripts.

## Implemented Read Models (First)
- Formation-based analytics datasets are now generated from the database:
  - `data/processed/api_football/starting_formations.json`
  - `data/processed/api_football/formation_usage_full.json`
  - `data/processed/api_football/formation_usage_primary.json` (legacy alias: `formation_usage_summary.json`)
  - `data/processed/api_football/fixture_formations_primary.json` (legacy alias: `fixture_formations.json`)

## Next Steps
- Update the frontend visualization layer to consume these processed JSON artifacts instead of CSV files.
- Extend the read model approach to additional tactical datasets (as lineups/players/transfers ingestion grows).


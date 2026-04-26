# Project Overview

## Goal
Build a maintainable, database-backed Premier League analytics system powered by API-Football.

## Current State
The repo contains a Python ingestion + analytics foundation that fetches Premier League data from API-Football, persists raw payloads, and builds normalized DB-backed datasets for analytics and dashboard use.

## What’s Implemented (as of now)
- API-Football HTTP client (requests-based) with retries and timeouts
- Fixtures ingestion pipeline (`scripts/ingest_fixtures.py`) that:
  - fetches fixtures for a given league + season
  - saves raw JSON for inspection
  - transforms fixtures into a cleaned schema and saves processed JSON
  - upserts teams/fixtures into SQLite and records `ingestion_runs`
- Fixture lineups ingestion pipeline (`scripts/ingest_lineups.py`) for controlled fixture subsets:
  - fetches `GET /fixtures/lineups` by `fixture_id`
  - transforms lineup/player/formation data
  - upserts players + fixture lineups into SQLite
- Transfers ingestion pipeline (`scripts/ingest_transfers.py`) that:
  - fetches `GET /transfers?team=<team_id>` for season teams
  - supports reprocessing from saved raw payloads (`--raw-path`)
  - upserts teams/players/transfers into SQLite
- Formation analytics build pipeline (`scripts/build_formation_analytics.py`) producing read-model JSONs for tactical analysis

## Output Artifacts
- Raw API responses:
  - `data/raw/api_football/fixtures_league_<league_id>_season_<season>.json`
  - `data/raw/api_football/lineups_fixture_<fixture_id>.json`
  - `data/raw/api_football/transfers_league_<league_id>_season_<season>.json`
- Cleaned fixtures dataset:
  - `data/processed/api_football/fixtures_cleaned.json`
- Tactical analytics datasets:
  - `data/processed/api_football/starting_formations.json`
  - `data/processed/api_football/formation_usage_full.json`
  - `data/processed/api_football/formation_matchup_summary.json`

## Planned Direction
The architecture is **DB-first** with controlled, API-second ingestion to respect API request limits and enable efficient reuse in analytics and dashboarding.


# Project Overview

## Goal
Evolve the Premier League analytics project from a static, CSV-based dashboard into a maintainable, database-backed analytics system powered by API-Football.

## Current State
The repo currently contains:
- A legacy interactive HTML dashboard (`SarangAnilkumar_34662774_Code.html`) that was built around CSV-derived data.
- A new Python ingestion foundation that fetches Premier League fixture data from API-Football, persists the raw payload, and produces a cleaned/normalized fixtures dataset for downstream analytics/ML/frontend use.

## What’s Implemented (as of now)
- API-Football HTTP client (requests-based) with retries and timeouts
- Fixture ingestion script that:
  - fetches fixtures for a given league + season
  - saves raw JSON for inspection
  - transforms fixtures into a cleaned schema and saves processed JSON
- Type-safe, modular transformation layer for fixtures

## Output Artifacts
- Raw API response:
  - `data/raw/api_football/fixtures_league_<league_id>_season_<season>.json`
- Cleaned fixtures dataset:
  - `data/processed/api_football/fixtures_cleaned.json`

## Planned Direction
The long-term architecture is intended to become **DB-first** with controlled, API-second ingestion to respect API request limits and enable efficient reuse in analytics and the frontend.


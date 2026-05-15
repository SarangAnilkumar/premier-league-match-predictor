"""Canonical filesystem paths for data artifacts."""
from __future__ import annotations

from pathlib import Path

PROJECT_DATA = Path("data")
RAW_API_FOOTBALL = PROJECT_DATA / "raw" / "api_football"
PROCESSED_API_FOOTBALL = PROJECT_DATA / "processed" / "api_football"
FORMATION_READ_MODELS = PROJECT_DATA / "processed" / "read_models" / "formations"
EXPORTS_DIR = PROJECT_DATA / "exports"

DEFAULT_DB_PATH = PROJECT_DATA / "premier_league.db"
TRANSFERS_EXPORT_CSV = EXPORTS_DIR / "transfers_flat.csv"

FIXTURES_CLEANED_JSON = PROCESSED_API_FOOTBALL / "fixtures_normalized.json"

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pl_ingestion.analytics.formation_aggregator import (  # noqa: E402
    build_fixture_formations_primary,
    build_formation_usage_primary,
    build_starting_formations,
    build_formation_usage_full,
    build_formation_matchups,
    build_formation_matchup_summary,
)
from pl_ingestion.database.connection import create_db_engine, make_session_factory, session_scope  # noqa: E402
from pl_ingestion.database.db_config import DatabaseSettings  # noqa: E402
from pl_ingestion.database.schema import create_schema  # noqa: E402
from pl_ingestion.config import Settings  # noqa: E402


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _write_json(path: Path, data: list[dict[str, Any]] | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

    # Reuse the same LOG_LEVEL as ingestion.
    settings = Settings.from_env()
    setup_logging(settings.log_level)

    db_settings = DatabaseSettings.from_env()
    engine = create_db_engine(db_settings)
    # Ensure tables exist; does not call external APIs.
    create_schema(engine)
    session_factory = make_session_factory(engine)

    with session_scope(session_factory) as session:
        fixture_formations_primary = build_fixture_formations_primary(session)
        formation_usage_primary = build_formation_usage_primary(session)
        starting_formations = build_starting_formations(session)
        formation_usage_full = build_formation_usage_full(session)
        formation_matchups = build_formation_matchups(session)
        formation_matchup_summary = build_formation_matchup_summary(session)

    out_fixture_formations_primary = Path("data/processed/api_football/fixture_formations_primary.json")
    out_fixture_formations = Path("data/processed/api_football/fixture_formations.json")

    out_usage_primary = Path("data/processed/api_football/formation_usage_primary.json")
    out_usage_summary = Path("data/processed/api_football/formation_usage_summary.json")

    out_starting_formations = Path("data/processed/api_football/starting_formations.json")
    out_usage_full = Path("data/processed/api_football/formation_usage_full.json")
    out_matchups = Path("data/processed/api_football/formation_matchups.json")
    out_matchup_summary = Path("data/processed/api_football/formation_matchup_summary.json")

    # Primary (collapsed) datasets retained for compatibility/legacy visuals.
    _write_json(out_fixture_formations_primary, fixture_formations_primary)
    _write_json(out_fixture_formations, fixture_formations_primary)

    _write_json(out_usage_primary, formation_usage_primary)
    # Legacy filename alias.
    _write_json(out_usage_summary, formation_usage_primary)

    # New multi-formation datasets (no single-formation collapse).
    _write_json(out_starting_formations, starting_formations)
    _write_json(out_usage_full, formation_usage_full)
    _write_json(out_matchups, formation_matchups)
    _write_json(out_matchup_summary, formation_matchup_summary)

    logging.getLogger(__name__).info(
        "Formation analytics built: fixture_formations_primary=%s starting_formations=%s formation_usage_primary=%s formation_usage_full=%s formation_matchups=%s formation_matchup_summary=%s",
        len(fixture_formations_primary),
        len(starting_formations),
        len(formation_usage_primary),
        len(formation_usage_full),
        len(formation_matchups),
        len(formation_matchup_summary),
    )


if __name__ == "__main__":
    main()


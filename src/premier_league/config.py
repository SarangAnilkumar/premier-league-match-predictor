from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    """
    Ingestion configuration loaded from environment variables.
    Keep this module focused on configuration only.
    """

    api_football_base_url: str
    api_football_league_id: int
    api_football_season: str
    request_timeout_seconds: float
    api_football_api_key: str
    log_level: str

    @staticmethod
    def from_env() -> "Settings":
        base_url = _get_env("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
        league_id = int(_get_env("API_FOOTBALL_LEAGUE_ID", "39"))
        season = _get_env("API_FOOTBALL_SEASON", "2024")
        timeout_seconds = float(_get_env("API_FOOTBALL_TIMEOUT_SECONDS", "30"))
        api_key = _get_env("API_FOOTBALL_API_KEY", None)
        log_level = os.getenv("LOG_LEVEL", "INFO")

        return Settings(
            api_football_base_url=base_url.rstrip("/"),
            api_football_league_id=league_id,
            api_football_season=season,
            request_timeout_seconds=timeout_seconds,
            api_football_api_key=api_key,
            log_level=log_level,
        )


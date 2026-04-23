from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class APIFootballRateLimitError(RuntimeError):
    """
    Raised when the API returns a payload-level rate limit error (HTTP may still be 2xx).
    Carries the raw JSON payload for debugging.
    """

    def __init__(self, *, message: str, payload: Dict[str, Any]) -> None:
        super().__init__(message)
        self.payload = payload


def _extract_rate_limit_error(payload: Dict[str, Any]) -> Optional[str]:
    errors = payload.get("errors")
    if not isinstance(errors, dict):
        return None
    rate_limit = errors.get("rateLimit")
    if rate_limit:
        return str(rate_limit)
    return None


@dataclass(frozen=True)
class FixturesQuery:
    league_id: int
    season: str
    status: Optional[str] = None

    def to_params(self) -> Dict[str, str | int]:
        params: Dict[str, str | int] = {"league": self.league_id, "season": self.season}
        if self.status:
            params["status"] = self.status
        return params


@dataclass(frozen=True)
class FixtureLineupsQuery:
    fixture_id: int
    team_id: Optional[int] = None

    def to_params(self) -> Dict[str, str | int]:
        params: Dict[str, str | int] = {"fixture": self.fixture_id}
        if self.team_id:
            params["team"] = self.team_id
        return params


@dataclass(frozen=True)
class TransfersQuery:
    team_id: int

    def to_params(self) -> Dict[str, str | int]:
        return {"team": self.team_id}


class APIFootballClient:
    """
    Minimal API-Football HTTP client (requests-based), with retries and
    production-minded timeouts.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        session: Optional[requests.Session] = None,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

        self.session = session or requests.Session()
        self.session.headers.update(
            {
                # API-Football v3 direct authentication header
                "x-apisports-key": api_key,
                "Accept": "application/json",
            }
        )

        # Retry transient failures (rate limiting and 5xx).
        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            status=max_retries,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            # Retry on retryable POST/PUT isn't needed (we use GET only).
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.debug(
            "APIFootballClient initialized base_url=%s timeout_seconds=%s",
            self.base_url,
            self.timeout_seconds,
        )

    def get_fixtures(self, query: FixturesQuery) -> Dict[str, Any]:
        """
        Fetch fixtures for league+season (optionally filtered by status).
        Endpoint: GET /fixtures
        """
        url = f"{self.base_url}/fixtures"
        params = query.to_params()
        logger.info("Fetching fixtures url=%s params=%s", url, params)

        resp = self.session.get(url, params=params, timeout=self.timeout_seconds)
        # Raise with context if still failing after retries.
        resp.raise_for_status()

        data: Dict[str, Any] = resp.json()
        return data

    def get_fixture_lineups(self, query: FixtureLineupsQuery) -> Dict[str, Any]:
        """
        Fetch fixture lineups for a given fixture id.
        Endpoint: GET /fixtures/lineups
        """
        url = f"{self.base_url}/fixtures/lineups"
        params = query.to_params()
        logger.info("Fetching fixture lineups url=%s params=%s", url, params)

        resp = self.session.get(url, params=params, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()

        rate_limit_message = _extract_rate_limit_error(data)
        if rate_limit_message:
            raise APIFootballRateLimitError(
                message=rate_limit_message,
                payload=data,
            )

        return data

    def get_transfers(self, query: TransfersQuery) -> Dict[str, Any]:
        """
        Fetch player transfers for a team.
        Endpoint: GET /transfers
        """
        url = f"{self.base_url}/transfers"
        params = query.to_params()
        logger.info("Fetching transfers url=%s params=%s", url, params)

        resp = self.session.get(url, params=params, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()

        rate_limit_message = _extract_rate_limit_error(data)
        if rate_limit_message:
            raise APIFootballRateLimitError(
                message=rate_limit_message,
                payload=data,
            )

        return data


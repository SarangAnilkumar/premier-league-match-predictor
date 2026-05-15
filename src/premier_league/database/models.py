from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


class IngestionRun(Base):
    """
    Cache/ingestion tracking table.
    """

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Example: "api_football"
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Example: "fixtures"
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False)

    league_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    season: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # A deterministic key for idempotent upserts of ingestion runs.
    # For example: api_football:fixtures:league_id=39:season=2024:status=FT-AET-PEN
    run_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)

    # A higher-level label for the kind of ingestion (e.g., "fixtures").
    run_type: Mapped[str] = mapped_column(String(64), nullable=False, default="fixtures")

    # Cache-first ingestion flags.
    # - fetched_from_api: 1 when we called the external provider for this run.
    # - cache_hit: 1 when we skipped the external provider and used cached DB data.
    fetched_from_api: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cache_hit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # How many records were written/upserted during this run (best-effort).
    records_written: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Where the raw payload was written on disk.
    raw_payload_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    ingested_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    last_refreshed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Team(Base):
    """
    Reference/master table for teams.
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    source_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    last_refreshed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    raw_payload_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Player(Base):
    """
    Reference/master table for players.
    """

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    short_position: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    source_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    last_refreshed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    raw_payload_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Fixture(Base):
    """
    Event table for match fixtures/results.
    """

    __tablename__ = "fixtures"

    fixture_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    season: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    league_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    league_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    round: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    date_utc: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    timestamp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    referee: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    status_long: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status_short: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    elapsed_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    venue_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    venue_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    venue_city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    home_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    away_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)

    home_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Stored as integer (0/1) in SQLite; NULL when unknown.
    home_team_winner: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_team_winner: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    home_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    halftime_home_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    halftime_away_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fulltime_home_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fulltime_away_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extratime_home_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extratime_away_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    penalty_home_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    penalty_away_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    match_result: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    source_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    last_refreshed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    raw_payload_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    home_team: Mapped[Optional[Team]] = relationship("Team", foreign_keys=[home_team_id])
    away_team: Mapped[Optional[Team]] = relationship("Team", foreign_keys=[away_team_id])


Index("ix_fixtures_league_season", Fixture.league_id, Fixture.season)


class FixtureLineup(Base):
    """
    Event table: players appearing in a fixture.
    """

    __tablename__ = "fixture_lineups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.fixture_id"), nullable=False)
    player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)

    team_side: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # e.g. "home"/"away"
    player_position: Mapped[Optional[str]] = mapped_column("position", String(64), nullable=True)
    player_number: Mapped[Optional[int]] = mapped_column("shirt_number", Integer, nullable=True)

    formation: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    grid: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lineup_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    source_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    last_refreshed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    raw_payload_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("fixture_id", "player_id", "team_id", name="uq_fixture_player_team"),
    )


Index("ix_fixture_lineups_fixture", FixtureLineup.fixture_id)


class Transfer(Base):
    """
    Event table: transfers between teams for a player.
    """

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    season: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    transfer_period: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # e.g. "Summer", "Winter"
    transfer_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # ISO date string (YYYY-MM-DD)

    player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)

    from_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    to_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)

    player_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    in_out: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # "In"/"Out" when using provider semantics

    fee_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # store numeric amount (e.g. euros) when known
    source_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    ingested_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    last_refreshed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    raw_payload_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


Index("ix_transfers_season_period", Transfer.season, Transfer.transfer_period)
Index("ix_transfers_player", Transfer.player_id)


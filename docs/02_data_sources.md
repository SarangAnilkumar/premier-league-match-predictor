# Data Sources

## API Provider
API-Football (api-football.com) via the v3 endpoint:
`https://v3.football.api-sports.io`

## Current Endpoint Used
### Fixtures
- Endpoint: `GET /fixtures`
- Query parameters (current ingestion):
  - `league` (Premier League league id)
  - `season` (season year used by the API)
  - optional `status` (fixture status filter)

## Auth
- API key is read from environment variable `API_FOOTBALL_API_KEY`
- Sent as request header:
  - `x-apisports-key: <API_FOOTBALL_API_KEY>`

## Output Schema (Cleaned)
The cleaned dataset stored at:
- `data/processed/api_football/fixtures_cleaned.json`

is a list of dicts, one per fixture, with the following normalized fields:
- fixture_id
- referee
- timezone
- date_utc
- timestamp
- season
- league_id
- league_name
- round
- venue_id
- venue_name
- venue_city
- status_long
- status_short
- elapsed_minutes
- home_team_id
- home_team_name
- away_team_id
- away_team_name
- home_team_winner
- away_team_winner
- home_goals
- away_goals
- halftime_home_goals
- halftime_away_goals
- fulltime_home_goals
- fulltime_away_goals
- extratime_home_goals
- extratime_away_goals
- penalty_home_goals
- penalty_away_goals
- match_result (derived)

## How `match_result` is derived
Based on `home_goals` and `away_goals` extracted from the API payload:
- `home_win` if `home_goals > away_goals`
- `away_win` if `away_goals > home_goals`
- `draw` if equal
- if either is null, `match_result` is set to `null`


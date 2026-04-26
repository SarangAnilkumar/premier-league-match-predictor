# DS-ARCHITECTURE

## Data Source Selection

**Chosen source**: local project CSV `data/processed/tableau_transfers_flat.csv`  
**Why this source**: It is your real project output (not demo scaffold data), already modeled for Tableau, and includes cleaned transfer semantics (`transfer_type`, `movement_direction`) and date fields.

## Source Inventory

### Primary source
- **File**: `data/processed/tableau_transfers_flat.csv`
- **Grain**: one row per transfer event record
- **Row count**: 1,853
- **Season coverage**:
  - 2023: 808 rows
  - 2024: 1,045 rows
- **Date range**: `2023-07-01` to `2025-06-30`

## Schema and Field Dictionary

| Field | Type | Role | Description |
|---|---|---|---|
| `season` | string | Dimension | Season key (`2023`, `2024`) |
| `transfer_period` | string | Dimension | Window segment (`Summer`, `Winter`) |
| `transfer_date` | date string | Dimension | Exact transfer date (`YYYY-MM-DD`) |
| `transfer_month` | string | Time dimension | Month bucket (`YYYY-MM`) |
| `transfer_week` | string | Time dimension | Week bucket (`YYYY-Www`) |
| `transfer_day_of_week` | string | Time dimension | Day name (`Monday`...`Sunday`) |
| `player_id` | integer-like string | Dimension | Player identifier |
| `player_name` | string | Dimension | Player display name |
| `from_team_id` | integer-like string | Dimension | Origin team identifier |
| `from_team_name` | string | Dimension | Origin team display name |
| `to_team_id` | integer-like string | Dimension | Destination team identifier |
| `to_team_name` | string | Dimension | Destination team display name |
| `transfer_type` | string | Dimension | Normalized transfer class (`Loan`, `Transfer`, `Free`, `Return from loan`, `Unknown`) |
| `movement_direction` | string | Dimension | PL flow class (`Incoming to PL`, `Outgoing from PL`, `Internal PL`) |
| `fee_amount_numeric` | numeric | Measure | Transfer fee numeric value (EUR), null when unknown |
| `fee_amount` | string | Label | Human-readable fee (`€ 16.5M`, `€ 250K`) |

## Data Quality Summary

### Completeness
- `transfer_date`: 0 nulls
- `transfer_type`: 0 nulls (normalized)
- `movement_direction`: 0 nulls (normalized)
- `fee_amount_numeric`: 1,543 nulls (expected due to unknown/unreported fees)
- `from_team_*`: 29 nulls
- `to_team_*`: 16 nulls

### Category distributions
- `transfer_period`: Summer 1,336, Winter 517
- `transfer_type`: Loan 592, Unknown 459, Transfer 414, Free 195, Return from loan 193
- `movement_direction`: Outgoing from PL 909, Incoming to PL 797, Internal PL 147

### Coverage note
Fee-driven visuals should explicitly state "known fees only" where applicable.

## Recommended Tableau Data Types

- Date: `transfer_date`
- String dimensions: `season`, `transfer_period`, `transfer_month`, `transfer_week`, `transfer_day_of_week`, `player_name`, `from_team_name`, `to_team_name`, `transfer_type`, `movement_direction`
- Number (whole): `player_id`, `from_team_id`, `to_team_id`, `fee_amount_numeric`

## Core Business Entities

- **Player**: `player_id`, `player_name`
- **Club movement**: `from_team_*`, `to_team_*`, `movement_direction`
- **Transfer event**: `transfer_date`, `transfer_period`, `transfer_type`, `fee_amount_numeric`
- **Seasonal context**: `season`

## KPI-Ready Metrics (for planning step)

- `Transfer Count` = `COUNT(*)`
- `Known Fee Transfer Count` = `COUNT(IF NOT ISNULL([fee_amount_numeric]) THEN 1 END)`
- `Total Known Fees` = `SUM([fee_amount_numeric])`
- `Avg Known Fee` = `AVG([fee_amount_numeric])` (filter non-null)
- `Incoming Count` = `COUNT(IF [movement_direction]='Incoming to PL' THEN 1 END)`
- `Outgoing Count` = `COUNT(IF [movement_direction]='Outgoing from PL' THEN 1 END)`
- `Internal PL Count` = `COUNT(IF [movement_direction]='Internal PL' THEN 1 END)`

## Suggested Calculated Fields (for dashboard build)

- **Club (PL Perspective)**
  - If incoming/internal -> `to_team_name`
  - If outgoing -> `from_team_name`
- **Incoming Fee**
  - Known fee for incoming/internal rows, else 0
- **Outgoing Fee**
  - Known fee for outgoing/internal rows, else 0
- **Net Spend**
  - `SUM([Incoming Fee]) - SUM([Outgoing Fee])`

## Constraints and Interpretation Notes

- Transfer dataset represents events associated with PL clubs, including external club counterparts.
- Not all transfer fees are disclosed; fee metrics are partial and should be labeled as known-fee analytics.
- Movement direction is already normalized and should be preferred over deriving direction in Tableau.

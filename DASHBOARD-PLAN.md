# DASHBOARD-PLAN

## Dashboard Identity

- **Dashboard name**: Premier League Transfer Market Intelligence
- **Audience**: recruiters, hiring managers, football analytics reviewers, and portfolio visitors
- **Primary goal**: explain how PL transfer activity changes by season, window timing, movement direction, transfer type, and known-fee spend

## Data Source Mapping

- **Primary source**: `data/processed/tableau_transfers_flat.csv`
- **Grain**: transfer event row
- **Core dimensions**: `season`, `transfer_period`, `transfer_date`, `transfer_type`, `movement_direction`, `from_team_name`, `to_team_name`, `player_name`
- **Core measures**: `fee_amount_numeric`, `Transfer Count`

## Stable IDs

### KPIs
- `KPI_01_TOTAL_TRANSFERS`
- `KPI_02_KNOWN_FEE_TRANSFERS`
- `KPI_03_TOTAL_KNOWN_FEES`
- `KPI_04_INTERNAL_PL_SHARE`

### Charts
- `CH_01_TRANSFER_TIMELINE`
- `CH_02_NET_SPEND_BY_CLUB`
- `CH_03_TRANSFER_TYPE_MIX`
- `CH_04_DIRECTION_BREAKDOWN`
- `CH_05_TOP_DEALS_TABLE`
- `CH_06_CLUB_ACTIVITY_BALANCE`

### Filters
- `FLT_01_SEASON`
- `FLT_02_TRANSFER_PERIOD`
- `FLT_03_MOVEMENT_DIRECTION`
- `FLT_04_TRANSFER_TYPE`
- `FLT_05_CLUB`
- `FLT_06_DATE_RANGE`

### Actions
- `ACT_01_TIMELINE_TO_TABLE`
- `ACT_02_CLUB_CROSS_FILTER`
- `ACT_03_TYPE_CROSS_FILTER`

## KPI Definitions

### `KPI_01_TOTAL_TRANSFERS`
- **Definition**: `COUNT(*)`
- **Purpose**: high-level market volume signal

### `KPI_02_KNOWN_FEE_TRANSFERS`
- **Definition**: count where `fee_amount_numeric` is not null
- **Purpose**: transparency indicator for fee-based analysis

### `KPI_03_TOTAL_KNOWN_FEES`
- **Definition**: `SUM(fee_amount_numeric)` with nulls excluded
- **Purpose**: known-spend market size
- **Display**: compact currency (EUR millions/billions formatting in Tableau)

### `KPI_04_INTERNAL_PL_SHARE`
- **Definition**: `COUNT(movement_direction='Internal PL') / COUNT(*)`
- **Purpose**: league internal recycling share

## Worksheet Specifications

### `CH_01_TRANSFER_TIMELINE` (Line chart)
- **Question answered**: when does transfer activity spike?
- **X**: `transfer_date` (continuous day)
- **Y**: transfer count
- **Color**: `movement_direction`
- **Tooltip**: date, count, direction split
- **Interactions**: drives table filter (`ACT_01_TIMELINE_TO_TABLE`)

### `CH_02_NET_SPEND_BY_CLUB` (Horizontal bar, diverging)
- **Question answered**: which clubs are net spenders vs net sellers?
- **Dimension**: `Club (PL Perspective)` calc
- **Measure**: `Net Spend = SUM(Incoming Fee) - SUM(Outgoing Fee)`
- **Sort**: descending net spend
- **Color**: diverging red/blue around zero
- **Note**: label as "Known fees only"

### `CH_03_TRANSFER_TYPE_MIX` (100% stacked bar)
- **Question answered**: how do clubs structure transfer strategy?
- **Dimension**: `Club (PL Perspective)`
- **Stack**: `transfer_type`
- **Measure**: transfer count (% of club total)
- **Interaction**: click type filters other charts (`ACT_03_TYPE_CROSS_FILTER`)

### `CH_04_DIRECTION_BREAKDOWN` (Donut or bar)
- **Question answered**: how much is incoming/outgoing/internal?
- **Dimension**: `movement_direction`
- **Measure**: transfer count (optionally known fees as secondary label)

### `CH_05_TOP_DEALS_TABLE` (Text table)
- **Question answered**: what are the biggest disclosed deals?
- **Rows**: `player_name`, `from_team_name`, `to_team_name`
- **Columns**: `transfer_date`, `season`, `transfer_period`, `fee_amount`
- **Filter**: `fee_amount_numeric` not null
- **Sort**: `fee_amount_numeric` descending
- **Limit**: Top N parameter (default 20)

### `CH_06_CLUB_ACTIVITY_BALANCE` (Bubble scatter)
- **Question answered**: which clubs are net-active buyers/sellers by volume?
- **X**: outgoing transfer count (club perspective)
- **Y**: incoming transfer count (club perspective)
- **Bubble size**: known fee volume (`SUM(fee_amount_numeric)`)
- **Detail**: club name (`Club (PL Perspective)`)

## Calculated Fields Required

1. **`CF_01_TRANSFER_COUNT`**
   - `1` (for SUM-based counting)
2. **`CF_02_KNOWN_FEE_FLAG`**
   - `IF NOT ISNULL([fee_amount_numeric]) THEN 1 ELSE 0 END`
3. **`CF_03_CLUB_PL_PERSPECTIVE`**
   - Incoming/Internal -> `[to_team_name]`, Outgoing -> `[from_team_name]`
4. **`CF_04_INCOMING_FEE`**
   - Fee for incoming/internal else 0
5. **`CF_05_OUTGOING_FEE`**
   - Fee for outgoing/internal else 0
6. **`CF_06_NET_SPEND`**
   - `SUM([CF_04_INCOMING_FEE]) - SUM([CF_05_OUTGOING_FEE])`
7. **`CF_07_INTERNAL_PL_SHARE`**
   - `SUM(IF [movement_direction]='Internal PL' THEN 1 ELSE 0 END) / SUM([CF_01_TRANSFER_COUNT])`
8. **`CF_08_INCOMING_COUNT`**
   - `SUM(IF [movement_direction] IN ('Incoming to PL','Internal PL') THEN 1 ELSE 0 END)`
9. **`CF_09_OUTGOING_COUNT`**
   - `SUM(IF [movement_direction] IN ('Outgoing from PL','Internal PL') THEN 1 ELSE 0 END)`
10. **`CF_10_KNOWN_FEE_SUM`**
   - `SUM(ZN([fee_amount_numeric]))`

## Filter Strategy

- Global filters at top:
  - `FLT_01_SEASON` (multi-select, default all)
  - `FLT_02_TRANSFER_PERIOD` (Summer/Winter)
  - `FLT_03_MOVEMENT_DIRECTION`
  - `FLT_04_TRANSFER_TYPE`
  - `FLT_06_DATE_RANGE`
- Context behavior:
  - `season` and `transfer_period` as context filters for performance

## Dashboard Actions

- `ACT_01_TIMELINE_TO_TABLE`:
  - selecting a time range filters top deals and club views
- `ACT_02_CLUB_CROSS_FILTER`:
  - selecting club in net spend filters timeline and deals table
- `ACT_03_TYPE_CROSS_FILTER`:
  - selecting transfer type filters all distribution views

## Layout Plan (matches design tokens)

- Header: title + subtitle + last refresh text
- Row 1: 4 KPI cards
- Row 2: `CH_01_TRANSFER_TIMELINE` (left, wide) + `CH_04_DIRECTION_BREAKDOWN` (right)
- Row 3: `CH_02_NET_SPEND_BY_CLUB` (left) + `CH_03_TRANSFER_TYPE_MIX` (right)
- Row 4: `CH_05_TOP_DEALS_TABLE` full width
- Optional row 5: `CH_06_CLUB_ACTIVITY_BALANCE`

## Narrative Guidance (for portfolio value)

- Title subtitle should explicitly mention:
  - "Known-fee analytics"
  - "Internal vs external PL movement"
- Add callouts:
  - largest net spender
  - largest net seller
  - peak transfer activity date

## Acceptance Criteria (Step B approval)

Dashboard plan is ready for Step C when:

1. KPI definitions are accepted.
2. Chart lineup and ordering are accepted.
3. Global filters match expected exploration flow.
4. "Known fee only" caveat is accepted for spend visuals.
5. Layout structure is approved for a 1100px+ wide viewport.

# Tableau Implementation: Premier League Transfer Market Intelligence

**Template**: Layout A (KPI row + 2x2 chart grid + full-width table + optional secondary chart)  
**Datasources**: `data/processed/tableau_transfers_flat.csv`  
**Mock version**: `v_1`  
**Derived from**: approved `design-tokens.md`, approved `DS-ARCHITECTURE.md`, updated `DASHBOARD-PLAN.md`, `mock-version/v_1/mock.html`

---

## Section 1: Container Hierarchy

### Container Tree

```text
Root Container (layout-basic)
└── Content Wrapper (Vertical, flex)
    ├── Top Banner (Horizontal, fixed-height: 52)
    │   ├── Brand Text / Logo Placeholder (Text/Image, fixed-width: 195, padding: 4)
    │   ├── Spacer (Blank, flex)
    │   └── Update Timestamp (Text/Sheet, fixed-width: 320, inner-padding: 8)
    ├── Dashboard Title (Text, fixed-height: 70)
    │   └── "Premier League Transfer Market Intelligence" + subtitle
    ├── Filter Bar (Horizontal, fixed-height: 53, margin-top: 11, margin-bottom: 11)
    │   ├── "Filters" Label (Text, fixed-width: 90)
    │   ├── FLT_01_SEASON (Filter card/dropdown)
    │   ├── FLT_02_TRANSFER_PERIOD (Filter card/dropdown)
    │   ├── FLT_03_MOVEMENT_DIRECTION (Filter card/dropdown)
    │   ├── FLT_04_TRANSFER_TYPE (Filter card/dropdown)
    │   └── Spacer (Blank, flex)
    ├── KPI Row (Horizontal, fixed-height: 94, distribute-evenly)
    │   ├── KPI_01_TOTAL_TRANSFERS card (Vertical)
    │   ├── KPI_02_KNOWN_FEE_TRANSFERS card (Vertical)
    │   ├── KPI_03_TOTAL_KNOWN_FEES card (Vertical)
    │   └── KPI_04_INTERNAL_PL_SHARE card (Vertical)
    ├── Chart Row 1 (Horizontal, fixed-height: 260)
    │   ├── CH_01_TRANSFER_TIMELINE card (70% width)
    │   └── CH_04_DIRECTION_BREAKDOWN card (30% width)
    ├── Chart Row 2 (Horizontal, fixed-height: 260)
    │   ├── CH_02_NET_SPEND_BY_CLUB card (50% width)
    │   └── CH_03_TRANSFER_TYPE_MIX card (50% width)
    ├── Chart Row 3 (Horizontal, fixed-height: 280)
    │   ├── CH_05_TOP_DEALS_TABLE card (50% width)
    │   └── CH_06_CLUB_ACTIVITY_BALANCE card (50% width)
    └── Footnote (Text, fixed-height: 28)
```

### Container Rules

- Every horizontal/vertical flow includes at least one `Spacer (Blank, flex)`.
- All sheet zones use `inner-padding: 8`.
- Fixed-size structural elements: title bars, filter bar, KPI row, chart headers, separator bars.
- No rounded corners and no shadows.
- Borders: none.

### Container Details

| Container Name | Type | Direction | Size | Background | Padding | Margin |
|---|---|---|---|---|---|---|
| Root | layout-basic | n/a | min 1100x800 | `#F6F7F9` | 0 | 0 |
| Content Wrapper | layout-flow | V | flex | `#F6F7F9` | 4 | 4 |
| Top Banner | layout-flow | H | fixed 52h | `#F6F7F9` | 4 | 4 |
| Filter Bar | layout-flow | H | fixed 53h | `#FFFFFF` | 4 | 11 top/bottom |
| KPI Row | layout-flow | H | fixed 94h | transparent | 0 | 4 |
| Chart Cards | layout-flow | V | fixed row heights | `#FFFFFF` | 8 | row top 11 |

---

## Section 2: Sheets

### Sheet: KPI Total Transfers
**Sheet ID**: `KPI_01_TOTAL_TRANSFERS`  
**Container**: KPI row card 1  
**Size**: flex  
**Title**: hidden

#### Marks
- **Mark type**: Text
- **Columns shelf**: none
- **Rows shelf**: none
- **Label**: `SUM([CF_01_TRANSFER_COUNT])`
- **Tooltip**: `Total transfers: <SUM(CF_01_TRANSFER_COUNT)>`

#### Calculated Fields

| Field Name | Formula | Purpose |
|---|---|---|
| `CF_01_TRANSFER_COUNT` | `1` | Row-level transfer counter |

#### Filters
| Filter | Type | Values | Scope |
|---|---|---|---|
| `season` | Dimension | selected | All using data source |
| `transfer_period` | Dimension | selected | All using data source |
| `movement_direction` | Dimension | selected | All using data source |
| `transfer_type` | Dimension | selected | All using data source |
| `transfer_date` | Date | selected range | All using data source |

#### Formatting
- Font 24 bold, `#1C2833`
- Number format `#,##0`

---

### Sheet: KPI Known Fee Transfers
**Sheet ID**: `KPI_02_KNOWN_FEE_TRANSFERS`  
**Container**: KPI row card 2  
**Size**: flex  
**Title**: hidden

#### Marks
- **Mark type**: Text
- **Label**: `SUM([CF_02_KNOWN_FEE_FLAG])`

#### Calculated Fields
| Field Name | Formula | Purpose |
|---|---|---|
| `CF_02_KNOWN_FEE_FLAG` | `IF NOT ISNULL([fee_amount_numeric]) THEN 1 ELSE 0 END` | Count rows with known fee |

#### Filters
Same global filters as KPI 1.

#### Formatting
- Font 24 bold, `#1C2833`
- Number format `#,##0`

---

### Sheet: KPI Total Known Fees
**Sheet ID**: `KPI_03_TOTAL_KNOWN_FEES`  
**Container**: KPI row card 3  
**Size**: flex  
**Title**: hidden

#### Marks
- **Mark type**: Text
- **Label**: `SUM([fee_amount_numeric])`

#### Calculated Fields
No additional calculated field required.

#### Filters
Same global filters as KPI 1.

#### Formatting
- Font 24 bold, `#1C2833`
- Number format custom: `€#,##0,,"M"` for millions (or Tableau default compact currency)

---

### Sheet: KPI Internal PL Share
**Sheet ID**: `KPI_04_INTERNAL_PL_SHARE`  
**Container**: KPI row card 4  
**Size**: flex  
**Title**: hidden

#### Marks
- **Mark type**: Text
- **Label**: `CF_07_INTERNAL_PL_SHARE`

#### Calculated Fields
| Field Name | Formula | Purpose |
|---|---|---|
| `CF_07_INTERNAL_PL_SHARE` | `SUM(IF [movement_direction]='Internal PL' THEN 1 ELSE 0 END) / SUM([CF_01_TRANSFER_COUNT])` | Internal share |

#### Filters
Same global filters as KPI 1.

#### Formatting
- Number format percentage `0.0%`

---

### Sheet: Transfer Timeline
**Sheet ID**: `CH_01_TRANSFER_TIMELINE`  
**Container**: Chart Row 1 left  
**Size**: flex  
**Title**: `Transfer Timeline`

#### Marks
- **Mark type**: Line
- **Columns shelf**: `transfer_date` (continuous day)
- **Rows shelf**: `SUM([CF_01_TRANSFER_COUNT])`
- **Color**: `movement_direction`
- **Tooltip**:  
  - `Date: [transfer_date]`  
  - `Direction: [movement_direction]`  
  - `Transfers: <SUM(CF_01_TRANSFER_COUNT)>`

#### Calculated Fields
None (uses `CF_01_TRANSFER_COUNT`).

#### Filters
Global filters + optional `season` context filter.

#### Formatting
- Axis titles visible
- Grid lines subtle
- Series colors: `#4E79A7`, `#F28E2B`, `#76B7B2`

---

### Sheet: Direction Breakdown
**Sheet ID**: `CH_04_DIRECTION_BREAKDOWN`  
**Container**: Chart Row 1 right  
**Size**: flex  
**Title**: `Direction Breakdown`

#### Marks
- **Mark type**: Pie (or donut-style worksheet design)
- **Color**: `movement_direction`
- **Angle**: `SUM([CF_01_TRANSFER_COUNT])`
- **Label**: `movement_direction`, percent of total
- **Tooltip**: direction + count + percent

#### Filters
Global filters.

#### Formatting
- Palette consistent with timeline colors

---

### Sheet: Net Spend by Club
**Sheet ID**: `CH_02_NET_SPEND_BY_CLUB`  
**Container**: Chart Row 2 left  
**Size**: flex  
**Title**: `Net Spend by Club (Known Fees)`

#### Marks
- **Mark type**: Bar (horizontal)
- **Columns shelf**: `SUM([CF_06_NET_SPEND])`
- **Rows shelf**: `[CF_03_CLUB_PL_PERSPECTIVE]`
- **Color**: `SUM([CF_06_NET_SPEND])` diverging around zero
- **Tooltip**: club, net spend, incoming fee sum, outgoing fee sum

#### Calculated Fields
| Field Name | Formula | Purpose |
|---|---|---|
| `CF_03_CLUB_PL_PERSPECTIVE` | `IF [movement_direction]='Incoming to PL' OR [movement_direction]='Internal PL' THEN [to_team_name] ELSE [from_team_name] END` | Club perspective |
| `CF_04_INCOMING_FEE` | `IF [movement_direction]='Incoming to PL' OR [movement_direction]='Internal PL' THEN ZN([fee_amount_numeric]) ELSE 0 END` | Incoming fee |
| `CF_05_OUTGOING_FEE` | `IF [movement_direction]='Outgoing from PL' OR [movement_direction]='Internal PL' THEN ZN([fee_amount_numeric]) ELSE 0 END` | Outgoing fee |
| `CF_06_NET_SPEND` | `SUM([CF_04_INCOMING_FEE]) - SUM([CF_05_OUTGOING_FEE])` | Net spend |

#### Filters
Global filters + keep null club names excluded.

#### Formatting
- Number format: currency compact
- Sort descending by net spend
- Explicit subtitle in dashboard: "Known fees only"

---

### Sheet: Transfer Type Mix
**Sheet ID**: `CH_03_TRANSFER_TYPE_MIX`  
**Container**: Chart Row 2 right  
**Size**: flex  
**Title**: `Transfer Type Mix`

#### Marks
- **Mark type**: Bar
- **Columns shelf**: `[CF_03_CLUB_PL_PERSPECTIVE]`
- **Rows shelf**: `SUM([CF_01_TRANSFER_COUNT])`
- **Color**: `transfer_type`
- **Tooltip**: club, transfer type, count, percent within club

#### Calculated Fields
None beyond shared `CF_03_CLUB_PL_PERSPECTIVE`.

#### Filters
Global filters.

#### Formatting
- Stack bars on
- Add quick table calc `% of total` within club if needed

---

### Sheet: Top Deals Table
**Sheet ID**: `CH_05_TOP_DEALS_TABLE`  
**Container**: Chart Row 3 left  
**Size**: flex  
**Title**: `Top Deals`

#### Marks
- **Mark type**: Text Table
- **Rows shelf**: `player_name`, `from_team_name`, `to_team_name`
- **Text shelf**: `transfer_date`, `season`, `transfer_period`, `fee_amount`
- **Detail**: `player_id`
- **Tooltip**: player + route + numeric fee

#### Calculated Fields
| Field Name | Formula | Purpose |
|---|---|---|
| `CF_11_TOP_DEAL_RANK` | `RANK_DENSE(SUM([fee_amount_numeric]), 'desc')` | Rank rows by known fee |

#### Filters
| Filter | Type | Values | Scope |
|---|---|---|---|
| `fee_amount_numeric` | Measure | non-null | This sheet |
| `CF_11_TOP_DEAL_RANK` | Table calc | `<= [PRM_TOP_N]` | This sheet |

#### Formatting
- Sort descending by fee
- Table font 12, headers bold

---

### Sheet: Club Activity Balance
**Sheet ID**: `CH_06_CLUB_ACTIVITY_BALANCE`  
**Container**: Chart Row 3 right  
**Size**: flex  
**Title**: `Club Activity Balance`

#### Marks
- **Mark type**: Circle (scatter/bubble)
- **Columns shelf**: `CF_09_OUTGOING_COUNT`
- **Rows shelf**: `CF_08_INCOMING_COUNT`
- **Size**: `CF_10_KNOWN_FEE_SUM`
- **Detail**: `CF_03_CLUB_PL_PERSPECTIVE`
- **Tooltip**: club, incoming count, outgoing count, known fee sum

#### Calculated Fields
| Field Name | Formula | Purpose |
|---|---|---|
| `CF_08_INCOMING_COUNT` | `SUM(IF [movement_direction]='Incoming to PL' OR [movement_direction]='Internal PL' THEN 1 ELSE 0 END)` | Incoming count |
| `CF_09_OUTGOING_COUNT` | `SUM(IF [movement_direction]='Outgoing from PL' OR [movement_direction]='Internal PL' THEN 1 ELSE 0 END)` | Outgoing count |
| `CF_10_KNOWN_FEE_SUM` | `SUM(ZN([fee_amount_numeric]))` | Bubble size metric |

#### Filters
Global filters.

#### Formatting
- Axes titles visible
- Circle opacity ~65%
- Color fixed `#4E79A7`

---

## Section 3: Parameters

| Parameter Name | Data Type | Default | Allowable Values | Used In |
|---|---|---|---|---|
| `PRM_TOP_N` | Integer | 20 | Range 5-50 | Top deals table filter (`CF_11_TOP_DEAL_RANK`) |

---

## Dashboard Actions

| Action ID | Action Name | Type | Source Sheet ID | Target Sheet ID(s) | Run On | Fields |
|---|---|---|---|---|---|---|
| `ACT_01_TIMELINE_TO_TABLE` | Timeline Date Filter | Filter | `CH_01_TRANSFER_TIMELINE` | `CH_05_TOP_DEALS_TABLE`, `CH_02_NET_SPEND_BY_CLUB`, `CH_06_CLUB_ACTIVITY_BALANCE` | Select | `transfer_date -> transfer_date` |
| `ACT_02_CLUB_CROSS_FILTER` | Club Focus Filter | Filter | `CH_02_NET_SPEND_BY_CLUB` | `CH_01_TRANSFER_TIMELINE`, `CH_05_TOP_DEALS_TABLE`, `CH_06_CLUB_ACTIVITY_BALANCE` | Select | `CF_03_CLUB_PL_PERSPECTIVE -> CF_03_CLUB_PL_PERSPECTIVE` |
| `ACT_03_TYPE_CROSS_FILTER` | Transfer Type Focus | Filter | `CH_03_TRANSFER_TYPE_MIX` | `CH_01_TRANSFER_TIMELINE`, `CH_04_DIRECTION_BREAKDOWN`, `CH_05_TOP_DEALS_TABLE` | Select | `transfer_type -> transfer_type` |

---

## Cross-Dashboard Navigation (if multi-dashboard)

No multi-dashboard navigation required in v1.

### Shared Worksheets
Not applicable.

---

## Notes

- Tableau cannot render a true donut natively without a dual-axis workaround; pie is acceptable if implementation speed is prioritized.
- `CH_06_CLUB_ACTIVITY_BALANCE` replaces the prior window pace concept from early planning; plan has been synced.
- `fee_amount` is display-ready text; use `fee_amount_numeric` for all math.
- Keep subtitle/caption on spend visuals: "Known fees only."

---

## Approval Checklist
- [x] Every sheet maps back to a stable ID from `DASHBOARD-PLAN.md`
- [x] All calculated fields and filters are explicit enough to implement without guessing
- [x] Container sizes and hierarchy are specific enough to reproduce the approved mock
- [x] Any Tableau-driven deviations from the mock are called out explicitly
- [x] Root-level docs can remain the latest approved global truth after sync

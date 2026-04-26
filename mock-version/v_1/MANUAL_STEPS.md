# Manual Steps After Opening `dashboard.twbx`

This Step E output is an **experimental starter workbook** generated from validated snippets and mapped to your transfer CSV.

Implemented in XML:
- Live CSV datasource (`tableau_transfers_flat.csv`)
- Two starter worksheets:
  - `Transfer Type - Known Fee Sum`
  - `Movement Direction - Known Fee Sum`
- One dashboard (`Transfer Dashboard Starter`) with both starter sheets

## Why manual completion is still needed

Your approved spec includes a richer multi-sheet layout, KPI cards, filters, actions, and calculated fields. Generating that full XML end-to-end without Tableau Desktop refinement is high-risk in one pass.

## Complete in Tableau Desktop (recommended order)

1. Open `mock-version/v_1/dashboard.twbx`
2. Duplicate the starter dashboard to preserve a fallback copy.
3. Create calculated fields from `mock-version/v_1/TABLEAU-IMPLEMENTATION.md`:
   - `CF_01_TRANSFER_COUNT`
   - `CF_02_KNOWN_FEE_FLAG`
   - `CF_03_CLUB_PL_PERSPECTIVE`
   - `CF_04_INCOMING_FEE`
   - `CF_05_OUTGOING_FEE`
   - `CF_06_NET_SPEND`
   - `CF_07_INTERNAL_PL_SHARE`
   - `CF_08_INCOMING_COUNT`
   - `CF_09_OUTGOING_COUNT`
   - `CF_10_KNOWN_FEE_SUM`
4. Build remaining sheets from the implementation spec:
   - `KPI_01_TOTAL_TRANSFERS`
   - `KPI_02_KNOWN_FEE_TRANSFERS`
   - `KPI_03_TOTAL_KNOWN_FEES`
   - `KPI_04_INTERNAL_PL_SHARE`
   - `CH_01_TRANSFER_TIMELINE`
   - `CH_02_NET_SPEND_BY_CLUB`
   - `CH_03_TRANSFER_TYPE_MIX`
   - `CH_04_DIRECTION_BREAKDOWN`
   - `CH_05_TOP_DEALS_TABLE`
   - `CH_06_CLUB_ACTIVITY_BALANCE`
5. Add global filters:
   - `season`, `transfer_period`, `movement_direction`, `transfer_type`, `transfer_date`
6. Wire dashboard actions:
   - timeline -> table/club views
   - club -> timeline/table
   - type -> distribution views
7. Apply styling from `design-tokens.md` (colors, spacing, typography).

## Notes

- Data is packaged inside `.twbx` so no extra connection setup is required.
- Keep `fee_amount_numeric` for calculations and `fee_amount` for display labels.

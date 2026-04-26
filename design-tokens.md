# Design Tokens

**Source**: approved project design token decisions and Tableau defaults  
**Derived for**: Step 0 approval candidate (Premier League Transfers dashboard)

## Typography
- **Font family**: Open Sans
- **Dashboard title**: 36px, Bold, `#1C2833`
- **Chart title**: 15px, Regular, `#1C2833`
- **Filter/section labels**: 12px, Bold, `#5D6D7E`
- **Worksheet default font size**: 12px
- **Tooltip font size**: 12px

## Colors

### Backgrounds
- **Dashboard background**: `#F6F7F9`
- **Top banner / title area**: `#F6F7F9`
- **Chart card background**: `#FFFFFF`
- **Separator line**: `#F0F3F5`

### Accent Colors (KPI top border bars)
- Accent 1: `#4E79A7`
- Accent 2: `#F28E2B`
- Accent 3: `#E15759`
- Accent 4: `#76B7B2`

### Chart Series Colors
`#4E79A7`, `#F28E2B`, `#E15759`, `#76B7B2`, `#59A14F`, `#EDC948`, `#B07AA1`, `#FF9DA7`, `#9C755F`, `#BAB0AC`

### Text
- Dark (titles): `#1C2833`
- Medium (labels): `#5D6D7E`

### Borders
- Default border-style: `none`
- Exceptions: none

## Logo
- **File**: none provided
- **Dimensions**: n/a
- **Placement**: Top-left banner area (optional when logo is later added)

## Dashboard Sizing
- **Sizing mode**: Range
- **Minimum height**: 800
- **Minimum width**: 1100
- **Maximum**: Flexible

## Standard Container Hierarchy
```text
layout-basic (root)
└── Content (vertical)
    ├── Header banner (optional logo + title + update context)
    ├── Filter row (season, period, movement, transfer type)
    ├── KPI row (4 cards)
    ├── Main chart row (2 charts)
    └── Secondary chart row (2 charts / table)
```

## Available Template Layouts
- **Layout A (Recommended)**: KPI row + 2x2 chart grid
- **Layout B**: KPI row + full-width timeline + 2 supporting charts
- **Layout C**: Single-page executive summary with top table

## KPI Card Pattern
```text
KPI container
└── Inner wrapper (bg: #FFFFFF, padding: 8)
    ├── Accent bar (3px)
    ├── KPI value (large text)
    └── KPI subtitle (small text)
```

## Chart Card Pattern
```text
Chart wrapper
└── Chart inner (bg: #FFFFFF, padding: 8)
    ├── Title row
    ├── Separator (3px)
    └── Worksheet area (flex)
```

## Icons
No `branding/icons/` folder provided. Step C should generate simple inline SVG icons matching chart types.

## Fallback Decisions
| Token / Decision | Fallback Value Used | Why It Was Needed |
|------------------|---------------------|-------------------|
| Primary color | `#4E79A7` | No fixed project brand palette was available at token extraction time |
| Secondary color | `#F28E2B` | No fixed project brand palette was available at token extraction time |
| Accent colors 1-4 | Tableau defaults (`#4E79A7`, `#F28E2B`, `#E15759`, `#76B7B2`) | Needed a consistent 4-card accent set |
| Chart series palette | Tableau 10 palette | Needed a stable ordered categorical palette |
| Separator line color | `#F0F3F5` | Needed subtle section separation |
| Top banner/title area color | `#F6F7F9` | Needed contrast against white chart cards |
| Dashboard title size | 36px | Needed readable hierarchy at laptop resolution |
| Chart title size | 15px | Needed readable chart-level labeling |
| Filter label size | 12px | Needed compact but readable controls |
| Tooltip font size | 12px | Needed consistent tooltip readability |
| Border policy | `none` | Preferred clean card style with minimal chrome |
| Container hierarchy | Tableau standard dashboard container flow | Ensured predictable dashboard assembly |
| Logo usage | none | No logo file provided in repository |

## Spacing Reference
| Element | Property | Value |
|---------|----------|-------|
| Card | padding | 8px |
| Section blocks | vertical spacing | 11px |
| Containers | margin | 4px |
| KPI accent bar | height | 3px |
| Chart separator | height | 3px |

## Constraints
- Avoid rounded corners unless explicitly requested.
- Keep chart/card backgrounds white for readability.
- Ensure filter row remains visible at laptop width (1100px min).
- Keep transfer fee labels in compact notation (`€ 16.5M`, `€ 250K`) when shown.

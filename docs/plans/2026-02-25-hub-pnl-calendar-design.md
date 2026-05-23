# Hub P&L Calendar — Design Doc

**Date:** 2026-02-25
**File:** `hub/index.html` (single-file modification)

## Goal
Add a P&L Calendar tab to the Trading Systems Hub that aggregates closed trades from ALL systems into a visual monthly calendar with filtering and automatic version tracking.

## Architecture
- **No new files** — everything added inline to `hub/index.html` (matching existing pattern)
- **No new API calls** — reuses the `closed_picks.json` data already fetched by the Hub
- **Client-side aggregation** — all P&L grouping happens in the browser

## Components

### 1. Tab Bar
```
[ Systems ]  [ P&L Calendar ]
```
- Systems = existing Hub view (default)
- P&L Calendar = new calendar view
- Tabs toggle visibility of `.systems-view` vs `.calendar-view`

### 2. Filter Bar
- **System pills**: All Systems | Mercury 2 | Alpha Engine | KIMI | ... (dynamic from loaded data)
- **Strategy pills**: Multi-select, populated from selected system's strategies
- **Time range**: Last 35 days (default) | This Month | Last 60 days | All Time

### 3. Calendar Grid
- 7-column grid (Sun–Sat) with month labels
- Day cells show: daily P&L %, W/L count
- Color: green (net positive), red (net negative), neutral (no trades)
- Hover tooltip: per-system + per-strategy breakdown for that day

### 4. Summary Cards
Total P&L | Green Days | Red Days | Total Trades | Win Day Rate

### 5. Strategy Breakdown Table
Per-strategy: trades, W/L, WR%, cumulative P&L, symbols

### 6. Version Tracking
- **Primary**: Use `version` field from JSON record if present (Mercury 2 has this)
- **Fallback**: GitHub API commits on scanner `.py` files, filtered to strategy-logic-only changes
- **Display**: Vertical dotted lines on calendar at version boundaries, hover shows commit info
- **Split stats**: Version breakdown table showing WR/P&L before vs after revision

### Scanner files tracked per system
| System | Path |
|--------|------|
| Mercury 2 | `mercury2/scanner.py` |
| Alpha Engine | `alpha_engine/scanner.py` |
| KIMI | `KIMI_RISEOFTHECLAW/live_scanner.py` |

## Data Flow
```
Hub loadAll() → fetches closed_picks.json per system (already done)
  → P&L Calendar aggregates all closed picks by exit_date
  → Groups by date → renders calendar cells
  → GitHub API → fetches commit history on scanner .py files → version epochs
```

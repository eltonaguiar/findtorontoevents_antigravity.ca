# Crypto CSV Export Analysis

- Closed export: `C:\Users\zerou\Downloads\antigravity_closed_picks_2026-03-27 (6).csv`
- Active export: `C:\Users\zerou\Downloads\antigravity_active_picks_2026-03-27 (7).csv`
- Generated: `2026-03-27`

## Coverage

- Closed crypto rows: `1956`
- Active crypto rows: `310`
- `A-viable` tag coverage: `0`
- HTF-specific field coverage: `0` explicit HTF columns in both exports

## Closed Export Findings

- Full closed crypto sample:
  - Win rate: `49.8%`
  - Avg PnL: `+0.09%`
- Score buckets:
  - `<40`: `950` trades, `45.7%` WR, `+0.11%` avg PnL
  - `40-54`: `594` trades, `53.0%` WR, `-0.28%` avg PnL
  - `55-69`: `335` trades, `53.1%` WR, `+0.47%` avg PnL
  - `70+`: `77` trades, `61.0%` WR, `+1.09%` avg PnL
- Forward WR buckets:
  - `<40`: `779` trades, `41.2%` WR, `+0.97%` avg PnL
  - `40-49`: `233` trades, `50.6%` WR, `+0.59%` avg PnL
  - `50-59`: `514` trades, `52.3%` WR, `-1.86%` avg PnL
  - `60+`: `430` trades, `61.9%` WR, `+0.56%` avg PnL

## Recent 3-Day Closed Slice

- Baseline: `1214` trades, `47.0%` WR, `-0.40%` avg PnL
- Direction split:
  - `LONG`: `935` trades, `39.0%` WR, `-0.75%` avg PnL
  - `SHORT`: `279` trades, `73.8%` WR, `+0.78%` avg PnL
- Raw confluence split:
  - `SHORT + confluence >= 5`: `245` trades, `78.8%` WR, `+1.08%` avg PnL
  - `LONG + confluence >= 5`: `739` trades, `40.5%` WR, `-0.89%` avg PnL
- Trust tiers:
  - `PROVEN`: `35` trades, `51.4%` WR, `+0.25%` avg PnL
  - `SANDBOX`: `379` trades, `54.4%` WR, `+0.40%` avg PnL

## Active Export Findings

- Score buckets:
  - `<40`: `244`
  - `40-54`: `19`
  - `55-69`: `28`
  - `70+`: `19`
- Trust tiers:
  - `SANDBOX`: `189`
  - `WATCH`: `72`
  - `PROVEN`: `27`
  - `PROBATION`: `22`
- Direction / live-PnL snapshot:
  - `LONG`: `148` rows, `-1.52%` avg live PnL
  - `SHORT`: `162` rows, `+6.82%` avg live PnL
  - `SHORT + confluence >= 5`: `68` rows, `+4.52%` avg live PnL
  - `LONG + confluence >= 5`: `123` rows, `-1.77%` avg live PnL
- Strict active shortlist using the safer profile (`Trust Tier in {PROVEN, RELIABLE}` + `Score 40-69` + `Confluence Count 1-4`):
  - `TONUSDT` `LONG` via `ml_crypto_pred / enhanced_ml_A_xgboost`
    - Score: `44`
    - Forward WR: `79.4%`
    - Forward Trades: `34`
    - Confluence Count: `4`
    - Trust Tier: `PROVEN`
    - Live PnL snapshot: `+0.58%`

## Score Distortion Flags

- `22` active crypto rows have `Score` at least `25` points above the `Raw weighted total` stated in `Score Breakdown (English)`.
- `6` active crypto rows have score `>= 99` despite `0` forward trades and `0.0%` forward WR:
  - `XRPUSDT` / `pm_kalshi_signals`
  - `BNBUSDT` / `pm_kalshi_signals`
  - `SOLUSDT` / `pm_whale_signals`
  - `BTCUSDT` / `pm_whale_signals`
  - `ETHUSDT` / `pm_whale_signals`
  - `BTCUSDT` / `pm_whale_signals`

## Takeaways

- The CSV exports reinforce that raw `Score` is not safe to trust on its own for active crypto rows.
- The strongest export-level recent edge is `SHORT` plus high raw confluence, but that metric is not deduped by strategy family and is likely overstating independence.
- To make this analysis robust, exports should add:
  - `strategy_tags` / `A-viable`
  - explicit `htf_bias` and `htf_matches_direction`
  - deduped `agreement_count_unique_groups`
  - raw score plus final score plus multiplier/cap fields

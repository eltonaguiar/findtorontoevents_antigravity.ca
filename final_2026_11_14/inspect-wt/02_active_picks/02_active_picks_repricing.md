# Notes — Active Picks repricing methodology & per-field findings

## Method (reproducible)
1. `GET https://findtorontoevents.ca/audit/data/dashboard_payload.json` (16:15:51Z) →
   `.picks.active_raw` = 4,164 rows; open-ish (`status ∈ OPEN|ACTIVE|PENDING|NEW`) = **703**.
2. Price sources:
   - Crypto: `https://api.binance.com/api/v3/ticker/price` (3,745 symbols) — also maps `XXX-USD` → `XXXUSDT`.
   - FX: `https://open.er-api.com/v6/latest/USD` — `XXXYYY=X` resolved by base/cross math
     (e.g. `USDJPY=X` = rates.JPY; `AUDUSD=X` = 1/rates.AUD; `EURGBP=X` = rates.GBP/rates.EUR).
   - Equity/ETF/commodity: Yahoo `v8/finance/chart/{sym}?range=1d` — 90/90 tickers returned.
3. Recomputed P/L: `dir_sign * (mark − entry)/entry * 100`, `dir_sign = −1` for SHORT/SELL.
4. Compared to dashboard `unrealized_pnl_pct` (fallback `pnl_pct`).
5. Script: `.inspect-wt/_audit_tmp/` (repricing.json is the row-level output).

## Coverage
703 open picks → **624 priced** (89%). 79 unpriced = symbols with no mapping (delisted/odd tickers).

## Per-class table
(see AUDIT_FINAL.md §2 for the table; raw counts in `evidence/repricing.json`)

## Field-by-field findings on Active Picks
| Field | Status | Evidence |
|---|---|---|
| `entry_price` | **BROKEN for some rows** | `EURGBP=X` entry 688.17 vs market 0.835 (824x off); `XRPUSDT` entry 0.0 emitted 13:54Z by `prediction_market_consensus` |
| `current_price` | **STALE/None** | OPEN picks from 2026-11-12 still `None` (10 incubator BTCUSDT rows) |
| `unrealized_pnl_pct` | **FROZEN at 0** | 504/624 (81%) show 0/None; real mean −1.80% |
| `pnl_pct` | same problem | same rows |
| `status` | polluted | 78.6% of active_raw are `EXPIRED` (should not be "active") |
| `timestamp`/`entry_date` | plausible | fresh rows 1.5–3.6h; zombies up to 267d old |
| `last_checked` | suspicious | often identical across hundreds of rows (batch stamp, not per-pick check) |
| `asset_class` | split bug | `STOCKS` vs `EQUITY` are separate classes for the same asset |
| `symbol` | polluted | `'MONTREAL CANADIENS VS BUFFALO SABRES'` — a sports fixture used as a trading symbol |
| `direction` | works | LONG/SHORT respected in 624-row recompute (no systematic inversion) |
| forward fields (`forward_wr`,`forward_trades`,`strat_fwd_wr`) | present but often 0/None | cannot be validated without per-pick forward ledger |

## Stale-entry flags
- 3,272 / 4,164 active_raw = `EXPIRED` + pnl 0 (78.6%).
- `inverse_mutations` = 2,262 of those (re-emitting BTCUSDT / XRPUSDT / NEARUSDT daily since 2026-07-13).
- CRYPTO active_raw median age **2,128h (89 days)**, max 6,421h (267 days).
- FUTURES active_raw median **2,344h (98 days)**; BOND newest *closed* pick 98h (4.1 days).

## Caveat
Price cross-reference validates the **mark**, not the system's claimed intrabar fills. A pick could
have hit TP intrabar and the current mark still show a loss — but since the dashboard displays the
current mark as its P/L too, the discrepancy stands either way.

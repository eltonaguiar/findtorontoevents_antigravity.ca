# DB-QUALITY AUDIT — 2026-10-22 (INCEPTION/VLLM)

## Scope

Per user directive: "check the database also for data quality, is our picks per asset class
even being fed in properly, do we have any proven data pipelines, or can we trust our database /
anything performing way too well to be real, and anything that actually feeds in correct where its
performing well and you can cross-check it."

Source: `mysql.50webs.com` → `ejaguiar1_stocks.at_pick_outcomes` (409 tables; outcomes table is
the resolver's write target). Credentials from `../dbpasses.txt`.

## 1. What the DB actually feeds

`at_pick_outcomes` holds **59,276** rows (min resolved_at 2026-02-22, max 2026-10-22T20:08Z).

| asset_class | total | WON | LOST | EXPIRED | FLAT | note |
|---|---|---|---|---|---|---|
| CRYPTO | 33,539 | 11,064 | 12,925 | 8,737 | 813 | dominant |
| FOREX | 15,976 | 1,095 | 1,657 | 13,174 | 50 | 82% expired |
| COMMODITY | 5,882 | 331 | 560 | 4,947 | 44 | 84% expired |
| EQUITY | 2,232 | 218 | 231 | 1,754 | 29 | |
| FUTURES | 446 | 2 | 4 | 420 | 20 | 94% expired |
| INDEX | 314 | 3 | 0 | 311 | 0 | 99% expired |
| ETF | 181 | 4 | 19 | 145 | 13 | |
| BOND | 154 | 4 | 12 | 125 | 13 | |
| '' / UNKNOWN | 345 | 140 | 190 | 0 | 15 | empty/unknown taxonomy |
| MEME/STOCKS/STOCK/PENNY... | 207 | 33 | 68 | 58 | 48 | fragmented labels |

## 2. Data-quality findings (ordering by severity)

1. **Massive time-expiry bias.** FOREX/COMMODITY/FUTURES/INDEX are >80% `TIME_EXPIRED`.
   The DB is not recording TP/SL outcomes for most non-crypto picks — it records "nothing happened,
   we timed out". That depresses win-rate to near-zero signal for those classes and means per-class
   verdicts from the raw table are untrustworthy for non-crypto.

2. **Half of closed outcomes carry zero PnL.** `29,753` closed rows (WON/LOST/EXPIRED/FLAT) have
   `pnl_pct = 0`. A "win" with zero PnL is not a real winner. The mark-to-market estimator returns
   exactly 0 for a large slice — these should be treated as unresolved / not creditable.

3. **No forward validation has ever been stamped.** `forward_validated = 0` for all 59,276 rows;
   `forward_test_only = 0`; `_gated_forward_test_isolated = 0`. So the table contains **no** sealed
   forward cohort — nothing in the DB is pre-registered forward evidence.

4. **Asset-class taxonomy is fragmented** (`''`, `UNKNOWN`, `STOCKS` vs `STOCK`, `PENNY` vs
   `PENNYSTOCK`). Per-class aggregation is unreliable, and a chunk of rows has empty class.

5. **Suspicious "too good to be real" CRYPTO strategies** (all with nonzero PnL, but clustered):
   - Calendar Effect Crypto: 105W / 0L (100%) over only **6 distinct exit dates**
   - HoffmannmanStripTrendStrategy: 146W / 0L over 16 dates
   - BTCSPXCorrBreakdownStrategy: 44W / 0L over 11 dates
   - VerifiedStochRsiStrategy: 116W / 0L over 13 dates
   - ADX Trend Confirmation: 207W / 6L over 17 dates
   - Price Acceleration Detector: 181W / 27L / 87% WR
   100%-WR over 100+ trades with high date-clustering is the same signature as the frozen-exit
   artifact I fixed in P0 (one price snapshot stamped across many picks). These do **not** survive
   the strict walk-forward gate.

## 3. Cross-check: DB "winners" vs strict walk-forward harness

I cross-referenced the high-WR CRYPTO names against `reports/walkforward_strategy_eval_2026-10-22.json`
(chronological 50/50 split, test n≥10, PF≥1.15, WR≥0.50, non-artifact). Every candidate fails:

- `cal-effect-crypto-scout` (Calendar Effect): train n=2 WR=0.0, test None → FAILS
- `adx-trend-scout`: test cells n=1–4 → FAILS n≥10 gate
- `price-accel-scout`: test cells n=1–3 → FAILS
- `rsi-divergence-scout`: test cells n=1–3 → FAILS
- No cell in the harness passes the strict gate; overall winners list is empty.

## 4. Verdict

- **No proven data pipeline / trustable "winner" can be certified from the DB today.** The raw table
  is dominated by time-expired outcomes, zero-PnL rows, and date-clustered 90–100% WR artifacts.
- The "too good" performers are **not real** — they are artifacts (same root cause as the P0
  frozen-exit bug), and they fail the walk-forward gate on direct cross-check.
- The DB's per-asset-class counts are only reliable for CRYPTO at scale; everything else is too thin
  or too fragmented to certify.
- Recommendation: the only honest route to a *proven* winner is a **sealed forward cohort** (P1-3)
  fed by the fixed resolver, not back-fill from this table.

## 5. Items I did NOT touch

Read-only audit. No rows were modified. The resolver dry-run (PICK_OUTCOMES_MYSQL_ENABLED=0) only
regenerates the local resolved JSON in place and does not write to MySQL.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*

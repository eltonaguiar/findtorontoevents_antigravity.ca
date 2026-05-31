# Phase 7 Forensics — 293 NULL `pnl_pct` Rows in `ejaguiar1_stocks.trading_picks`

**Date:** 2026-05-31
**Author:** Claude Opus 4.7 (peer subagent)
**Source:** Live query against `ejaguiar1_stocks.trading_picks` (read-only, no mutations).
**Phase 6 context:** Phase 6 resolver backfilled 347 of 640 NULL-pnl rows; this report
diagnoses the remaining **293** that are still NULL.

---

## TL;DR

The 293 orphan rows are **two distinct populations** with very different root causes:

| Group | Count | Symptom | Root cause | Action |
|---|---|---|---|---|
| **A** | 131 | `pnl_pct=NULL` AND `exit_price=NULL` | Resolver flagged `UNRESOLVABLE_MISSING_PRICE` — could not fetch exit candle | **Re-fetch via Binance/yfinance** (115 rows recoverable, 16 missing entry_price too) |
| **B** | 162 | `pnl_pct=NULL` AND `exit_price IS NOT NULL` | Resolver flagged `STATUS_PNL_MISMATCH` — status='LOST' but math says positive PnL | **Resolver bug — direction inversion or condition flip.** Recompute is trivial. |

**Headline finding:** All 162 Group B rows, when recomputed via the standard
`(exit-entry)/entry * direction` formula, produce **positive PnL** — yet every one is
labeled status='LOST'. Examples: CL=F LONG 87.64→94.65 = +8.0% LOST; AEROUSDT SHORT
0.4454→0.4015 = +9.87% LOST. This is **not a missing-data problem; it is a labeling
bug in whichever resolver wrote `status='LOST'`** (most likely a direction-sign flip
in `multi_asset_scanner` and `copy_trader_intel::copy_hl_lb_None`).

---

## 1. Live counts (verified)

```sql
SELECT COUNT(*) FROM trading_picks
WHERE closed_at IS NOT NULL AND pnl_pct IS NULL;
-- 293

SELECT COUNT(*) FROM trading_picks
WHERE closed_at IS NOT NULL AND pnl_pct IS NULL AND exit_price IS NULL;
-- 131   (Group A)

SELECT COUNT(*) FROM trading_picks
WHERE closed_at IS NOT NULL AND pnl_pct IS NULL AND exit_price IS NOT NULL;
-- 162   (Group B)
```

Universe: 7,093 closed picks total. Orphan rate = 293/7093 = **4.13%**.

---

## 2. Group A — `UNRESOLVABLE_MISSING_PRICE` (131 rows)

### By `exit_reason` / `status`

| status | exit_reason | count |
|---|---|---|
| EXPIRED | UNRESOLVABLE_MISSING_PRICE | 91 |
| TIME_EXIT | UNRESOLVABLE_MISSING_PRICE | 22 |
| LOST | UNRESOLVABLE_MISSING_PRICE | 15 |
| TP_HIT | UNRESOLVABLE_MISSING_PRICE | 3 |

### Top source_system / strategy

| source_system | strategy | n |
|---|---|---|
| luxalgo_filters | luxalgo_confluence | 23 |
| copy_trader_intel | copy_hl_lb_None | 11 |
| copy_trader_binance | binance_smart_money | 10 |
| momentum_evolver | GPX_Gen10_2a4b0b | 8 |
| multitf_evolver | GPM_Gen10_16158d | 5 |
| institutional_picks_engine | forex_carry_momentum | 5 |
| contrarian_evolver | GPX_Gen14_da88cc | 5 |
| audit_ensemble | AuditEnsemble_LONG | 4 |
| battleground_luxalgo | luxalgo_confluence | 3 |

### By category

| category | n |
|---|---|
| crypto | 117 |
| meme | 7 |
| forex | 6 |
| commodity | 1 |

### Age distribution

Bimodal: **86 rows cluster at 53–66 days old** (a single batch the resolver missed
in late March / early April), 45 rows are <50 days old (sporadic per-day failures).

| days_old | n |
|---|---|
| 2–11 | 19 |
| 19–48 | 12 |
| 53 | 65 |
| 54 | 11 |
| 56 | 4 |
| 61–71 | 16 |

### Recoverability

- **115 rows have `entry_price IS NOT NULL`** + symbol + `closed_at` timestamp → re-fetchable.
- **16 rows are missing `entry_price` too** → unrecoverable, recommend mark `EXPIRED_UNRESOLVED`.
- Top symbols are all liquid USDT pairs: BTCUSDT (22), SOLUSDT (16), ETHUSDT (15),
  HYPEUSDT (10), AVAXUSDT (7), DOGEUSDT (6) — **all available on Binance 1m API for any
  date in the last 90d**. Forex (USDJPY=X, 6 rows) and commodity (1 row) via yfinance.
- 1 outlier: `OPNUSDT` (1 row) — check if delisted/renamed before counting it as recoverable.

**Effort estimate to recover 115/131:**
- New resolver pass against Binance `/api/v3/klines` with `interval=1m`, `startTime=closed_at`,
  `limit=1`. 90% of symbols already supported by existing
  `alpha_engine/outcome_resolver.py` fetchers. ~**2–3 hours** to write a focused
  `tools/backfill_orphan_pnl.py` + run it.

---

## 3. Group B — `STATUS_PNL_MISMATCH` (162 rows)

### By source_system / strategy

| source_system | strategy | n |
|---|---|---|
| copy_trader_intel | copy_hl_lb_None | 87 |
| battleground_luxalgo | luxalgo_confluence | 13 |
| alpha_engine | (empty) | 11 |
| alpha_engine | vt_equity_two_day_rsi_reversal | 4 |
| genome_mutations | claude_ml_moderate_mut | 4 |
| genome | st_fear_greed_contrarian (Revival) | 3 |
| multi_asset_copytrader | smart_money_accumulation | 3 |
| regime_terminal | regime_accumulation / regime_mild_bear | 6 |
| multi_asset_scanner | ema_stack_momentum / connors_rsi2 / hyperopt_connors_rsi2 | 4 |

**Single root cause for all 162:** `status='LOST'` AND `exit_reason='STATUS_PNL_MISMATCH'`.

### Math diagnosis

For all 162 rows that have both `entry_price` and `exit_price`, applying the standard
formula:

```python
if direction in ('LONG','BUY'):  pnl = (exit - entry) / entry * 100
else:                            pnl = (entry - exit) / entry * 100
```

yields **162 positive PnL outcomes, 0 negative, 0 zero-entry**. Sample:

| id | dir | entry | exit | recomputed pnl_pct |
|---|---|---|---|---|
| ema_stack_momentum::TLT::2026-03-11 | LONG | 88.28 | 88.40 | +0.13% |
| ema_stack_momentum::CL=F::2026-03-11 | LONG | 87.64 | 94.65 | **+8.00%** |
| connors_rsi2::SI=F::2026-03-12 | LONG | 84.86 | 85.06 | +0.24% |
| copy_hl_lb_None::AEROUSDT::2026-04-18 | SHORT | 0.4454 | 0.4015 | **+9.87%** |
| copy_hl_lb_None::LITUSDT::2026-04-18 | SHORT | 1.0407 | 0.7430 | **+28.6%** |

### Interpretation

The resolver that wrote `status='LOST'` got the direction wrong (or used a
flipped comparator). The Phase 6 backfill correctly refused to write `pnl_pct`
because it detected the mismatch (`STATUS_PNL_MISMATCH`) — that is the right
safeguard. But **the underlying status is wrong**, not the math.

Most likely offender: `copy_trader_intel::copy_hl_lb_None` accounts for 87/162
(54%). The Hyperliquid leaderboard copy-trader source has historically had
direction-handling bugs (see prior incidents on SHORT-side accounting).

### Recoverability

**Trivial.** Recompute `pnl_pct` from entry/exit/direction; **also flip `status`** so
it matches sign of recomputed pnl_pct. **~1 hour** to write
`tools/backfill_status_pnl_mismatch.py` + run. Should be done jointly with the source
audit (open ticket against `copy_trader_intel`).

⚠️ **Asset-class impact**: 135/162 are crypto, 9 equity, 7 stocks, 4 futures, 1 etf,
1 forex. Fixing this will improve the crypto WR by a small but non-zero margin (all
162 were mislabeled losses; recoveries are all wins). Per-class stats are currently
*pessimistically biased* by these mislabels.

---

## 4. Recommendation

### Tiered plan

1. **P1 — Fix Group B mislabels (162 rows, ~1h)**
   New script `tools/backfill_status_pnl_mismatch.py`:
   - Recompute pnl_pct from entry/exit/direction.
   - Set `status = 'WON'` if pnl_pct > 0 else 'LOST'.
   - Set `exit_reason = 'BACKFILL_PHASE7_RESOLVED_FROM_PRICES'`.
   - **Do NOT skip the source audit** — open a P1 incident for
     `copy_trader_intel::copy_hl_lb_None` direction handling (87 of these are from it).

2. **P2 — Backfill Group A recoverable (115 rows, ~2–3h)**
   New script `tools/backfill_orphan_pnl_from_binance.py`:
   - For each row with NULL exit_price + non-NULL entry_price + symbol:
     - Fetch `closed_at` 1m candle via Binance `klines` (with mirrors/CoinGecko/KuCoin
       fallback per repo API failover rule); yfinance for `=X` and `=F` symbols.
     - Compute pnl_pct as in (1).
     - Write `exit_price`, `pnl_pct`, `exit_reason='BACKFILL_PHASE7_FETCHED_BINANCE'`.

3. **P3 — Mark Group A unrecoverable (16 rows, ~5min)**
   - For rows where `entry_price IS NULL`: set `exit_reason='EXPIRED_UNRESOLVED'` and
     **exclude from per-class WR/PF stats** in `asset_class_health` /
     `pf_registry.by_asset_class_policy_clean_net`. They cannot contaminate per-class
     numbers because they have no pnl signal, but they should be excluded from
     `n_resolved` so the gate counts stay honest.

### Why not just exclude all 293?

- Group B (162) is a **labeling bug masquerading as missing data**. Excluding hides a
  real source-system bug. Worse: per-class WR is currently understated, hiding edge.
- Group A (115 recoverable) represents real signal we paid the fetch cost for and lost
  to a resolver timeout. Free win.
- Only Group A (16 unrecoverable, no entry_price) genuinely belongs in
  `EXPIRED_UNRESOLVED`.

### Acceptance criteria for follow-up PR

- After backfill, `SELECT COUNT(*) FROM trading_picks WHERE closed_at IS NOT NULL AND
  pnl_pct IS NULL` ≤ 16.
- New script writes an audit row to `reports/peer_claude-phase7-orphan-pnl-forensics_*`
  before mutation (BEFORE/AFTER counts).
- Per-class `asset_class_health` recomputed; expect small WR↑ for CRYPTO (Group B
  flip) and small n↑ for CRYPTO/FOREX (Group A recovery).

---

## 5. Caveats

- This report is **diagnosis only**; no rows were mutated.
- The recommendation does **not** touch the `pnl_pct` field of any row — execution
  belongs in a separate PR after this analysis is reviewed.
- The status-flip in step (1) is non-trivially destructive: it converts 162 LOSSes to
  WINs on the audit page. Should be human-reviewed before running, ideally with a
  spot-check on 10–20 rows against Binance 1m candles to confirm the recomputed
  exit_price matches what the original resolver wrote (i.e. the exit_price itself is
  correct; only the status/pnl_pct were corrupted).

## 6. Reproducer

```python
import pymysql
conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks',
                      password='stocks1234560', database='ejaguiar1_stocks')
cur = conn.cursor()
# Group A
cur.execute("""SELECT COUNT(*) FROM trading_picks
  WHERE closed_at IS NOT NULL AND pnl_pct IS NULL AND exit_price IS NULL""")
# Group B
cur.execute("""SELECT COUNT(*) FROM trading_picks
  WHERE closed_at IS NOT NULL AND pnl_pct IS NULL AND exit_price IS NOT NULL""")
```

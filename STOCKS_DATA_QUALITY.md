# STOCKS Domain — Consolidated Findings

**Domain:** ejaguiar1_stocks, ejaguiar1_backups, ejaguiar1_memecoin, ejaguiar1_backtests  
**Focus:** Data quality, divergence between stocks/backups schemas, stale data, profitable edges per asset class

---

## 1. DB Divergence VERIFIED (Critical)

**Source:** `dbq.py` cross-schema row counts (2026-11-16)

| Table | ejaguiar1_stocks | ejaguiar1_backups | Delta | % |
|-------|------------------|-------------------|-------|---|
| bt_backtest_trades | 32,441,049 | 32,724,171 | **-283,122** | **-0.87%** |
| (other tables) | — | — | — | — |

**Finding:** `stocks` schema is missing 283k rows vs `backups` schema. This supersedes the older 31,010,964 TABLE_ROWS estimate. Source-of-truth mismatch between production (`stocks`) and backup (`backups`) schemas.

**Implication:** Any backtest or strategy trained on `stocks` schema may be under-counting trades by ~0.87%. Forward validator and PnL integrity checks must use `backups` as the reference until divergence is resolved.

---

## 2. Ghost Rows (Constant PnL)

**Live `db_health.json` (fresh ~1h):** 22,947 ghost rows across 10 cohorts (n>1000 with few distinct entries, constant `pnl_pct`).

**Hardcoded Truth Layer banner (2026-05-31):** "Ghost rows: 0 (was 22,947)" — direct contradiction on public page.

**Finding:** Ghost-row fix from 2026-05-31 partially regressed or the banner was never updated. The generator script still emits the hardcoded "0" string.

**Impact:** Dashboard displays contradictory data; users cannot trust the "Ghost rows" metric.

---

## 3. PnL Integrity (Sampled)

**Sample:** 130/24,158 mismatches >1pp (99.5% ok).  
**Magnitude issues:** ~27% naive (some PnL magnitude drift).  
**WON-vs-PnL contradictions:** None detected.

**Forward Validator:** Fresh (~1h, last WON/LOST ~02:26Z).

---

## 4. Open Bloat

**Active picks:** ~91k OPEN rows vs ~20–22 real filtered picks.  
**Status standardization:** Clean (0 non-canonical).  
**PnL=0% / constant pnl_pct:** Still appear in cohorts and non-crypto active_raw (~89% in some older audits).

---

## 5. Per-Asset-Class Performance (Policy-Clean / Recent)

| Class       | n    | WR%  | PF    | Status          | Notes |
|-------------|------|------|-------|-----------------|-------|
| CRYPTO     | 3716 | 35.8 | 0.92  | NOT ready      | Largest; hold LONG production; inverse/feature sleeves needed. Recent PF ~0.89 |
| EQUITY     | 250  | 59.2 | 0.94  | NOT ready      | Closest; FAIL emitters |
| FOREX      | 612  | 32.2 | 0.66  | FAIL           | Mutate/kill. Tight TP / wide SL asymmetry |
| COMMODITY  | 229  | 40.2 | 1.03  | SUB_TIER2      | Forward paper only until n≥100 + PF≥1.5. Some momentum leads |
| FUTURES    | 52   | 42.3 | 1.09  | SUB_TIER2      | Insufficient n |
| ETF        | 45   | 2.2  | 0.02  | FAIL           | Very poor |
| Others (MEME, PENNY, BOND, etc.) | tiny | — | — | INSUFFICIENT_N | Paper only |

**Intrabar honest view (n≥100 where possible):**
- CRYPTO: 32.9% WR, PF 0.74 (FAIL)
- EQUITY: 60% WR, PF 2.13 (n=72, insufficient)
- COMMODITY: 42% WR, PF 1.77 (n=81)

**Cleanest shadow leads (not sized):**
- commodity futures_momentum ~63% WR / PF 2.6 (n=57)
- forex_rsi2 ~63% WR / PF 2.4 (n=19)
- crypto_rsi5070_us (RSI 50–70 US session) ~ net PF 1.11 (n=430) — strongest forward candidate but fails CI-LB promotion bar

---

## 6. ML Calibration Inverted

**Finding:** High confidence ≠ high WR.  
- CRYPTO ≥0.90 confidence → ~14% WR  
- Lower confidence bands perform better.

**Recommendation:** Score-booster applies penalties. Do not size off raw confidence.

---

## 7. Filter-Survival Gaps

**Example:** COMMODITY dashboard WR 85.5% vs raw 60.2% — significant survival bias in filtered view.

**Implication:** Dashboard inflates vs DB reality. Policy-clean numbers are the only reliable benchmark.

---

## 8. Data Freshness

- Forward validator: ~1h old (last WON/LOST ~02:26Z)
- db_health.json: ~1h old
- Some cohorts: 5h+ old (mixed)

---

## 9. ejaguiar1_memecoin / ejaguiar1_backtests Stale Data

**Context from request:** Check for stale data under ejaguiar1_memecoin that may be relevant findings from before we moved over the tables, or ejaguiar1_backtests.

**Status:** Not yet profiled in this swarm pass. The `dbq.py` run focused on `stocks` vs `backups` divergence. Recommend a follow-up sweep on `memecoin` and `backtests` schemas for:
- Tables with last_insert >30 days
- Tables with row counts unchanged for >7 days
- Any "ghost" patterns (constant pnl_pct, low distinct entries)

---

## 10. Profitable Edges per Asset Class (Summary)

**Winning strategy candidates (shadow leads, not sized):**
1. commodity futures_momentum (63% WR, PF 2.6, n=57)
2. forex_rsi2 (63% WR, PF 2.4, n=19)
3. crypto_rsi5070_us (net PF 1.11, n=430) — needs CI-LB validation

**Policy-clean verdict:** 0/9 asset classes money-ready. No class clears real-money bars (DSR>0.95, PBO<0.05, WFE>60%, live-Sharpe>0.5, n≥100).

---

## Files Consumed

- `/home/eaguiar2015/findtorontoevents_antigravity.ca/SWARM_Nov162026/DB/DONE/CROSS_DB_DATA_QUALITY_MATRIX.md`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/SWARM_Nov162026/DB/DONE/stocks_db_profile.md`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/SWARM_Nov162026/DB/DONE/dbq.py`
- Context from user prompt (CONDENSED_AUDIT_SUMMARY)

---

## Next Steps (TODO)

- [ ] Reconcile `stocks` vs `backups` divergence (283k row gap)
- [ ] Profile ejaguiar1_memecoin and ejaguiar1_backtests for stale data
- [ ] Fix ghost-string generator (remove hardcoded "0")
- [ ] Validate shadow leads (commodity futures_momentum, forex_rsi2) with n≥100 + CI-LB
- [ ] Apply score-booster penalty for high-confidence/low-WR bands

---

*Generated 2026-11-16T06:35Z — STOCKS domain consolidation*

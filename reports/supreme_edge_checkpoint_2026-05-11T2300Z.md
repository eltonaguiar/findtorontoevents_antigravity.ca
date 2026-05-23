# SUPREME EDGE — Checkpoint Report 2026-05-11T23:00Z

**Branch:** main &middot; **HEAD:** post-Kimi-archive (`6fc93b4b137`) &middot; **Cadence:** 20-min progress per user directive

## Shipped this 20-min window (22:30Z → 23:00Z)

| Commit | Action | Verdict |
|---|---|---|
| `81bd0b86388` | Wave 1 — rm `alpha_engine/data/circuit_breaker_state.json` (48d stale HALT) | ✓ Forward validator unfrozen: `bt_backtest_trades MAX(imported_at)=2026-05-11 20:00:59`, 1.8M rows |
| `4a2d337a5dc` | P0 #2 + #3 + #4 — blacklist `kimi_signal_tracking` + 3 `crypto_soc_*` quarantine + elite-score floors FOREX 50→70 / COMMODITY 50→65 / EQUITY 50→60 | ✓ Shipped to main |
| `6fc93b4b137` | Kimi 4-agent swarm archive (32 files) + master plan revision + Kimi P0 #9/#10 + anti_overfit_validator P1 wire-up | ✓ Live on findtorontoevents.ca/updates/ |

## P0 verification results (RAW DB probes against `mysql.50webs.com::ejaguiar1_stocks`)

### P0 #5 — multi_asset_cot verification ⚠ DASHBOARD ARTIFACT

**Finding:** `multi_asset_cot` strategy does NOT exist in `trading_picks`, `at_raw_picks`, `at_local_picks`, `at_consensus_picks`, or `bt_backtest_trades`. The dashboard `systems` payload entry "multi_asset_cot PF=19.19 / n=130" is a **synthesized system-level aggregator** combining `cot_positioning` + `cftc_cot_commercial_signal` outputs.

**Actual COT strategies:**

| Strategy | Table | Total n | OPEN bloat | Closed | WR (closed) | PF (closed) |
|---|---|---|---|---|---|---|
| `cot_positioning` | trading_picks | 3,886 | 96.7% (3,757 OPEN) | 104 | 86.5% (90/104) | 10.82 |
| `cot_positioning` | bt_backtest_trades | 186,368 | — | — | — | — |
| `cftc_cot_commercial_signal` | trading_picks | 2,299 | 95.1% | 112 | 91.1% (102/112) | 0.85 |

**Verdict:** COMMODITY edge is REAL on the small closed sample but OPEN-bloat factor invalidates any "n=130" claim at face value. The 96.7% OPEN-bloat directly explains the **DB Health "Phantom EXPIRED 100% / Raw-Pick Coverage 0.09%"** metrics — outcome resolver is not closing positions even post-Wave-1. Wave 1.5 (lm_signals + signal_tier + at_consensus_picks) remains required.

### P0 #6 — claude_gainer_st enforcement ✓ WORKING

**Finding:** `claude_gainer_st` returns **0 rows** in `trading_picks`, `at_raw_picks`, `at_local_picks`, and `bt_backtest_trades`. Blacklist at `alpha_engine/config.py:216` is effectively enforced — no current live emissions.

**Dashboard reconciliation:** the `systems` payload entry "claude_gainer_st PF 6.12 / n=3472 / WR 78.5%" must come from a historical-archive table NOT under the standard pick tables — possibly an aggregator's frozen pre-2026-05-01 snapshot. Master plan flagged "contradiction" is RESOLVED: blacklist works; aggregator just hasn't refreshed its frozen historical snapshot.

**Action:** flag dashboard `systems` payload to either (a) refresh against live blacklist or (b) show `last_signal_at` and explicitly mark "no current emissions since blacklist 2026-05-01".

### P0 #9 — ML calibration inversion verify ⚠ KIMI'S CLAIM CONFIRMED

Direct query against `trading_picks` closed picks with `confidence` column:

| Confidence bucket | n | WR % | avg_pnl % |
|---|---|---|---|
| **≥0.90** | 610 | **14.4** | **-5.85** |
| 0.80-0.89 | 678 | 48.7 | -0.05 |
| 0.70-0.79 | 1,949 | 40.7 | -2.40 |
| 0.60-0.69 | 3,048 | 44.6 | -36.62 |
| 0.50-0.59 | 908 | 39.5 | +0.56 |
| **<0.50** | 489 | **60.3** | **+0.00** |

**Verdict:** highest-confidence bucket has LOWEST WR and WORST PnL; lowest-confidence bucket has HIGHEST WR. **Confidence is currently an anti-signal across the system, not just ETF/CRYPTO as memory `project_performance_reality` documented.**

### BONUS finding — Confidence schema mixed-scale data-quality bug 🆕

Spot-check of conf≥0.9 cohort shows confidence values like `10.000` — strongly suggests rows being written on a 0-10 scale alongside the standard 0-1 scale rows in the same `confidence` column. This alone introduces massive noise into calibration measurements and into the HIGH_CONVICTION button gate (which assumes 0-1 scale).

| conf value | observed |
|---|---|
| 0.50-1.00 | normal 0-1 scale (post-2026-04-X writers) |
| 10.000 | 0-10 scale (legacy writer or different source — TBD) |

**Action:** add `confidence_schema_normalizer` to `audit_trail/dashboard_generator.py` — clamp confidence to 0-1 on read; flag writers emitting >1 values as a regression test failure.

## Remaining P0 (next 20-min window 23:00Z → 23:20Z)

- [ ] P0 #1 — coordinate PR #904 merge (peer chatlog says MERGEABLE/CLEAN at `6d7ccd928fd`)
- [ ] P0 #7 — verify max-drawdown calc uses capped PnL (Kimi flagged 680% MDD)
- [ ] P0 #8 — cap `quan_engine` to 12% CRYPTO volume share
- [ ] P0 #10 (Kimi) — EQUITY filter-criteria audit (RAW 1.84% WR / dashboard 54% — what's the filter?)
- [ ] P1 — wire `alpha_engine/anti_overfit_validator.py` (CPCV/PBO/DSR) into `passes_smart_gate`
- [ ] Wave 1.5a/b/c — independent pipeline fixes (lm_signals expire-cron, signal_tier writer, at_consensus_picks time-travel)

## Risk register updates

| Risk | Status | Notes |
|---|---|---|
| Calibration inversion system-wide | **CONFIRMED** (was P2 hypothesis) | escalates to P0 #9 |
| Confidence schema mixed-scale | **NEW** P0 finding | normalize on read |
| OPEN-bloat post-Wave-1 | **CONFIRMED** | Wave 1 alone insufficient; Wave 1.5 critical |
| `multi_asset_cot` synthesized | **CONFIRMED** | not a real strategy; aggregator artifact |
| `claude_gainer_st` enforcement | **WORKING** | dashboard payload stale — refresh issue, not gate failure |
| `anti_overfit_validator.py` orphan | **CONFIRMED** | 13.8KB, last modified 2026-05-02, zero production callers per CLAUDE.md Wire-Up Rule |

## Verification commands (reproducer)

```bash
# Wave 1 verify
python -c "import pymysql; c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password='stocks',database='ejaguiar1_stocks'); cur=c.cursor(); cur.execute(\"SELECT MAX(imported_at), COUNT(*) FROM bt_backtest_trades WHERE status IN ('WON','LOST')\"); print(cur.fetchone())"
# Expect: (datetime.datetime(2026, 5, 11, 20, 0, 59), 1819839) ✓

# Calibration verify
python -c "import pymysql; c=pymysql.connect(host='mysql.50webs.com',user='ejaguiar1_stocks',password='stocks',database='ejaguiar1_stocks'); cur=c.cursor(); cur.execute(\"SELECT CASE WHEN confidence>=0.9 THEN 'A_>=90' WHEN confidence>=0.5 THEN 'B_50-89' ELSE 'C_<50' END AS bucket, COUNT(*) AS n, SUM(CASE WHEN status IN ('WON','WIN','TP_HIT') THEN 1 ELSE 0 END) AS wins FROM trading_picks WHERE status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT') AND confidence IS NOT NULL GROUP BY bucket\"); [print(r) for r in cur.fetchall()]"
```

## Live URLs

- Master plan: https://findtorontoevents.ca/updates/2026-05-11-money-maker-master-plan.html (200 OK)
- Kimi audit: https://findtorontoevents.ca/reports/kimi_edge_audit_2026-05-11/edge_audit_report.html (200 OK)
- This checkpoint: https://findtorontoevents.ca/reports/supreme_edge_checkpoint_2026-05-11T2300Z.md (deploying)

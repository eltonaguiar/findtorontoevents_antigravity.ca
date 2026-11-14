# Detailed Audit Findings (final_v3, 2026-11-14)

**Scope:** All asset classes (stocks, crypto, forex, bonds, ETFs, mutual funds)  
**Basis:** Live ledger screener (0/166 cells), protocol v1-v4 runs (0/23 proved), peer research (3 approaches, 0 strictly proved), today's modified files

---

## 1. Actions Health — FAIL

**365 GitHub Actions workflows** (361 active, 4 disabled). Latest-run state:

| State | Count |
|---|---:|
| success | 283 |
| failure | 30 |
| cancelled | 11 |
| skipped | 1 |
| in_progress/queued | 21 |
| never-run / API error | 20 |
| disabled | 4 |

**Critical failures:** `CI Tests`, all three `Live Trading Bot` variants, `Daily Price Refresh` (PHP 404 since 2026-04-29), `Daily Prices yfinance Refresh`, `DNA Strategy Pipeline`, `Forward Test - Strategy Validation`, `picks_dispatch`, `self_optimizing_trading`, `verified-pilot-daily`, `robust-edge-miner`, `ALPHA ENGINE - Live Autonomous Scanner`.

**Audit-relevant:** `audit-hourly-update.yml` success; `db-freshness-guardian.yml` success; `Pick Monitor & Price Validator (30min)` success; `outcome-resolver.yml` cancelled.

---

## 2. Active Picks — FAIL

**Curated picks** (`picks_now.json`, 2026-11-12, RISK_OFF regime): 25 picks, 100% LONG-biased (25/25 STRONG_BUY/WATCH). By class: BOND 9, EQUITY 5, ETF 5, FOREX 6; **CRYPCO=0, MUTUAL_FUND=0, COMMODITY=0**. 20/25 have zero DB forward validation (db_n=0). Target price null on 20/25.

**Live open P&L** (`picks_now_live_pnl.json`, yfinance/Binance): 4,310 open, 4,260 priced; avg PnL -1.42%; 1,693 positive / 2,556 negative. By class: BOND -1.66% (n=1,293), EQUITY -5.22% (n=757), ETF -0.20% (n=1,722), FOREX +0.26% (n=534), COMMODITY +3.57% (n=4). **CRYPCO and MUTUAL_FUND absent** from live-P&L slice.

**Cross-reference (Yahoo Finance spot checks):** SPY $754.37 (-0.36%); BITO entry $9.56 (11/12) vs Yahoo $9.15 (11/14) — directionally consistent. Full verification not performed.

---

## 3. Frozen Data — FAIL

| Item | Finding |
|---|---|
| `recent_closed.json` | 0 bytes (empty; no writer) |
| `db_freshness.json` | Generated 2026-05-23 (~5.5 months stale), overall RED |
| `signal_outcomes` check | RED — ~80 days stale, last resolved 2026-03-04, n_resolved_today=0 |
| `backtests` check | YELLOW — no timestamp column in `backtest_trades`, n_total=0 |
| `signals_database.json` | Latest signals Feb 2026 (stale) |
| `hyrotrader_closed_picks.json` | Generated 2026-05-30, n_closed=0, picks=[] |
| `hyrotrader_journal.json` | trades=[], daily_summary=[] (no trades ever logged) |
| No closed picks | ~26 days (most recent 2026-10-19) |
| pnl_pct=0% entries | 54 entries frozen at zero |

---

## 4. Closed Picks — FAIL

**3,500 closed picks** (2026-02-17 → 2026-10-19). WON 1,573 / LOST 1,874 / CLOSED 52 (all pnl=0) / UNRESOLVED 1. **Overall WR 45.6%** (below 50%). All classes WR <50%: BOND 33.3%, CRYPCO 45.7%, EQUITY 48.2%, ETF 44.3%, FOREX 40.3%, COMMODITY 50.0%, FUTURES 0.0%.

**48h window:** FOREX 5.6% WR (PF 0.057), ETF 9.1% WR (PF 0.077), EQUITY n=1 (INSUFF-N), FUTURES 94.1% WR but n=34 single symbol GC=F (76.5% share).

**14d window:** CRYPCO 43.4% WR (PF 0.966), FOREX 6.8% WR (PF 0.087), ETF 26.7% WR (PF 0.631), EQUITY 35.3% WR (PF 1.007).

---

## 5. Money-Ready Screening — 0/166 Cells Pass

Applied full Tier-2 gate contract (n≥100, WR≥50%, PF≥1.5, net expectancy>0 with CI lower>0, MDD<20%, single-source<60%, multi-source≥2, regime-direction consistency) to all 166 strategy×class×direction cells.

**Class rollup:**

| Class | Cells | n | WR | PF | Avg Net Expectancy | Passing |
|---|---|---|---|---|---|---|
| CRYPCO | 67 | 2,069 | 45.7% | 1.31 | +0.385% | 0 |
| EQUITY | 44 | 680 | 48.2% | 1.23 | +0.486% | 0 |
| ETF | 32 | 503 | 44.3% | 1.07 | -0.165% | 0 |
| COMMODITY | 3 | 8 | 50.0% | 1.03 | +0.897% | 0 |
| FOREX | 9 | 159 | 40.3% | 0.66 | -0.528% | 0 |
| BOND | 10 | 27 | 33.3% | 0.56 | -0.342% | 0 |
| FUTURES | 1 | 1 | 0.0% | 0.00 | -0.675% | 0 |

**All 166 cells single-source.** Only 1 cell clears n≥100 (`luxalgo_confluence` CRYPCO LONG, n=563) and it fails WR (44%), PF (1.24), MDD (289.5%), single-source (94%).

**CRYPCO expectancy:** -5.86% with bootstrap 95% CI [-4.96%, -4.38%] — statistically significant NEGATIVE.

---

## 6. Bugs Found Today (Modified Files)

| File | Bug | Fix Applied Today |
|---|---|---|
| `audit_trail/dashboard_generator.py:7772` | `after_cost_net_per_trade=None` for all 3,500 closed rows — HC after-cost gate reads dead field | Fallback to `stamp_class_after_cost` from `tools/per_class_cost_gate.py` |
| `audit_trail/universal_pick_resolver.py:614-712` | Pre-2026-11-14 code returned stop/TP level unconditionally even when bar gapped through level — understated SL on gap-downs, overstated TP on gap-ups | Gap-aware fill pricing (`_gap_fill_price`): fill at bar open when open is beyond level; fail-open on missing data |
| `tools/hc_gates_python.py:444-538` | No per-class cost gate; ~390 picks/month emitted despite costs exceeding average PnL (ETF 267%, COMMODITY 422%) | Added `passes_per_class_cost_gate` — blocks pick when class avg PnL < 3x round-trip cost; fail-open on missing/stale data |

---

## 7. Common Themes (All Peers Agree)

1. **NOT money-ready** — all 9 classes
2. **Data pipeline broken** — stale picks, PnL contradictions, empty audit_trail.db, EXPIRED→WON mislabeling
3. **Multiple testing not corrected** — horizon harness reports counts but no BH/Bonferroni correction
4. **Benchmark-relative alpha unproven** — ITERATION-005 trend buy-and-hold Sharpe ~2.2 on same assets; H10 risk-matched benchmark Sharpe 2.168-2.285 > 1.83
5. **Single-source concentration** — all 166 cells single-source; multi-source gate mechanically impossible
6. **VWAP refuted** — Sharpe/PBO certification refuted by independent re-examination
7. **Mutual fund infrastructure exists but not connected** — ranker + walkforward complete, but no live class

---

## 8. Deeper Investigation Items

1. **Cross-ledger reconciliation**: `money_ready_verdict` (CRYPCO n=3,705) vs `pf_registry` (CRYPCO n=22,055) vs `recent_closed` vs `at_raw_picks` — row counts diverge materially; no reconciliation published
2. **Resolution provenance**: All 3,500 closed rows missing valid `resolution_method`
3. **Per-class cost gate indexing**: Index built from closed rows + `tools/data/transaction_costs.json` — needs validation
4. **Mutual fund low-fee subset**: 38 funds in metadata; 20 meet sub-0.20% ER + $0 min initial criteria; need NAV history ≥5y and benchmark
5. **SubQ comparison**: Not yet performed — matrix drafted in `06_subq_comparison/`

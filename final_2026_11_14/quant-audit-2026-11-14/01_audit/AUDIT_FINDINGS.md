# 01_Audit — Quantitative Audit Findings (2026-11-14)

**Worktree:** quant-audit-2026-11-14  
**Scope:** Stocks, crypto, forex, bonds, ETFs, mutual funds at findtorontoevents.ca/audit  
**Data source:** `recent_closed_array.json` (3,500 picks; 3,447 decisive WON/LOST; 53 non-decisive excluded)  
**Cross-reference price source:** Yahoo Finance (`query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>`) — spot checks only (SPY $754.37, BITO $9.15)

---

## A. Actions Health — FAIL

**365 GitHub Actions workflows** in `.github/workflows/` (361 active, 4 disabled).

| Metric | Count |
|---|---|
| `success` (latest run) | 283 |
| `failure` (latest run) | 30 |
| `cancelled` (latest run) | 11 |
| `skipped` (latest run) | 1 |
| `in_progress`/`queued` (running at snapshot) | 21 |
| No runs ever / API returned no run | 20 |
| Disabled manually | 4 |

**Disabled workflows:** `AI Tournament Pipeline — Daily Picks + DB Ingest`, `Real-Time Battle Test`, `Forex Agent`, `Forex Smart Picks Scanner`.

**Trading-critical failures (latest run):**
- `CI Tests` — failure (push, main)
- `ALPHA ENGINE - Live Autonomous Scanner` — failure
- `Autonomous Trading Bot` — failure
- `Live Trading Bot` / `Live Trading Bot - Canada Edition` / `Live Trading Bot - Canada Edition (FREE Data)` — all failure
- `Daily Price Refresh` — failure (PHP endpoint `fetch_prices.php` returns HTTP 404, dead since 2026-04-29)
- `Daily Prices yfinance Refresh` — failure
- `DNA Strategy Pipeline` — failure
- `Forward Test - Strategy Validation` — failure
- `picks_dispatch` — failure
- `self_optimizing_trading` — failure
- `verified-pilot-daily` — failure
- `robust-edge-miner` — failure
- `sports-smoke-and-e2e` — failure

**Audit-relevant:** `audit-hourly-update.yml` success; `db-freshness-guardian.yml` success; `Pick Monitor & Price Validator (30min)` success; `outcome-resolver.yml` **cancelled**.

**Unverified:** per-workflow warning counts (not exposed by workflow-runs API without drilling into each job log).

---

## B. Active Picks — FAIL

**Curated picks** — `audit_dashboard/data/picks_now.json` (generated 2026-11-12, `market_regime: RISK_OFF`, `n_scored: 325`):

| Metric | Value |
|---|---|
| Total picks | 25 |
| Direction bias | 100% LONG (25/25 STRONG_BUY or WATCH) despite RISK_OFF regime |
| By class | BOND 9, EQUITY 5, ETF 5, FOREX 6; **CRYPCO=0, MUTUAL FUND=0, COMMODITY=0** |
| Forward validation (db_n=0) | 20/25 (80%) have zero DB history |
| Target price defined | 5/25 (20%) — null on 20 picks |
| db_wr > 0 | 5/25; best: AUDUSD=X 33.3% (n=18), AUDJPY=X 37.5% (n=56) |

**Live open P&L** — `audit_dashboard/data/picks_now_live_pnl.json` (generated 2026-11-12, source: yfinance/Binance):

| Class | n | avg_pnl_pct |
|---|---|---|
| BOND | 1,293 | −1.66% |
| EQUITY | 757 | −5.22% |
| ETF | 1,722 | −0.20% |
| FOREX | 534 | +0.26% |
| COMMODITY | 4 | +3.57% |
| **Overall** | **4,310** | **−1.42%** |

**CRYPCO and MUTUAL FUND absent** from live-P&L slice. 4310 open, 4260 priced, 1,693 positive / 2,556 negative, 50 no price.

**Cross-reference (Yahoo Finance, spot checks):** SPY $754.37 (−0.36%); BITO system entry $9.56 (11/12) vs Yahoo $9.15 (11/14) — directionally consistent. Full price verification across all picks not performed (partial).

---

## C. Frozen Data — FAIL

| Item | Finding |
|---|---|
| `recent_closed.json` | **0 bytes** (empty; no script writes it) |
| `db_freshness.json` | Generated 2026-05-23 (~5.5 months stale), overall RED |
| `signal_outcomes` check | RED — 115,782 min stale (~80 days), last resolved 2026-03-04, n_resolved_today=0 |
| `backtests` check | YELLOW — no timestamp column in `backtest_trades`, n_total=0 |
| `signals_database.json` | Latest signals Feb 2026 (stale) |
| `hyrotrader_closed_picks.json` | Generated 2026-05-30, n_closed=0, picks=[] |
| `hyrotrader_journal.json` | trades=[], daily_summary=[] (no trades ever logged) |
| Hyro account snapshot | last_session_date 2026-04-08, equity 4929.34 (−1.41%) — stale |
| No closed picks | ~26 days (most recent timestamp 2026-10-19) |
| pnl_pct = 0% entries | **54 entries** frozen at zero (incl. V/MA/JPM/JNJ/GOOGL/AMZN/LLY/GE/CAT, 2026-08-26; TLT UNRESOLVED 2026-05-29) |
| `picks_now.json` / `picks_now_live_pnl.json` | Dated 2026-11-12 — not refreshed today (11/14) |

---

## D. Closed Picks (Realized Performance) — FAIL

**Source:** `recent_closed_array.json` — 3,500 closed picks, timestamps 2026-02-17 → 2026-10-19.

| Status | Count |
|---|---|
| WON | 1,573 |
| LOST | 1,874 |
| CLOSED (pnl=0) | 52 |
| UNRESOLVED | 1 |

**Overall realized WR:** 1,573 / (1,573+1,874) = **45.6%** (below 50%)

**Overall avg PnL:** +0.41% (wins avg +4.45%, losses avg −2.97%)

**Per-class win rate (decisive only, all below 50%):**

| Class | n | WR | Avg PnL |
|---|---|---|---|
| BOND | 28 | 33.3% | −0.23% |
| CRYPCO | 2,070 | 45.7% | +0.54% |
| EQUITY | 690 | 48.2% | +0.46% |
| ETF | 503 | 44.3% | +0.08% |
| FOREX | 199 | 40.3% | −0.13% |
| COMMODITY | 9 | 50.0% | +0.03% |
| FUTURES | 1 | 0.0% | −0.47% |

**48h window** (`pick_summary_stats_48h.json`):
- FUTURES 94.1% WR but n=34, single symbol GC=F (76.5% share), single source AlphaEngine
- FOREX **5.6% WR (1/18), PF 0.057**
- ETF **9.1% WR (1/11), PF 0.077**
- EQUITY n=1 decisive (INSUFF-N)

**14d window** (`pick_summary_stats_14d.json`):
- CRYPCO 43.4% WR (PF 0.966)
- FOREX **6.8% WR (PF 0.088)**
- ETF **26.7% WR (PF 0.631)**
- EQUITY 35.3% WR (PF 1.007)

---

## E. Money-Ready Gate Screening — 0/166 Cells Pass

Applied full Tier-2 gate contract (n≥100, WR≥50%, PF≥1.5, net expectancy>0 with CI lower bound>0, MDD<20%, single-source<60%, multi-source≥2, regime-direction consistency) to all 166 strategy×class×direction cells using `tools/money_ready_screener.py`.

**Class-level rollup:**

| Class | Cells | n | WR | PF | Avg Net Expectancy | Passing |
|---|---|---|---|---|---|---|
| CRYPCO | 67 | 2,069 | 45.7% | 1.31 | +0.385% | 0 |
| EQUITY | 44 | 680 | 48.2% | 1.23 | +0.486% | 0 |
| ETF | 32 | 503 | 44.3% | 1.07 | −0.165% | 0 |
| COMMODITY | 3 | 8 | 50.0% | 1.03 | +0.897% | 0 |
| FOREX | 9 | 159 | 40.3% | 0.66 | −0.528% | 0 |
| BOND | 10 | 27 | 33.3% | 0.56 | −0.342% | 0 |
| FUTURES | 1 | 1 | 0.0% | 0.00 | −0.675% | 0 |

**Best cell:** `mega_mutation_macd_rsi_m048` CRYPCO LONG, n=48, WR=75.0%, PF=6.98, net_exp=+6.70% — FAILS on n<100, MDD=209.6%, single-source=100%.

**Largest cell:** `luxalgo_confluence` CRYPCO LONG, n=563, WR=44.0%, PF=1.24 — FAILS on WR<50%, PF<1.5, MDD=289.5%, single-source=94%.

**All 166 cells are single-source** (100% from one `source_system`). **Only 1 cell clears n≥100.**

---

## F. CRYPCO Expectancy (from money_ready_verdict.json)

- Expectancy: **−5.86%** with bootstrap 95% CI **[−4.96%, −4.38%]** — statistically significant NEGATIVE
- MDD ≈ 100%, CVaR₉₅ = −95.04%, WR 36.0%, PF 0.92 (<1)
- 84 strategies tested (PBO=0, SPA p=0.0) — multiple-testing artifact
- Dashboard "Smart Picks" CRYPCO cohort (WR 78.93%, PF 9.69, n=337) is inflated: dominated by one strategy (70%), one source (91.7%), EXPIRED→WON mislabeled (63.9% on 97 EXPIRED rows). DB-side raw `at_raw_picks` 90d: WR 39.38%, PF 0.371 — diametrically opposite.

---

## G. Systemic Data Defects (cross-verified with peers)

1. **EXPIRED picks mislabeled as WON** — `tools/relabel_crypto_expired.py`, `tools/resolver_hygiene_check.py`; outcome-resolver PNL_WIN_THRESHOLD=0.00001 (0.1bp) converted spread noise into "WIN" labels for FOREX/COMMODITY (~1,700 non-crypto picks historically)
2. **53 picks frozen at pnl_pct=0%** in `recent_closed_array.json`
3. **`recent_closed.json` = 0 bytes** (abandoned, no writer)
4. **`hyrotrader_journal.json` = 0 trades** (no real fills ever logged)
5. **`at_signal_outcomes` RED** — ~80 days stale, n_resolved_today=0
6. **Dead price refresh** — `fetch_prices.php` HTTP 404 since 2026-04-29; yfinance replacement also failing
7. **No MUTUAL_FUND class** anywhere (not in `asset_class.py`, `gatekeeper ASSET_CLASS_MAP`, or any picker)

---

## H. Peer Consensus (cross-referenced)

All peers (childlike-airport/kilo, finpredict-v2, finpredict-v3) agree on:
- **NOT money-ready; data pipeline broken**
- **Highest-value first fixes:** PnL-unit contract + NULL-tombstone zombie drain
- **Backtest↔forward disconnect:** 0 rows have both bt_trades>0 and fwd_trades>0
- **Multiple-testing / look-elsewhere effect** invalidates most high-WR cells

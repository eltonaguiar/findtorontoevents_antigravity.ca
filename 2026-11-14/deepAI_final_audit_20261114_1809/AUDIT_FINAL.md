# FINAL AUDIT — findtorontoevents.ca/audit prediction system
**Date:** 2026-11-14 (live data pulled 16:15Z, market prices 16:20Z)
**Auditor:** DeepAI Code agent · isolated worktree `.inspect-wt` @ `f54efb3b4a`
**Scope:** stocks, crypto, forex, bonds, ETFs, mutual funds — /audit and /audit/hyrotrader

Market data sources used for cross-reference: **Binance** (`api.binance.com/api/v3/ticker/price`,
3,745 symbols), **Yahoo Finance** chart API (90 equity/ETF/commodity tickers),
**open.er-api.com** (USD-based FX rates). All timestamps UTC.

---

# 1. Actions health — **FAIL**

**Every workflow with a run in the last 5 hours (1,200 runs scanned → 185 distinct workflows):**
163 success · 7 failure · 4 cancelled · 10 in progress · 1 skipped. Of 365 registered workflows,
185 ran in-window; the remaining 180 are daily/weekly/monthly and are **UNVERIFIED** for last-run
status (GitHub API budget; see `notes/01_actions_health.md`).

**Failing now:**
| Workflow | Last run | Conclusion |
|---|---|---|
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | 16:19 | failure |
| Sports endpoint smoke + Playwright | 16:18 | failure |
| ALPHA ENGINE FAST (Tighter TP/SL) | 16:10 | failure |
| Signal Tracking & Validation - Beat the Market | 16:01 | failure |
| CI Tests | 14:37 | failure |
| robust-edge-miner | 12:43 | failure |
| Mirror: findtorontoevents.ca ↔ torntoevent.net | 12:11 | failure |

**Also failing earlier in the day (audited per-workflow):** ALPHA ENGINE Live Autonomous Scanner
(14:09 "Full cycle" step), Daily Prices yfinance Refresh (Nov 12 **and** 13).

**Cancelled (0 jobs executed — discarded while queued):** Unified Audit Dashboard (11:14, 14:14, 16:14),
Outcome Resolver (16:19), Academic Strategies Daily, STOCKSUNIFY2 daily-stocks pull.
**Effect:** the hourly /audit publish lands ~70% of hours.

**Warnings:** workflows emit `::warning::` annotations (freshness tripwires, PF reconciliation
divergence), but per-run annotation bodies require repo-admin log access → **UNVERIFIED**.

---

# 2. Active Picks — **FAIL (81% of open picks have no real P/L; losses understated ~10x)**

**Method:** took all 703 open/active rows from `dashboard_payload.json` (16:15:51Z), independently
repriced 624 of them from Binance/Yahoo/ER-API, recomputed P/L from entry → current market and
compared with the dashboard's own number.

| Class | priced n | shows 0/None | disagree >1pp | disagree >5pp | median abs diff | **median REAL P/L** |
|---|---|---|---|---|---|---|
| CRYPTO | 334 | **270 (81%)** | 241 | 164 | **4.71pp** | **−3.69%** |
| FOREX | 121 | 118 | 1 | 1 | 0.06 | −0.01% |
| EQUITY | 94 | 57 | 13 | 1 | 0.00 | −0.00% |
| ETF | 30 | 24 | 0 | 0 | 0.00 | 0.00% |
| COMMODITY | 27 | 23 | 3 | 3 | 0.00 | 0.00% |
| BOND | 15 | 9 | 0 | 0 | 0.04 | +0.09% |
| FUTURES | 3 | 3 | 0 | 0 | 0.00 | 0.00% |

**Aggregate:** 504/624 (81%) open picks display 0%/unknown. Their true mark-to-market:
median −0.04%, **mean −1.80%**, with **125 rows actually down >5%**. Sum of dashboard-claimed P/L =
**−106pp**; sum of real mark-to-market = **−1,116pp** → **losses understated roughly 10x.**

**Worst individual errors:**
- `EURGBP=X` entry recorded as **688.17** vs market 0.835 → dashboard shows −0.63% instead of **−99.9%**.
- `ENAUSDT`, `ARBUSDT`, `SUIUSDT` LONGs: real **−22.4% / −19.9% / −19.6%**, dashboard **0.0%**.

**Stale entries flagged:** 3,272 of 4,164 `active_raw` rows are `EXPIRED` with pnl=0 (78.6%);
`inverse_mutations` alone contributes 2,262 re-emissions of BTCUSDT/XRPUSDT/NEARUSDT since 2026-07.
Median CRYPTO active_raw age **89 days**; oldest 267 days.

**Named-symbol verification (your question):**
| Symbol | Entry | Market (Binance) | Real P/L | Dashboard |
|---|---|---|---|---|
| NEARUSDT (tsmom_volscaled, SHORT) | 3.324 | **3.142** | **+5.47%** | +5.75% ✅ consistent |
| NEARUSDT (battleground_ml, LONG) | 3.340 | 3.142 | −5.93% | **0.0%** ❌ hidden |
| XRPUSDT (prediction_market_consensus) | 0.9685 | **0.964** | +0.47% | +0.52% ✅ |
| BTCUSDT (prediction_market_consensus) | 65,252 | **66,048** | −1.22% | −0.24% ⚠ |
| USDCAD=X | 1.4269 | **1.4260** | +0.06% | −0.00% ✅ (genuinely flat) |
| NZDUSD=X | 0.55252 | **0.55273** | +0.04% | 0.00% ✅ (genuinely flat) |

→ **Your NEARUSDT 3.16% figure is plausible and consistent with market data.** But USDCAD/NZDUSD
really ARE flat (real moves +0.06%/+0.04% — not a data bug), while most *crypto* "flat" rows are stale
zeros hiding double-digit losses.

**Data-quality defect:** `'MONTREAL CANADIENS VS BUFFALO SABRES'` appears as a *symbol* in active
picks — sports bets are leaking into the trading feed.

---

# 3. Frozen data — **FAIL**

- **Zero-P/L is systemic:** peer audit `reports/zero_pnl_data_pipeline_audit_2026-06-05.md` found
  100% of 28,218 zero rows are `status=EXPIRED`, `resolution_method=TIME_EXPIRED`, produced by the
  `backfill_widened/updated` resolvers (81.2% / 96.6% zero share). The time-expiry resolver writes
  `pnl_pct=0` instead of computing close-vs-entry.
- **Per-class zero share (peer):** FUTURES 98.4% · INDEX 99.0% · BOND 89.1% · COMMODITY 84.9% ·
  FOREX 83.7% · ETF 83.1% · EQUITY 79.5% · CRYPTO 56.5%.
- **My live measurement:** 504/624 open picks (81%) show 0/None P/L; real mean −1.80%.
- **Dead timestamps:** `hyro_pick_performance.json` generated **2026-11-08** → 157h stale while the
  "Hyro daily" workflow reports success (silent deploy/emit break).
- **Fields that never update:** OPEN picks with `current_price=None` for days
  (10 incubator BTCUSDT opens from 2026-11-12 still unpriced at snapshot).
- **404 data files** the frontend requests: `pick_funnel_snapshot.json`,
  `strategy_tribunal_latest.json` (Playwright-confirmed 404).
- **Regime layer effectively empty:** `closed_with_regime = 21` vs `closed_without_regime = 8,538`
  (0.25% coverage) — no regime-conditioned claim is supportable.

---

# 4. Closed picks — recent realized performance — **FAIL**

Recomputed from the live payload's 3,500 most-recent closed picks (slippage-adjusted P/L as stored):

| Class | 7d n | 7d WR | 7d PF | 7d Σ | 14d PF | 30d n | 30d PF | 30d Σ |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 332 | 34.9% | 0.64 | **−218.3pp** | 0.79 | 1,034 | 0.80 | **−352.7pp** |
| EQUITY | 19 | 73.7% | 3.63 | +67.8 | 1.20 | 100 | 0.84 | −41.2 |
| ETF | 15 | 66.7% | 3.21 | +25.2 | 0.84 | 81 | 0.72 | −29.8 |
| FOREX | 25 | 32.0% | 0.56 | −3.9 | 1.48 | 43 | 1.48 | +5.2 |
| COMMODITY | 6 | 33.3% | 0.38 | −6.5 | 0.60 | 7 | 0.60 | −4.2 |
| BOND | 4 | 25.0% | 0.05 | −3.4 | 0.32 | 8 | 0.67 | −1.3 |
| **ALL** | **401** | **37.7%** | **0.79** | **−139.0** | **0.84** | **1,273** | **0.80** | **−424.0** |

**Only genuinely positive signal found: `mega_mutation::crypto`** — peer T2 inventory: n=295,
WR 64.1%, PF 3.16, the sole PASS_ALL_AXES candidate; my live check: n=18 in-window WR 72.2%
PF 3.20, last-30d n=7 WR 57.1% PF 1.58.
**Everything else with n≥100 is at or below break-even.**

---

# 5. VERDICT — **not profitable; the performance is a multiple-testing artifact**

**Multiple-testing, directly:**
- Strategy universe: **361 core families** (`alpha_engine/config.py`) + **285 baby strategies** = 646;
  114 distinct strategies appear in the live 3,500-row window alone.
- At p=0.05, pure chance alone yields **~32 "PF>1.3 winners"** across 646 strategies (18 across the
  361 families). The system's own gate agrees: **69 of 80 audited strategies are OVERFIT_LIKELY (86%)**
  (`live_anti_overfit_audit.json`, 14:22Z), with PBO computed on only 21 observations and the White
  Reality Check **never running** (missing `arch` package).
- **Break-even test on n≥100:** only 4 strategies qualify. Best `rs-breakout-scout` n=133, WR 53.4%,
  PF 1.65, **z = 0.78** (needs 1.96). `luxalgo_confluence` n=1,284, WR 43.0%, PF 1.13, **z = −5.02**
  (significantly *worse* than a coin flip). **Zero strategies pass n≥100 + PF>1.3 + z>1.96.**

**Survivorship, directly:** the only positive-looking cells are small-n (EQUITY 7d n=19 PF 3.63;
ETF 7d n=15 PF 3.21) and they decay to PF 0.84 / 0.72 at 30d. `mega_mutation` is the single
exception that has survived both peer and my independent check — and even it is n≈18–295, not a
certified edge. Meanwhile 2,262 duplicate `inverse_mutations` re-emissions and 129 dedup-key
collisions inflate sample counts independently of any edge.

**The system's own verdicts agree:** "0/9 asset classes money-ready on policy-clean closed picks.
Do not size on Smart Picks / tournament / leaderboard inflated WR" (`live_audit_surface_truth.json`).

**Not verified / limitations:** external market data verifies *prices*, not the system's intrabar
fills; I could not pull workflow logs (admin-only), 180 workflows' last-run status, or MySQL directly.
Where a number came from a peer report it is cited; where from live JSON the key is named.

---

## Files in this folder
- `AUDIT_FINAL.md` — this summary
- `notes/01_actions_health.md` … `notes/05_verdict.md` — per-subtask detail
- `notes/playwright_live_js_report.md` — live browser test (0 JS exceptions, 3 real bugs)
- `notes/evidence/` — `repricing.json` (624 rows), `closed_stats.json`, `wf_last_seen.json`,
  `px_binance_sample.json`, `px_yahoo.json`

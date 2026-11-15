# Elimination Rationale — Why Other Asset Classes and Strategies Were Eliminated

**Worktree:** scratch-hippodraco  
**Date-time:** 2026-11-15T0130Z  
**Core Principle:** Bias toward elimination. Default to NOT trading. The burden of proof is on each class/strategy to demonstrate clean out-of-sample edge after costs.

---

## 1. Asset Classes Eliminated (BLOCKED)

### 1.1 CRYPTO

| Metric | Value |
|--------|-------|
| n_resolved | 3,705 |
| WR | 35.87% |
| PF | 0.9196 |
| Verdict | NOT_READY |
| Source | money_ready_verdict.json (2026-11-15T00:05) |

**Elimination Reasons:**
1. **No OHLCV backfill** — `crypto_ohlcv` holds only ~30 days of 1h bars; need ≥180 days for intrabar replay
2. **Toxic sources** — CRYPTO sources fail training-PF gate
3. **Data integrity** — stale prices / frozen quotes in curated displays; resolver throughput issues
4. **Multiple testing** — ~658 strategies tested; ~33 expected false positives at p=5%
5. **Dashboard inflation** — CRYPTO Smart Picks showed 78.9% WR vs raw DB 39.4% (single-source concentration, 100% alpha_engine)
6. **PF below floor** — PF 0.92 < 1.5 T2 floor; WR 35.9% < 50%

**Block mechanism:** CRYPTO is **NOT** in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (that set contains {FOREX, COMMODITY, FUTURES, BOND}). CRYPTO is blocked **policy/verdict-based**:
- `money_ready_verdict.json`: verdict = NOT_READY (PF 0.92 < 1.5, WR 35.9% < 50%)
- `ml_gatekeeper/gatekeeper.py`: CRYPTO has its own threshold gating at line 735-744

**Verdict:** BLOCKED until OHLCV backfill ≥180d 1h + intrabar replay + source cleanup. Blind unblock vetoed.

### 1.2 FOREX

| Metric | Value |
|--------|-------|
| n_resolved | 612 |
| WR | 32.19% |
| PF | 0.6596 |
| Verdict | NOT_READY |
| Source | money_ready_verdict.json (2026-11-15T00:05) |

**Note:** The figure "PF 0.077, true 14d WR ~5%" cited elsewhere is a **stale 2026-06-08 snapshot** from `money-maker-readyv2/SKILL.md` Layer A, not the current verdict. Current PF is 0.66 (still far below 1.5 T2 floor).

**Elimination Reasons:**
1. **Sub-floor PF** — Clean cohort PF 0.63; current verdict PF 0.66 — still far below 1.5 T2 floor
2. **Spread costs** — Spread ~1–2 pips = ~4bp/side destroys micro-edges; rollover/funding if overnight
3. **Multiple testing** — Many FOREX strategies tested; no DSR ≥ 0.5 survivor
4. **Drift alert** — KS_D = 6.6× critical; do not unblock while drift_alert TRUE
5. **Direction bias** — SHORT-axis 57% WR vs LONG 21% on `ig_contrarian_sentiment`, 36pp spread (from prior analysis, unverifiable from current sources)

**Block mechanism:** FOREX **IS** in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (set contains {FOREX, COMMODITY, FUTURES, BOND}).

**Verdict:** BLOCKED. Mutation-before-kill protocol in progress. Do not unblock while drift_alert TRUE.

### 1.3 COMMODITY / FUTURES

| Metric | COMMODITY | FUTURES |
|--------|-----------|---------|
| n_resolved | 229 | 52 |
| WR | 40.17% | 42.31% |
| PF | 1.0256 | 1.0936 |
| Verdict | WATCH | INSUFFICIENT_DATA |
| Source | money_ready_verdict.json (2026-11-15T00:05) |

**Elimination Reasons:**
1. **No real commodity feed** — COMMODITY generator maps crypto proxies (RNDR→silver, XLM/DOT→oil); labelled COMMODITY rows may have no commodity exposure
2. **No contract specs** — no multiplier, tick value, margin, roll schedule
3. **n too small** — COMMODITY n=229, FUTURES n=52; need ≥100 for T2
4. **FUTURES dead** — 5.9% WR, −96% PnL, zombie tile; real futures hidden under COMMODITY
5. **Blocked asset class** — COMMODITY and FUTURES administratively blocked in `quality_gates.py`

**Block mechanism:** COMMODITY and FUTURES **ARE** in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (set contains {FOREX, COMMODITY, FUTURES, BOND}).

**Historical reference (use with caution):** `cot_positioning` family DSR=1.0000, WR 86.5%, Sharpe +1.377, n=104 — but `multi_asset_cot` PF 21.33 likely one-symbol (CT=F cotton) concentration artifact.

**Verdict:** BLOCKED. Do not blind-unblock FUTURES/COMMODITY by removing blocklists while feeds/mapping/costs are wrong.

**Note:** There is **no COMMODITY-specific MDD override** (MDD ≤ 55%). The `classify()` function applies MDD ≤ 20% for TIER_2 to all classes uniformly.

### 1.4 BOND

| Metric | Value |
|--------|-------|
| n_resolved | 1 |
| WR | 0.0% |
| PF | 0.0 |
| Verdict | INSUFFICIENT_DATA |
| Source | money_ready_verdict.json (2026-11-15T00:05) |

**Elimination Reasons:**
1. **Insufficient n** — n=1; need ≥100 for T2
2. **No FRED data** — `fred_data_fetcher.py` exists but needs `FRED_API_KEY`
3. **Scope unclear** — bond ETFs (model distributions) vs true bonds not decided
4. **Price-only PnL** — Bond ETF PnL ignoring distributions/dividends inflates returns

**Block mechanism:** BOND is in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (set contains {FOREX, COMMODITY, FUTURES, BOND}).

**Verdict:** BLOCKED until FRED unblock + n accumulation + scope decision.

### 1.5 MUTUAL FUNDS

| Metric | Value |
|--------|-------|
| Class id | −1 (dropped by ML gate) |
| Scanner | None |
| NAV data | None |
| Dashboard tile | None |

**Elimination Reasons:**
1. **Not a predicted class** — no registration in `ASSET_CLASS_MAP`, `_CAT_MAP`, `_LOWER_TO_UPPER`
2. **No NAV data source** — NAV struck once daily after close; no pipeline
3. **No scanner/strategy** — `mutual_fund_scanner.py` / `mutual_fund_strategies.py` do not exist
4. **Structurally unsuited** to active prediction (daily NAV, next-NAV fills, 30-day trading limits, expense ratios)
5. **ML gate drops MF** — `ml_gatekeeper/gatekeeper.py` classifies MF as unknown (-1) via `.get(..., -1)` at line 146; `asset_class.py` has no `mutual_fund` in `_CAT_MAP`/`_LOWER_TO_UPPER`

**Verdict:** BLOCKED. MF is an allocation play (buy-and-hold low-cost index funds), not an ML prediction edge. Near 0% probability as a prediction strategy. Probability as low-cost allocation: HIGH (~85–90% over 10-year horizons).

### 1.6 PENNY / MEMECOIN

| Metric | Value |
|--------|-------|
| MEMECOIN PF | 0.50 over 1,869 trades (class-wide quarantined) |
| PENNY | Blocked by Gate 0 |

**Verdict:** BLOCKED. Deep oversold BLOCKED by Gate 0; MEMECOIN class-wide quarantined.

---

## 2. Strategies Eliminated Within Classes

### 2.1 Within EQUITY

| Strategy | Claimed WR | Why Eliminated |
|----------|-----------|----------------|
| `vwap-reversion-scout` | PF 3.74 | n=15 — too small; fragile contributor |
| `gap-and-go-stocks` | +11.7pp | n=1 — single trade, not statistical |
| `rs-breakout-scout` | 81.3% | n=32 — thin; profitable-approach contributor but insufficient n |
| `donchian-stock-breakout` | 78.6% | n=14 — thin |
| `mtf-align-scout` | PF 1.50 | n=19 — below n≥100 floor |
| `connors_rsi2_scanner` | 75.7% | Proven sleeve but different strategy class (mean-reversion pullback vs momentum); kept as secondary |

**Kept:** `eq-mom-lb12-skip0-nl8` (lookback=12, skip=0, n_long=8) — only EQUITY variant to clear T2 gate on cost-adjusted backtest.

### 2.2 Within ETF

| Strategy | Status | Reason |
|----------|--------|--------|
| All 5 ETF strategies | On probation | Zero verified forward trades; n=45 current (at floor) |
| ETF mean reversion (variants 501–600) | Not wired | Target WR 70% but no production wiring |

**Kept:** `etf-sector-rotation` as secondary paper candidate — needs universe expansion to XLF/XLE/XLK to clear n≥150.

### 2.3 Within CRYPTO

| Strategy | Claimed | Why Eliminated |
|----------|---------|----------------|
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 100% WR, n=27 | n too small; intrabar replay needed |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 100% WR, n=25 | n too small; intrabar replay needed |
| `st_fear_greed_contrarian` | 94% WR | Promote to HC gate per master plan but no clean OOS n≥100 |
| `multi_asset_cot` | PF 21.33, WR 88.2%, n=144 | Likely one-symbol (CT=F cotton) concentration artifact |

**Verdict:** All CRYPTO strategies blocked until OHLCV backfill + intrabar replay.

### 2.4 Within FOREX

| Strategy | Claimed | Why Eliminated |
|----------|---------|----------------|
| `ig_contrarian_sentiment` | SHORT 57% vs LONG 21% | 36pp spread but no DSR ≥ 0.5 survivor |
| `forex_carry_momentum` | — | Blocked in `quality_gates.py` |
| `MomentumEMA` | — | Blocked in `quality_gates.py` |

**Verdict:** All FOREX strategies blocked; mutation-before-kill in progress.

---

## 3. Multiple-Testing Elimination

Across all classes, ~658 strategies were tested. At p=5%, ~33 strategies would appear "significant" by chance. The backtest found:

- **4 of 27 equity combos raw-passed T2** — expected ~1.4 false passes by chance
- **Cannot claim statistical significance** until forward-tested on unseen data

**Elimination Rule:** Any strategy that does not clear T2 on forward out-of-sample data (n≥100, PF≥1.5, WR≥50%, MDD≤20%, beats benchmark) is eliminated, not "given more time."

---

## 4. Do-Not-Adopt List (From Peer Reviews)

| Item | Reason |
|------|--------|
| Mass DELETE of ghost rows | Destructive; mark/quarantine instead |
| Mass UPDATE TIME_EXIT→LOST with pnl_pct=0.0 | Fabricates outcomes |
| Blind unblock of FUTURES/COMMODITY | No real feed/mapping/costs |
| ML confidence inversion without retrain | Data/leakage problems, not model math |
| Placeholder MF scanner emitting empty signals | Not production-ready |
| Trust dashboard headline WR/PF | Inflated; raw DB shows different numbers |
| Trust AI tournament leaderboard WR | 43–89 resolved, wide CIs, ~47% still OPEN |
| Trust "300 picks / 58.4% WR" claims | Merged model_ids; small-n forward test |

---

## 5. Final Elimination Summary

| Asset Class | Eliminated? | Primary Reason | Path to Unblock |
|-------------|-------------|---------------|-----------------|
| EQUITY | NO (paper candidate) | — | Forward-test T2-clearing variant |
| ETF | NO (paper candidate, secondary) | n=45 at floor | Expand universe to XLF/XLE/XLK |
| CRYPTO | YES | No OHLCV backfill; intrabar truth gap | Backfill ≥180d 1h; rerun intrabar replay |
| FOREX | YES | Sub-floor PF; drift_alert | Mutation-before-kill; spread-aware costs |
| COMMODITY / FUTURES | YES | No real feed; crypto-proxy mapping | Real feed + contract specs + costs |
| BOND | YES | n=1; no FRED data | Set FRED_API_KEY; accumulate n |
| MUTUAL FUNDS | YES | Not a class; no infrastructure | Register class + NAV source + scanner (allocation only) |
| PENNY / MEMECOIN | YES | Blocked by Gate 0; class-wide quarantined | Do not revisit |

---

# Pick Justification — Which Asset Classes Get Picks and Why

**Worktree:** scratch-hippodraco  
**Date-time:** 2026-11-15T0130Z  
**Status:** PAPER ONLY — no live picks deployed to `/audit`. All picks below are candidates for forward-test tracking only.

---

## 1. Executive Summary

| Asset Class | Pick Status | # of Picks | Basis |
|-------------|-------------|------------|-------|
| EQUITY | **PAPER CANDIDATE** | Top-8 by 12-month momentum | Only class with T2-clearing variant in cost-adjusted backtest |
| ETF | PAPER CANDIDATE (secondary) | Top-4 to 6 by sector momentum | Cleanest OOS profile in prior analysis; n=45 current (at floor) |
| CRYPTO | BLOCKED | 0 | Needs OHLCV backfill ≥180d 1h; intrabar truth drops WR 52%→43% |
| FOREX | BLOCKED | 0 | Clean PF 0.66; mutation-before-kill; drift_alert TRUE |
| COMMODITY / FUTURES | BLOCKED | 0 | No real feed; crypto-proxy mapping must be fixed |
| BOND | BLOCKED | 0 | n=1; FRED unblock needed |
| MUTUAL FUNDS | BLOCKED | 0 | Not a predicted class; class id −1 |

---

## 2. EQUITY Pick Justification

### 2.1 Why EQUITY gets picks

EQUITY is the only asset class in this system with:
- A pre-registered SPY total-return benchmark test path in the money-maker-ready skill framework
- A proven sleeve: `connors_rsi2_scanner` (listed in ALL_STRATEGIES.md at 75.7% WR; p-value and Sharpe claims unverifiable from current sources)
- Positive cost-margin signals (mean +0.323% per trade in prior analysis — unverifiable from current sources)
- n=250 current resolved picks (money_ready_verdict 2026-11-15T00:05)
- One T2-clearing variant in cost-adjusted walk-forward backtest (lookback=12, skip=0, n_long=8)

### 2.2 The Pick

**Strategy:** `eq-mom-lb12-skip0-nl8`  
**Type:** Paper-only candidate for forward testing  
**Universe:** 30 large-cap US equities (AAPL, MSFT, GOOJK, AMZN, META, NVDA, TSLA, AVGO, ORCL, JPM, BAC, WFC, GS, MS, BLK, JNJ, PFE, UNH, ABBV, LLY, WMT, HD, COST, KO, MCD, XOM, CVX, PG, PEP, TMO)  
**Rule:** Monthly rebalance; hold top 8 by 12-month momentum (skip 0 months); equal weight  
**Entry:** Next month-open after month-end rank  
**Exit:** Next month-end re-rank; sell fallouts, buy entrants  
**Sizing:** Equal weight (12.5% each); max 2.5% account per trade (¼ Kelly)  
**Cost model:** 20 bps round-trip per rebalance (hardcoded in backtest; transaction_costs.json lists EQUITY at 10 bps)  
**Benchmark:** SPY total return (dividends reinvested)  
**Status:** PAPER_TRACKING — not ACTIVE, not rendered on `/audit` as actionable picks

### 2.3 Why This Strategy Was Chosen Over Other EQUITY Strategies

| Strategy | Why Not Selected |
|----------|-----------------|
| `connors_rsi2_scanner` | Proven sleeve (75.7% WR listed in ALL_STRATEGIES.md) but this is a different strategy class (mean-reversion pullback vs momentum); kept as secondary candidate. p-value/Sharpe claims unverifiable from current sources. |
| `stocks_ema_golden_cross` | Institutional 50/200 crossover; no clean OOS n≥100 in this system |
| `donchian-stock-breakout` | WR 78.6% but n=14 — too thin |
| `rs-breakout-scout` | WR 81.3% but n=32 — thin; profitable-approach contributor (n=110, PF 1.26) |
| `vwap-reversion-scout` | Profitable-approach contributor (n=15, PF 3.74) but n too small for standalone |

The momentum variant was chosen because it **cleared the T2 gate** on cost-adjusted backtest (PF 2.62, WR 62.79%, MDD 17.37%, n=129) and beats SPY on return (1021% vs 359%), Sharpe (1.27 vs 0.95), and MDD (17.37% vs 23.93%).

### 2.3 Why Not Live Yet

- Historical backtest results are **hypothesis-grade** — after Bonferroni correction (27 combos tested, ~1.4 expected false T2 passes at α=0.05), we cannot claim statistical significance.
- Must clear T2 again on **forward out-of-sample data** (≥6 months, ≥100 trades).
- MDD is the binding constraint (17.37% is close to the 20% cap).
- Current money_ready_verdict shows EQUITY PF=0.94 (NOT_READY — below PF 1.5 gate).

---

## 3. ETF Pick Justification

### 3.1 Why ETF Gets Picks (Secondary)

ETF has the cleanest OOS profile in prior analysis:
- WF consistency 100%, OOS WR 75%, decay +23% (improving — from prior analysis, unverifiable from current sources)
- Profitable approach backtest: ETF n=120, PF 1.21 (+26.5pp) — **stale prior analysis**

### 3.2 Blocker

n is at floor (n=45 per current money_ready_verdict 2026-11-15T00:05). Universe must be expanded to XLF/XLE/XLK + more to reach n ≥ 100 minimum, n ≥ 150 for OOS_READY promotion. Current PF=0.0216 is critically low vs 1.5 T2 floor.

### 3.3 The Pick (Secondary, Lower Priority)

**Strategy:** `etf-sector-rotation`  
**Type:** Paper-only candidate  
**Universe:** SPY, QQQ, IWM, XLF, XLE, XLK, XLV, XLI, XLB, XLP, XLU, XLRE, XLC, EFA, EEM, AGG, TLT (expand to ≥150)  
**Rule:** Monthly rebalance; hold top 4–6 by 12-month momentum (skip 1 month); equal weight  
**Cost model:** ~15 bps round-trip (tighter spreads than single stocks)  
**Benchmark:** SPY total return  
**Status:** PAPER_TRACKING (secondary, lower priority than EQUITY)

---

## 4. Why No Picks for Other Classes

| Class | Primary Reason |
|-------|---------------|
| CRYPTO | No OHLCV backfill ≥180d 1h; intrabar replay drops WR 52%→43%; toxic sources excluded by gate; current PF 0.92 < 1.5 |
| FOREX | Clean PF 0.66; true clean WR ~32%; drift_alert TRUE (KS_D = 6.6× critical) |
| COMMODITY / FUTURES | No real feed; crypto-proxy mapping (RNDR→silver, XLM→oil); n too small (COMMODITY n=229, FUTURES n=52) |
| BOND | n=1; FRED API key not set; scanner produces 0 picks |
| MUTUAL FUNDS | Not a class; class id −1; no NAV data; no scanner; no dashboard tile |
| PENNY / MEMECOIN | Blocked by Gate 0; MEMECOIN PF 0.50 over 1,869 trades (class-wide quarantined) |

---

## 5. Pre-Registration Requirements (Before Any Pick Is Tracked)

Before month 1 of forward testing, the following must be committed:

| Field | Value |
|-------|-------|
| Strategy name | `eq-mom-lb12-skip0-nl8` |
| Asset class | EQUITY |
| Benchmark | SPY total return |
| Entry rule | Top-8 by 12-month momentum, monthly rebalance, long-only |
| Cost per trade | 20 bps round-trip |
| Position sizing | Equal weight; max 2.5% account per trade |
| Start date | First trading day of next month |
| Planned duration | ≥ 6 months (n ≥ 6 trades minimum to evaluate) |
| T2 gate targets | PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, n ≥ 100 |
| Kill criteria | See forward-test protocol (single month −10%, MDD >25%, etc.) |

**Save as:** `reports/forward_test_eq-mom-lb12-skip0-nl8_preregistration_2026-11.md`  
**Do not change during forward test.** Changes = new test, reset the clock.

---

## 6. How Picks Would Flow to `/audit` (Only After T2 Certification)

If and only if the strategy clears T2 on forward data:

1. Paper-only forward test ≥6 months / ≥100 trades
2. Clear T2 gate: PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, n ≥ 100, beats SPY total return — all post-cost
3. Wire into `tools/active_picks_sync.py` → resolver → `trading_picks`
4. Render on `/audit/active_picks` and `/audit/closed_picks` labeled `PAPER` until live-certified
5. Exclude from WR/PF aggregates until live-certified (prevents fake-0%-PnL/zombie pollution)

**Until step 3 passes, no picks are rendered on `/audit` as actionable signals.**

---

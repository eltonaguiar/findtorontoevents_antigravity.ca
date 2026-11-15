# Algorithm Specification — BOND

**Worktree:** scratch-hippodraco  
**Asset Class:** BOND  
**Status:** BLOCKED  
**T2 Gate Status:** Not cleared — n=1, thin, far below floor

---

## 1. Current Money-Ready Verdict (2026-11-15T00:05)

| Metric | Value |
|--------|-------|
| n_resolved | 1 |
| WR | 0.0% |
| PF | 0.0 |
| Verdict | INSUFFICIENT_DATA |

---

## 2. Why BLOCKED

BOND has extremely sparse data (n=1). Historical PF ~1.72, WR ~56% looks promising but n is far below the 100-floor for any statistical validity.

## 3. Blockers (must be resolved before unblocking)

| Blocker | Detail | Required Action |
|---------|--------|-----------------|
| Insufficient n | n=1; need ≥100 for T2 | Set `FRED_API_KEY` in repo secrets to unblock BOND scanner |
| No FRED data | `fred_data_fetcher.py` exists but needs `FRED_API_KEY` | Configure API key; wire scanner |
| Bond ETF vs true bond | Unclear scope: price-only PnL ignoring distributions | Decide: bond ETFs (model distributions) or true bonds |
| Price-only PnL | Bond ETF PnL ignoring distributions/dividends | Model distributions and expense ratios |

## 4. Block Mechanism

BOND is in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (set contains {FOREX, COMMODITY, FUTURES, BOND}).

## 5. Hypothetical Specification (for when unblocked)

**Strategy:** `bond-duration-rotation` or `bond-yield-curve`  
**Universe:** TLT, IEF, AGG, HYG, LQD (bond ETFs) or true bond futures  
**Cost model:** 5 bps round-trip (bond ETF commissions + spreads)  
**Benchmark:** TLT/IEF/AGG total return  
**Data frequency:** EOD/NAV (not intraday TP/SL — bond ETFs trade daily)  
**T2 gate:** PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, n ≥ 100  

**Probability of profitability:** LOW — until n accumulates and FRED data is wired.

---

## 6. Do Not

- Do not claim "bond edge" until intrabar/daily methodology is explicit and n ≥ 100.
- Do not ignore expense ratios and distributions for bond ETFs.
- Do not use price-only PnL for multi-day hold strategies.

---

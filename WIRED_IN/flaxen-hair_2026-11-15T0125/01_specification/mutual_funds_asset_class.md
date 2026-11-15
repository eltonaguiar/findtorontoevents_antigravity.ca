# Mutual Funds — Asset Class Coverage Audit

**WIRED_IN Documentation Folder**
**Asset Class:** Mutual Funds (open-end index funds)
**Status:** ZERO COVERAGE — Not a prediction class, equity risk premium / allocation only
**Date:** 2026-11-15
**Repository:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/flaxen-hair/`

---

## Executive Summary

Mutual funds have **zero production coverage** in this codebase. There are no mutual fund algorithms, no mutual fund data source, no mutual fund asset-class registration, no mutual fund scanner, and no mutual fund strategies. Mutual funds are **not a prediction class** — they are an allocation vehicle that captures equity risk premium and bond carry at minimal cost. The correct posture is to hold low-cost index mutual funds as core allocation, not to build mutual fund prediction infrastructure.

This document records the audit findings, the specific gaps in every layer of the stack, the proposed infrastructure IF mutual fund support were ever added (as allocation-only, never prediction), the solid pick criteria, the starter universe, and the final recommendation.

---

## 1. Zero Coverage — Verified Across the Entire Codebase

### 1.1 Search Results for Mutual Fund References

A full-repo search for `mutual`, `mutual_fund`, and the six common mutual fund tickers (VFIAX, VTSAX, FXAIX, VBTLX, VGSLX, VWELX) returned matches only in:

| Category | Files Matching | Nature of Match |
|----------|---------------|-----------------|
| Marketing/blog HTML | `investments/index.html`, `investments/all-dashboards.html`, `blog/blog*.html` | Legacy "findmutualfunds" static pages, category toggles, fee tables — not trading system code |
| Planning/docs | `2026-11-15_AM_profitability-plan/**`, `final_v*/**`, `quick_wins/05_mutual_funds/**` | Proposals and audit notes recommending de-advertise / NOT_BUILT |
| Spec only (unimplemented) | `multi_asset/portfolio_defs.py:677-720` | Universe definition + `tactical_fund_rotation` strategy spec marked `backtest_status: "research"` |
| Unrelated indicator math | `alpha_engine/crypto_strategies.py`, `alpha_engine/indicators.py`, `alpha_engine/features/flow.py` | `mf_` = "money flow" (Chaikin Money Flow), not mutual funds |
| Calendar anomaly notes | `alpha_engine/calendar_anomalies.py`, `alpha_engine/equity_strategies.py` | Mentions mutual funds as the *mechanism* behind turn-of-month flows, not an asset class |

**No file in `alpha_engine/`, `ml_gatekeeper/`, `audit_trail/`, `audit_dashboard/`, `multi_asset/`, `tools/`, or `tests/` implements a live mutual fund class, scanner, strategy, data source, or NAV cache.**

### 1.2 Asset Class Registration — MISSING

**File:** `alpha_engine/asset_class.py`

The canonical asset-class normalization module defines frozensets for `FOREX_CODES`, `BOND_SYMBOLS`, `ETF_SYMBOLS`, `EQUITY_SYMBOLS`, `COMMODITY_SYMBOLS`, plus `_CAT_MAP`, `_LOWER_TO_UPPER`, and `asset_class_from_symbol()`. None of these include mutual funds:

- No `MUTUAL_FUND_SYMBOLS` frozenset exists.
- No `"mutual_fund"` key in `_CAT_MAP` (line 102).
- No `"mutual_fund": "MUTUAL_FUND"` entry in `_LOWER_TO_UPPER` (line 111).
- No `is_mutual_fund()` helper function.
- `asset_class_from_symbol()` returns one of: `crypto, forex, futures, bond, etf, equity, unknown` — mutual fund tickers like `VFIAX`, `VTSAX`, `FXAIX` fall through all known-symbol checks and hit the default fallback at line 260, returning `"equity"`.

**Consequence:** Any mutual fund ticker entering the pipeline is silently misclassified as `equity`, subjecting it to intraday TP/SL rules that are semantically wrong for NAV-only instruments that settle T+1 and trade only at the 16:00 ET close.

### 1.3 ML Gatekeeper — MISSING

**File:** `ml_gatekeeper/gatekeeper.py` (line 73)

```python
ASSET_CLASS_MAP = {"CRYPTO": 0, "FOREX": 1, "EQUITY": 2, "COMMODITY": 3, "ETF": 4, "BOND": 5, "FUTURES": 6}
```

- No `"MUTUAL_FUND": 7` entry.
- `extract_features()` (line 146) does: `asset_class = ASSET_CLASS_MAP.get((pick.get("asset_class") or "").upper(), -1)`. Any mutual fund pick gets class id `-1` (unknown), dropped by the ML gate.
- No mutual fund-specific gating, no crypto-style confidence inversion, no mutual fund feature encoding.

### 1.4 Dashboard Generator — MISSING

**File:** `audit_trail/dashboard_generator.py`

- `_CANONICAL` (line 6027): `{"CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND"}` — 6 classes, no `MUTUAL_FUND`.
- `_CANONICAL` (line 6200): `["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"]` — 7 classes, no `MUTUAL_FUND`.
- `_PER_ASSET_CLASSES` (line 6763): `("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "FUTURES", "BOND", "ETF")` — no `MUTUAL_FUND` tile/bucket, no dashboard grouping.

### 1.5 Scanners and Strategies — MISSING

**Directory:** `alpha_engine/`

Strategy inventory includes `bond_*`, `etf_*`, `equity_*`, `forex_*`, `crypto_*`, `commodities_*`, `futures_*` scanners/strategies. **No `mutual_fund_*` scanner or strategy file exists** in this worktree.

**Directory:** `multi_asset/`

Contains `portfolio_defs.py` which defines a `mutual_fund` universe (14 funds) and a `tactical_fund_rotation` strategy spec (lines 677-719). However:
- `backtest_status: "research"` — not production.
- No live module imports `portfolio_defs` (confirmed by audit: "no live module imports portfolio_defs").
- It is a spec/universe definition only, not a working strategy, scanner, or emitter.

### 1.6 Data Sources — MISSING

Searched for:
- `audit_dashboard/data/mutual_fund_nav_cache/` — **does not exist** in this worktree.
- `audit_dashboard/data/mf_backtest_cache/` — **does not exist** in this worktree.
- Any CSV files with mutual fund NAV data — **none found**.
- `alpha_engine/data/mutual_fund_metadata.csv` — **does not exist** in this worktree.
- `alpha_engine/mutual_fund_ranker.py` — **does not exist** in this worktree.
- `audit_dashboard/data/mutut_fund_rankings.json` — **does not exist** in this worktree.

Note: Per multiple peer-audit documents, an untracked research prototype (`mutual_fund_ranker.py`, `mutual_fund_metadata.csv`, `mutual_fund_nav_cache/`, `mutut_fund_rankings.json`, `reports/mutual_fund_results.json`) exists only as untracked files in the main checkout outside this worktree. None are committed to `origin/main`, none are wired into production, and all carry known defects (misspelled output filename `mutut`, no coverage gate, unverified NAV freshness).

### 1.7 Picks — ZERO

- `live_picks.db` / `dashboard_data.json`: zero mutual fund asset class, zero mutual fund rows (active or closed).
- Multiple peer audits independently confirm: "no mutual fund class," "no mutual fund rows," "0 active / 0 closed MF picks," "mutual-fund prediction is vaporware on the live page."

---

## 2. Mutual Funds Are NOT a Prediction Class

Mutual funds are **equity risk premium** (and bond carry) captured at low cost through passive indexing. They are:

- **NAV-only instruments:** Priced once daily at 16:00 ET, settle T+1, no intraday execution, no short selling.
- **Not suitable for TP/SL intraday contracts:** The prediction system's `current_price`/`entry_price`/`take_profit`/`stop_loss` intraday mark contract does not apply to once-daily NAV funds.
- **Beta, not alpha:** Expected return is market beta (equity: ~7–9% nominal; bonds: ~4–5% carry) minus expense ratio. Not a trading edge.
- **Cost discipline is the edge:** Low expense ratio, no load, no 12b-1, low turnover, high AUM — these are the only controllable levers.

The prediction system has not demonstrated any edge on mutual funds, and the architecture (intraday marks, same-day resolution, TP/SL exits) is fundamentally mismatched to NAV-only funds.

---

## 3. If Building Mutual Fund Infrastructure (Allocation-Only, Not Prediction)

If the project ever decides to build mutual fund support, it must be **allocation-only** (NAV-based monthly rebalance, no picks, no TP/SL, no intraday marks). The following files would need to be created or modified.

### 3.1 Files to Create

| Path | Purpose |
|------|---------|
| `alpha_engine/mutual_fund_ranker.py` | Weekly NAV-based ranker; reads NAV cache, applies pick criteria, outputs ranked fund list (no TP/SL, no picks) |
| `alpha_engine/data/mutual_fund_metadata.csv` | Fund metadata: ticker, name, expense ratio, load, 12b-1, min investment, AUM, turnover, inception date, category |
| `audit_dashboard/data/mutual_fund_nav_cache/` | Daily NAV CSV cache keyed by ticker (e.g. `VFIAX.csv`) with `nav_through` freshness timestamp |
| `audit_dashboard/data/mf_backtest_cache/` | Backtest result cache for NAV-based walk-forward |
| `audit_dashboard/data/mutual_fund_rankings.json` | Ranker output (fix the `mutut` typo from the untracked prototype) |
| `tools/mutual_fund_nav_fetcher.py` | Daily NAV fetch job (yfinance or similar), writes to NAV cache |
| `tests/test_mutual_fund_no_prices.py` | Invariant test: mutual fund picks must never be assigned intraday TP/SL |
| `tests/test_asset_class_parity.py` | Pin `asset_class_from_symbol("VFIAX") == "mutual_fund"`, not `"equity"` |

### 3.2 Files to Modify

| Path | Change |
|------|--------|
| `alpha_engine/asset_class.py` | Add `MUTUAL_FUND_SYMBOLS` frozenset (starter universe), add `"mutual_fund"` to `_CAT_MAP` and `_LOWER_TO_UPPER`, add `is_mutual_fund()` helper, make `asset_class_from_symbol()` return `"mutual_fund"` before the equity fallback |
| `ml_gatekeeper/gatekeeper.py` | Add `"MUTUAL_FUND": 7` to `ASSET_CLASS_MAP`; add mutual fund handling in `extract_features()` (no crypto inversion; NAV-only semantics) |
| `audit_trail/dashboard_generator.py` | Add `"MUTUAL_FUND"` to `_CANONICAL` sets and `_PER_ASSET_CLASSES` tuple; add dashboard tile/bucket |
| `multi_asset/portfolio_defs.py` | Change `tactical_fund_rotation` from `"backtest_status": "research"` to `"RESEARCH_ONLY"` with `"asset_classes": []` or remove the mutual fund advertisement to avoid implying a live class |
| `alpha_engine/mysql_trading_sync.py` | Add `"mutual_fund": "MUTUAL_FUND"` to `_CATEGORY_CANONICAL_MAP` if DB category aliases are used |

### 3.3 Proposed Mutual Fund Strategies (NAV-Based Monthly Rebalance)

These are **allocation strategies**, not prediction strategies. They rebalance at next-NAV close, monthly.

| Strategy | Description | Rebalance | Universe |
|----------|-------------|-----------|----------|
| `mutual_fund_core_hold` | Buy-and-hold low-cost broad index funds; rebalance to target weights quarterly or by drift bands | Quarterly / bands | VFIAX, VTSAX, FXAIX, VBTLX, VTIAX, VGSLX, VWELX |
| `mutual_fund_dual_momentum` | Rank core funds by 12M momentum; hold top 1-2; move to bond fund (VBTLX) when momentum negative | Monthly | VFIAX, VTSAX, FXAIX, VBTLX |
| `mutual_fund_tactical_rotation` | Rank by 3M momentum + 1M reversal; top 3 equal weight; max 33% per fund | Monthly (21 days) | VTSAX, VBTLX, VTIAX, VGSLX, VWELX |

All strategies must:
- Execute at next NAV close (16:00 ET), T+1 settlement.
- Never emit intraday TP/SL marks.
- Respect minimum holding periods (e.g., 30 days) to avoid short-term trading fees.
- Apply expense ratio drag in backtests (net-of-fee only).

### 3.4 Proposed Mutual Fund Ranker

A weekly NAV-based ranker that scores funds on the pick criteria (§5) and outputs a ranked list. It must:
- Read from `audit_dashboard/data/mutual_fund_nav_cache/`.
- Apply a coverage gate: exit non-zero if NAV coverage < threshold (e.g., 80% of universe has NAV ≤ 24h old).
- Never emit pick-shaped rows with TP/SL/direction. Output is a ranked allocation list only.
- Fix the `mutut` filename typo from the untracked prototype (`mutut_fund_rankings.json` → `mutual_fund_rankings.json`).

### 3.5 Proposed COT/NAV Cache

| File | Format | Contents |
|------|--------|----------|
| `audit_dashboard/data/mutual_fund_nav_cache/<TICKER>.csv` | CSV | Date, NAV, daily_return, nav_fetched_at |
| `audit_dashboard/data/mutual_fund_nav_cache/manifest.json` | JSON | Ticker → {nav_through, coverage_pct, last_fetch, source} |

Freshness requirement: `nav_through` ≤ 24h old. If any fund in the universe is stale > 24h, the ranker exits non-zero (coverage gate).

---

## 4. Solid Pick Criteria for Mutual Funds (If Building)

A mutual fund passes the pick gate only if ALL criteria are met:

| # | Criterion | Threshold | Rationale |
|---|-----------|-----------|-----------|
| 1 | Expense ratio | ≤ 0.20% | Cost drag directly reduces net returns |
| 2 | Load fees | None (0%) | Front-end/back-end loads are pure drag |
| 3 | 12b-1 fees | None (0%) | Distribution fees are pure drag |
| 4 | Minimum investment | ≤ $1,000 | Accessibility for small capital |
| 5 | AUM | ≥ $1B | Liquidity and closure risk |
| 6 | Turnover | ≤ 20% | High turnover = tax drag + trading costs |
| 7 | Tracking error | ≤ 0.25% (index funds) | Closely tracks stated benchmark |
| 8 | Track record | ≥ 10 years | Sufficient history across regimes |
| 9 | NAV freshness | ≤ 24h | Stale NAV = cannot trade at known price |

Funds failing any criterion are excluded from the universe.

---

## 5. Starter Mutual Fund Universe

| Ticker | Name | Class | Expense Ratio | Min Investment | AUM (approx.) | Role |
|--------|------|-------|--------------|----------------|---------------|------|
| VFIAX | Vanguard 500 Index Admiral | Large Blend | 0.05% | $3,000 | $400B+ | US large-cap core |
| VTSAX | Vanguard Total Stock Market Admiral | Large Blend | 0.04% | $3,000 | $1.3T+ | Total US equity |
| FXAIX | Fidelity 500 Index Premium | Large Blend | 0.015% | $0 | $170B+ | US large-cap core ($0 min) |
| VBTLX | Vanguard Total Bond Market Admiral | Intermediate Bond | 0.05% | $3,000 | $300B+ | US bond core |
| VGSLX | Vanguard Real Estate Index Admiral | Real Estate | 0.12% | $3,000 | $50B+ | REIT exposure |
| VTIAX | Vanguard Total Intl Stock Admiral | Foreign Large Blend | 0.11% | $3,000 | $350B+ | International equity |
| VWELX | Vanguard Wellington Admiral | Allocation (50/70% equity) | 0.25% | $3,000 | $100B+ | Balanced (60/40-style) |

Note: Vanguard Admiral shares (VFIAX, VTSAX, VBTLX, VTIAX, VGSLX, VWELX) carry a $3,000 minimum. For lowest-capital deployment, prefer Fidelity $0-minimum equivalents (FXAIX, FSKAX, SWPPX, SWTSX, FXNAX) where available.

---

## 6. Recommendation

**Do NOT build mutual fund prediction.** Do not add `MUTUAL_FUND` to the canonical asset class taxonomy, do not build a mutual fund scanner, do not build mutual fund strategies that emit picks with TP/SL marks, and do not wire mutual funds into the ML gatekeeper as a live pick class.

**Instead:** Hold low-cost index mutual funds (or their ETF equivalents) as core allocation — buy-and-hold or simple periodic rebalance. This captures equity risk premium and bond carry at minimal cost, which is the highest-probability lower-risk path for this system. The research system should continue as a paper-pilot satellite under strict gates, but mutual funds should remain outside the prediction pipeline entirely.

If mutual fund infrastructure is ever desired for research allocation testing, it must be built as NAV-based monthly rebalance (allocation-only), with a coverage gate, no intraday marks, and explicit `NOT_BUILT` / `RESEARCH_ONLY` labeling so it is never mistaken for a proven prediction class.

---

## 7. Evidence Index

| Finding | Evidence |
|---------|----------|
| No `MUTUAL_FUND_SYMBOLS` in asset_class.py | `alpha_engine/asset_class.py` lines 22-69, 101-120, 130-260 — no mutual fund frozenset, `_CAT_MAP` entry, `_LOWER_TO_UPPER` entry, or `is_mutual_fund()` |
| Fund tickers fall back to equity | `asset_class.py` line 260 default fallback returns `"equity"` for unknown symbols |
| No `MUTUAL_FUND` in ASSET_CLASS_MAP | `gatekeeper.py` line 73 — map has 6 entries (CRYPTO, FOREX, EQUITY, COMMODITY, ETF, BOND, FUTURES), no MUTUAL_FUND |
| No MUTUAL_FUND in dashboard canonical classes | `dashboard_generator.py` lines 6027, 6200, 6763 — `_CANONICAL` and `_PER_ASSET_CLASSES` omit MUTUAL_FUND |
| No mutual fund scanner/strategy files | `alpha_engine/` and `multi_asset/` — no `mutual_fund_*` files exist |
| No NAV cache or metadata files | Glob results: `audit_dashboard/data/mutual_fund_nav_cache/`, `mf_backtest_cache/`, `alpha_engine/data/mutual_fund_metadata.csv`, `mutual_fund_ranker.py` all absent |
| Zero mutual fund picks | Peer audits: `live_picks.db` has no mutual fund class/rows; `dashboard_data.json` has 0 MF picks |
| `tactical_fund_rotation` is research-only | `portfolio_defs.py` lines 382-408 — `backtest_status: "research"`, no live importer |
| Mutual funds = equity risk premium | Multiple plan docs: MF is "allocation sleeve," "not prediction alpha," "market beta + cost discipline" |

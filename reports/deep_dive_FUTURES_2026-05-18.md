# Deep-Dive: FUTURES Asset Class
**Date:** 2026-05-18
**Trigger:** PF=0.064, WR=3.0%, n=203 — exceeds CLAUDE.md deep-dive threshold (PF<1, WR<30%)
**Status:** RESOLVED — source globally blocked; historical data only

---

## TL;DR

FUTURES class has PF=0.064 / WR=3.0% / n=203 / total_pnl=−5.37% summed raw. **100% of FUTURES closed picks come from `multi_asset_copytrader`**, which was globally added to `BLOCKED_SOURCE_SYSTEMS` (quality_gates.py:2032) in a prior session. No new FUTURES picks are being generated. This is a historical data artifact surfaced by the hourly audit PR #1234.

---

## Per-Source Autopsy

| Source | n | WR | PF | Total PnL | Status |
|--------|---|----|----|-----------|--------|
| multi_asset_copytrader | 203 | 3.0% | 0.064 | −5.37% raw | **GLOBALLY BLOCKED** (quality_gates.py:2032) |

Only one source ever emitted FUTURES-class picks. All symbols are commodity futures mis-classified at asset_class=FUTURES rather than COMMODITY.

---

## Symbol Breakdown

| Symbol | n | WR | Notes |
|--------|---|-----|-------|
| CT=F (Cotton) | 59 | 3% | |
| SI=F (Silver) | 45 | 2% | |
| HG=F (Copper) | 33 | 0% | |
| KC=F (Coffee) | 22 | 5% | |
| PL=F (Platinum) | 19 | 0% | |
| ZW=F (Wheat) | 15 | 13% | |
| GC=F (Gold) | 10 | 0% | |

All are commodity futures. None are financial futures (equity index, rates, FX). The `multi_asset_copytrader` strategy consistently mis-labeled COMMODITY futures as `asset_class=FUTURES`.

---

## Root Cause

`multi_asset_copytrader` emits futures contracts (CT=F, SI=F, etc.) with `asset_class=FUTURES`. These should be `COMMODITY`. The strategy itself had catastrophic performance (WR=3%, PF=0.06) on these symbols — likely due to trend-following logic applied to mean-reverting commodity spot-vs-futures dynamics.

The global block at `BLOCKED_SOURCE_SYSTEMS` in quality_gates.py prevents any new picks from this source. The 45 current active picks from `multi_asset_copytrader` are pre-block entries that are aging out.

---

## PR #1234 Clarification

PR #1234 (hourly audit 05Z) reports "P1 FUTURES catastrophic — cta_replicator primary contributor (NG=F, CL=F)." This is **incorrect in two ways**:

1. `cta_replicator` does NOT emit FUTURES-class picks — its NG=F and CL=F picks are classified as `COMMODITY` (confirmed via raw data audit). See separate COMMODITY deep-dive.
2. The actual FUTURES-class source is `multi_asset_copytrader` (n=203, all FUTURES), which is already globally blocked.

The PR's "FUTURES catastrophic" finding is historically accurate but the source attribution and implied action are incorrect.

---

## 30/60/90 Day Rescue Plan

**No rescue needed.** The source is blocked; FUTURES picks will stop appearing in the dashboard as the 45 active picks reach their TP/SL or expire. Timeline: ~2-4 weeks for full flush assuming normal resolution rates.

**Classification fix opportunity:** If `multi_asset_copytrader` is ever re-evaluated for reinstatement, the `asset_class` field on commodity futures (CT=F, SI=F, etc.) should be corrected to `COMMODITY` to avoid double-counting those symbols in both FUTURES and COMMODITY reporting.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| New picks from multi_asset_copytrader | LOW | HIGH | Global block in BLOCKED_SOURCE_SYSTEMS |
| Existing active picks resolve as losses | HIGH | LOW | Already losing; small position sizes |
| PR #1234 triggers unnecessary investigation | LOW | LOW | This doc clarifies |

---

## Acceptance Criteria

- [x] Source identified: multi_asset_copytrader (sole FUTURES emitter)
- [x] Source status confirmed: globally blocked (quality_gates.py:2032)
- [x] No new action required beyond documentation
- [ ] Active picks from multi_asset_copytrader flush naturally (ETA: 2-4 weeks)

---

## References
- `audit_dashboard/data/dashboard_data.json` — FUTURES health
- `audit_dashboard/data/pf_registry.json` — by_asset_class_strategy FUTURES rows
- `alpha_engine/data/closed_picks.json` — 203 FUTURES closed picks (all multi_asset_copytrader)
- `audit_trail/quality_gates.py:2032` — multi_asset_copytrader global block
- PR #1234 — hourly audit surfacing this finding

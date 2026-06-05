# HEARTBEAT - High Conviction Filter & Pick Tracking Monitor

Run this checklist every ~10 minutes (via heartbeat or manual trigger):

## 1. Check Redis Bus for Action Items
```bash
tail -20 .kilo/worktrees/aloud-linen/alpha_engine/data/bus_communications.log
```
**Look for:**
- HC_FILTER_ROOT_CAUSE_ANALYSIS (our analysis)
- Bitget Scraper HTTP 403 errors (action needed)
- STRATEGY_SYNC updates

## 2. Active Picks Analysis (Current State)

### Issue: NO trust_tier field in active_picks.json!
- Active picks: 111 total
- Has forward_wr data: 49/111 (44.1%)
- **CRITICAL: trust_tier field is MISSING** - cannot filter by PROVEN/SANDBOX

### What SHOULD be in active picks:
- trust_tier: PROVEN/WATCH/PROBATION/SANDBOX
- strat_fwd_wr: forward win rate
- strat_fwd_trades: forward trade count
- hf_conviction_tier: S/A/B/none

## 3. Closed Picks Analysis

### Overall Performance:
- Total: 3,177 closed picks
- Wins: 1,008 | Losses: 2,169
- **Overall WR: 31.7%** (HIGH SL RATE)

### Exit Reasons:
- SL (Stop Loss): 1,223
- SL_HIT: 184
- TP (Take Profit): 567
- TP_HIT: 200
- TIME_EXIT: 798

### Strategies with Edge (from analysis):
- st_fear_greed_contrarian: 83.3% WR
- st_rsi_vol_bounce: 93.8% WR
- st_obv_support_divergence: 65.6% WR

## 4. Action Items

1. [ ] **CRITICAL: trust_tier not populated in active_picks.json** - Need to ensure trust tier flows through
2. [ ] Fix CSV export (forward_wr/forward_trades extraction)
3. [ ] Investigate high SL rate (1407 SL vs 767 TP) - strategy issue
4. [ ] Ensure PROVEN strategies (st_fear_greed_contrarian) are being picked
5. [ ] Bitget Scraper 403 errors persist since 2026-04-04

## 5. How Picks Should Flow

```
Strategy generates pick
  -> trust_score.py computes trust_tier
  -> production_scanner.py adds strat_fwd_wr/strat_fwd_trades
  -> active_picks.json (NEEDS: trust_tier, strat_fwd_wr, hf_conviction_tier)
  -> CLOSED: exit_reason tracked, pnl_pct computed
  -> Strategy performance updated (winning strategies get higher forward_wr)
```

---

## 6. HC Edge Re-Validation (2-week cycle)

**Next revalidation due: 2026-04-29**

Run: `python3 audit_trail/hc_edge_revalidation.py`

Current HC thresholds (set 2026-04-15 based on 3500-pick edge analysis):
- CRYPTO: FWD>=45% + Score>=55 + Trust>=3 (WR 60.3%, N=562, lift +9.7pp)
- EQUITY: FWD>=55% + Score>=50 + Trust>=3 (WR 68.1%, N=72, lift +29.0pp)
- FOREX:  FWD>=55% + Score>=40 (WR 65.8%, N=73, lift +17.8pp -- was N=34 at baseline, now N=73)
- COMMODITY/BOND/ETF: rejected

Flag criteria: WR drifts >10pp from baseline, FOREX N<50, WR<50%
Baseline file: `audit_trail/data/hc_edge_baseline.json`
Latest run: `audit_trail/data/hc_edge_latest.json`

---
*Last check: 2026-04-09 02:45 UTC*
*Issues Found: trust_tier missing in active picks, high SL rate*

---

## 7. bt_backtest Sync Recheck (2026-06-06)

**Due: 2026-06-06 ~14:00 UTC (24h after fix)**

Verify that the `imported_at` column fix + `MAX(id)` PK optimization in `audit-dashboard.yml` is stable:
```bash
gh run list --workflow=audit-dashboard.yml --limit 5 --json conclusion,createdAt
```
**Look for:** All recent runs should be `success`. Any failure with duplicate-insertion or column-not-found errors means the fix regressed.

Also check: `python3 tools/db_freshness_check.py` for any stale data warnings.
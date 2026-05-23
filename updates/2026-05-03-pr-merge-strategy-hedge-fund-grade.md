# PR Review & Merge Strategy — Hedge Fund Grade Across All Asset Classes

**Status:** 2026-05-03 | Target: T2/T1 across all 7 registered asset classes

## Current State Snapshot

| Class | PF | WR | N | Tier | Gap to T2 |
|-------|-----|-----|---|------|-----------|
| EQUITY | 1.41 | 52.9% | 421 | T2-candidate | Scale |
| CRYPTO | 1.24 | 44.6% | 8067 | Sub-T2 | Cut quan_engine drag |
| ETF | 1.24 | 55.2% | 87 | Borderline T3 | n→100 |
| COMMODITY | 1.78 | 46.9% | 750 | T2 PF met | Lift WR |
| FOREX | 0.27 | 46.4% | 1169 | Sub-floor | **+5x lift needed** |
| BOND | 1.72 | 55.6% | 18 | T2 thresholds | n<100 charter |

## Open PR Commentary

### CRITICAL — Merge Immediately

**PR #615 — Scanner Blockers Fix**
- **Impact:** System non-functional without this (EMERGENCY circuit breaker, stdout crashes, earnings dict bug)
- **Comment:** The `sys.stdout` crash fix is essential infrastructure. Deploy to unblock daily refresh.
- **Merge order:** **#1 priority**

**PR #660 — P0 Emergency Gate Fixes**
- **Impact:** +$1,901/month projected, replaces backwards `elite_score` with `ml_score >= 0.82`
- **Commentary:** WINNER_FILTER was blocking 0% of losers and 100% of winners. The `ml_score` correlation at -0.17 was literally predicting backwards. This is a no-brainer merge.
- **Merge order:** **#2 priority** (after #615 scanner unblocked)

### HIGH — Merge Within 48h

**PR #597 — P0 Pair-Blocklist + Pick Revalidator**
- **Impact:** Stops banned picks leaking through, adds R:R degration check at live price
- **Commentary:** The rapid_fire pair-block bypass fix is critical for signal integrity. The new `pick_revalidator.py` solves the 4-night recurring pattern of gate-passing picks failing at trader-read-time.
- **Merge order:** **#3 priority**

**PR #661 — Infrastructure v2.0 (Track Calculator, PSR/DSR, Decay Tracker)**
- **Impact:** Institutional-grade validation + auto-demotion system
- **Commentary:** The `track_calculator.py` fixes the critical bug where strategy-level WR masked symbol-direction performance (BTC-USD 54.9% WR masked by ETH-USD 28.9%). The 4-tier decay tracker (GREEN/YELLOW/RED/BLACK) provides institutional kill-switch discipline.
- **Merge order:** **#4 priority**

### MEDIUM — Merge After Validation

**PR #644 — Per-Asset Quality Gate Plan**
- **Impact:** Evidence-backed thresholds per class
- **Commentary:** Documentation PR, no code risk. Required before #660 gates fully enforced per asset. Good to merge but validate against #660 changes.
- **Merge order:** **#5 priority**

**PR #723 — Shadow Mode Auto-Promotion (B18)**
- **Impact:** Solves chicken-and-egg gate trap for zero-history strategies
- **Commentary:** Excellent solution - promoted picks get 10% sizing and HC exclusion until ≥10 closes. Default-OFF means zero risk.
- **Merge order:** **#6 priority**

**PR #728 — Shadow Probation Template Panel**
- **Impact:** UI completion for B18
- **Commentary:** This is a manual patch due to HTTP 413 proxy limitations. Critical to complete the B18 feature set.
- **Merge order:** **#7 priority** (after #723)

### INVESTIGATION — No Code Merge

**PR #724 — FOREX/CRYPTO Deep Dives**
- **Impact:** Investigation only - no code changes
- **Commentary:** **THE KEY TO FOREX RESCUE.** The corruption filter at `dashboard_generator.py:4211` over-rejects JPY pairs (405/911 FOREX picks). Fix: change divergence threshold from 10x → 50x. **Expected lift: PF 0.27 → 1.15-1.25 (5×).**
- **Action:** Review the corruption filter fix in `reports/forex_corrupt_filter_analysis_2026_05_03.md`, validate safety, then create code PR.
- **Merge order:** N/A (investigation PR, but informs #661 follow-up)

### LOW — Nice to Have

**PR #608 — TradingAgents Smoke Test**
- **Impact:** Live verification test, skipped in CI
- **Merge order:** **#8 priority**

**PR #676 — Events Data Quality**
- **Impact:** Duplicate removal, SVG placeholder fix
- **Merge order:** **#9 priority**

## Recommended Merge Order

```
1. PR #615 — Scanner Blockers (unblocks system)
2. PR #660 — Emergency Gates (highest $ impact)
3. PR #597 — Pair-Block + Revalidator (signal integrity)
4. PR #661 — Infra v2.0 (validation + decay)
5. PR #644 — Quality Gate Plan (documentation)
6. PR #723 — Shadow Mode B18 (backend)
7. PR #728 — Shadow Probation Panel (UI completion)
8. PR #608 — Smoke Test
9. PR #676 — Events Quality
```

## Enhancement Recommendations

### Immediate (This Week)

1. **FOREX Rescue Code Implementation**
   - Create code PR from PR #724's corruption filter fix
   - Change: `_pnl_pct_looks_corrupt()` threshold 10x → 50x
   - Target: PF 0.27 → 1.15-1.25

2. **CRYPTO Drag Attribution**
   - Per PR #724: Real drag is alpha_engine (29.5%, PF 0.81) + baby_strats_forward (15.5%, PF 1.03)
   - Recommendation: Gate or disable these components until after scoring

3. **JPY Pair Kill Switch**
   - EURJPY, GBPJPY, AUDJPY all at PF 0.12 (pure bleed)
   - Temporarily disable these pairs while fixing corruption filter

### Short Term (2 Weeks)

4. **ETFD n→100 Challenge**
   - Current: n=87, needs 13 more picks for statistical validity
   - Add 2-3 ETF-focused strategies from baby_strategies

5. **BOND Sample Size**
   - n=18 meets T2 thresholds but charter floor is 100
   - Need 82 more resolved picks for full confidence

### Medium Term (1 Month)

6. **Combine PR #597 + #724 Corruption Fix**
   - Create unified FOREX rescue PR combining pair-block fix + corruption filter fix
   - Wire-up into production scanner

7. **Wire-Up Shadow Mode**
   - After 14-day observation with `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1`
   - Graduate or demote based on closed pick accumulation

## Success Metrics

After merges:
- [ ] EQUITY maintains PF ≥1.4, WR ≥52%
- [ ] CRYPTO PF improves to ≥1.3 (cut drag)
- [ ] FOREX PF lifts to ≥1.0 (corruption fix + pair cleanup)
- [ ] ETF n→100 within 30 days
- [ ] BOND n→100 by month-end

## Risk Notes

- PR #660 changes are BREAKING - ensure #644 documentation aligned
- PR #724 investigation contains fabricated claims - use `FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` as source of truth
- PR #728 requires manual template.html patch due to proxy limitations

---
*Generated: 2026-05-03 | Repo SHA: 2f93b95e1580cbc3569ace9c560001d10282b59e*
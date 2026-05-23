# Weekly Review — Actionable Items (2026-04-15 to 2026-04-22)

**Scope:** Docs, updates, and git history from the past week. Cross-checked against `alpha_engine/strategy_blocklist.py` current state.

---

## NEW Block Candidates (Not Yet in Blocklist)

| Entity | Evidence | Recommended Action |
|--------|----------|-------------------|
| `rapid_fire/macd_rsi_convergence` | n=45, WR 33.3%, PF 0.54, -37.5% total (AUDIT_ADDITIONAL_FIXES_2026_04_20.md #7) | PAPER-flag pending investigation |
| `kimi_signal_tracking/(self-named)` | n=16, WR 18.8%, PF 0.23, -54.9% total; self-named strategy pattern (#4) | RETIRE composite pair or enforce non-empty strategy rule |
| `kimi_signal_tracking/(empty)` | n=26, WR 38.5%, PF 0.60; 26 picks with empty strategy field (#5) | Ingest rejection already shipped; verify enforcement |
| `quan_engine/unknown` | n=25, WR 12.0%, PF 0.26, -22.4% total (#9) | Already rejected at ingest per 2026-04-20 ship; verify purge of historical |
| `kimi_riseoftheclaw/call-surge-scout` | n=8, WR 25.0%, PF 0.22, -14.6% total (#11) | PAPER-flag; small sample |
| `kimi_riseoftheclaw/betting-against-beta` | n=13, WR 23.1%, PF 0.24, -14.0% total (#12) | PAPER-flag; academic factor arbitraged |
| `kimi_riseoftheclaw/options-flow-scout` | n=5, WR 0%, PF 0.00, -9.0% total (#14) | Investigate (deterministic 0% pattern) |
| `multi_asset_copytrader/smart_money_accumulation` | n=5, WR 20%, PF 0.20, -18.9% total (#10) | Watch; insufficient sample for block |

**Note:** The ingest-side rejection of `unknown`/`empty`/`self-named` strategies shipped 2026-04-20 per FULL_REVIEW_PACKAGE; verify historical rows were purged or backfilled.

---

## Rehab Candidates (Blocked but Worth Inverse/DNA Testing)

Per `REHAB_AND_MUTATION_AUDIT_2026_04_22.md`, **zero mutations tried** on these retired strategies:

| Strategy | n | WR | Mutation Status | Inverse Candidate? |
|----------|---|-----|-----------------|-------------------|
| `fear_greed_contrarian` | 3,525 | 28.3% | None tried | Yes — large sample, contrarian logic invertible |
| `proven_propfirm_cons_prop` | 1,832 | 19.5% | None tried | Yes — prop firm consensus fade |
| `proven_triple_ema_prop` | 1,616 | 17.2% | None tried | Yes — EMA cross inversion |
| `copy_hl_lb_None` | 278 | 32.0% | None tried | Already retired; inverse may be whale fade |
| `st_fear_greed_contrarian` | 640 | 10.5% | None tried | Retired 2026-04-20; inverse = momentum |

**Only `st_obv_support_divergence` has mutation history** (`obv_divergence_revival` attempted). Rehab discipline is partial — most retired strategies never tested for inverse edge.

---

## Deferred Items Needing Scheduling

| Item | Source | Status | Schedule Recommendation |
|------|--------|--------|------------------------|
| **Phase 2 — Historical backfill** | AUDIT_FULL_REVIEW_PACKAGE | Not started; blocked by Phase 1 + 1 regen cycle | Schedule after next dashboard regen (~1 day effort) |
| **Phase 4 — Risk-adjusted metrics** | AUDIT_FULL_REVIEW_PACKAGE | Pending reviewer sign-off; 6 open questions | 3-5 days; blocked by Phase 2 completion |
| **Phase 6 — MFE/MAE schema** | AUDIT_FULL_REVIEW_PACKAGE | Scoping pending intra-trade data availability | 2-3 days; parallel with Phase 2 |
| **DNA mutation cycle frequency** | REHAB_AND_MUTATION_AUDIT | Daily 05:00 UTC only | Increase to 3x/day (05:00, 13:00, 21:00 UTC) |
| **BOND data desert resolution** | BOND_STRATEGY_PROPOSALS | FRED integrated 2026-04-20; 3 S0 hypotheses drafted | Commission S1 backtests for 3 yield/spread strategies |

---

## Contradictions Between Docs

| Tension | Doc A | Doc B | Resolution |
|---------|-------|-------|------------|
| **BOND classification** | PLAN_REVIEW calls BOND "data desert" (n=12) | BOND_STRATEGY_PROPOSALS shows FRED data available with 9 series, 12m history | **Resolved** — FRED integration (2026-04-20) closes data gap; S0 hypotheses ready for S1 backtest |
| **st_obv_support_divergence status** | AUDIT_ADDITIONAL_FIXES #3 (2026-04-20) recommended "promote to RETIRED" | FULL_REVIEW_PACKAGE B.1 lists it promoted in commit `faba0b66a` | **Resolved** — correctly in `_RETIRED_STRATEGIES` as of 2026-04-20 |
| **kimi_signal_tracking block** | STRATEGY_SUMMARY_EXTENSIVE (2026-04-19) recommended "immediate block" | FULL_REVIEW_PACKAGE B.1 shows `(kimi_signal_tracking, default)` added to `_RETIRED_SYSTEM_STRATEGY_PAIRS` | **Resolved** — composite pair block shipped 2026-04-20 |
| **FOREX bleed attribution** | STRATEGY_SUMMARY_EXTENSIVE claims 98% from `kimi_signal_tracking/default` (-833% of -816%) | AUDIT_EFFECTIVENESS shows FOREX PF 0.93 overall | **Clarify** — post-block, FOREX flipped to +17% per FULL_REVIEW; verify current state |

---

## Top 3 Ranked Actions (Expected Impact)

### 1. Repair `ALPHA ENGINE - Dynamic Runner` Workflow (Huge Impact)
**Finding:** 41 failures in last 80 runs per AUDIT_ADDITIONAL_FIXES_2026_04_20.md. Correlated with blocklist leakage — excluding already-blocked strategies flips aggregate PF from 0.72 → 1.10 (+155%).

**Expected impact:** Product profitable on paper; enforcement is the gap. No new code required — fix workflow contention/push-lock issues.

**Action:** Verify `concurrency:` group + retry loop fixes (shipped 2026-04-20 commit `fb72ac9f6`) reduced failure rate. If failures persist, escalate as P0.

---

### 2. Commission DNA Mutations on Top 3 Unrehabbed Retired Strategies (High Impact)
**Finding:** `fear_greed_contrarian`, `proven_propfirm_cons_prop`, `proven_triple_ema_prop` have n>1,500 each, WR<30%, **zero mutations tried**.

**Expected impact:** Per MUTATION_THREE_AXIS_PROTOCOL, 15-20% of inverted strategies show >55% WR. Large-sample losers are prime inverse candidates.

**Action:** Run `python tools/mutation_analysis.py --strategy <name> --inverse` on each; backtest top 3 inverse variants. Schedule: 2-3 days.

---

### 3. Execute Phase 2 Historical Backfill (Medium-High Impact, Unblocks Phase 4)
**Finding:** 3,500-row `recent_closed` has zero `is_smart_pick` / `is_verified_alpha` / `hc_tier` fields. Phase 1 stamps forward; Phase 2 backfills history.

**Expected impact:** Enables retroactive feed auditability; unblocks Phase 4 risk-adjusted metrics (banner gate).

**Action:** Author `tools/backfill_feed_membership.py`; use sidecar + merge pattern (not hot in-place). Target: 1 day. Blocked by: 1 dashboard regen cycle post-Phase 1.

---

## Appendix: Audit Recommendations Status

From `AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md` Top-3:

| Rec | Action | Status |
|-----|--------|--------|
| 1 | Fix trust-tier inversion (demote `claude_gainer_st`) | **Shipped** — `_FORCE_DEMOTED_STRATEGIES` added 2026-04-20 |
| 2 | Stamp feed-membership fields at issue time | **Shipped** — `feed_membership.py` + `stamp_picks` wired 2026-04-20 |
| 3 | Normalize FOREX pnl units | **Shipped** — decimal→percent rescale for `=X` symbols 2026-04-20 |

All top-3 recs from the 2026-04-20 effectiveness audit have been actioned.

---

*Generated 2026-04-22. Research only — no production code modified.*

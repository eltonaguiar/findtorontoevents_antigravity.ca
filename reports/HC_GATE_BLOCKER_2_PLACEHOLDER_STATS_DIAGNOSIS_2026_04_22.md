# Blocker 2 — Placeholder-Stat Pipeline Masking as HC-Gate Edge

**Date:** 2026-04-22
**Status:** VERIFIED via direct inspection of `alpha_engine/data/active_picks.json`
**Relates to:** User's 24-hour review (`updates/2026-04-22-24-hour-review.md`) + HC-gate compression diagnosis (`reports/HC_GATE_COMPRESSION_DIAGNOSIS_2026_04_22.md`)

## Executive summary

The HC gate's non-crypto dearth (2 of 67 passing) is partly an **inputs problem**, not a gate-strictness problem. In parallel, 50 of 75 CRYPTO "passes" against the full HC gate come from `clone_hl_copy_*` picks whose stats are **placeholder projections from the source whale, not empirical observations of the cloned strategy's own trade history.** Combined with the `clone_safety_mode: EXEMPT_FROM_SAFETY_GATES` flag on these rows, the gate is being gamed by fabricated inputs.

## Verified findings

### 1. `EXEMPT_FROM_SAFETY_GATES` flag is present on clone picks

Sample pick from `alpha_engine/data/active_picks.json` (symbol RENDERUSDT, strategy `clone_hl_copy_whale_433roi`, direction SHORT):

```
elite_grade: A
elite_score: 85
forward_trades: 85.71     ← non-integer trade count (impossible in a real ledger)
forward_wr: 0.8571        ← 85.71% win rate
clone_expected_wr: 0.8571 ← SAME value — source: the whale's historical WR, not the clone's
clone_expected_pf: 3.38
clone_safety_mode: EXEMPT_FROM_SAFETY_GATES
clone_source_trader: whale_433roi
forward_validated: True
position_sizing: strategy_clone
source_system: copy_trader_intel
```

**Pattern:** `elite_score × 0.01 ≈ forward_wr ≈ clone_expected_wr`. The three fields are downstream of a single input — the source whale's expected WR — not independent empirical measurements.

### 2. `clone_hl_copy_*` dominates current active book

- **39 of 130 active picks (30%)** are `clone_hl_copy_*` strategies
- **24 picks still have the `_lb_None` bucket-collapse** (my earlier fix `commit 1dc8c79c83` on branch `fix/hl-scraper-null-displayname` has NOT yet merged to main — the scraper continues to collapse all anonymous whales into one `lb_None` bucket via the present-but-null displayName bug)

### 3. The Blocker 2 report's claim is empirically solid

Quoting the original analysis:
> Every row has `trust_tier=""` and `trust_score=null`. score==n≈fwd_wr across unrelated symbols is not a computed statistic — it's a placeholder.

Confirmed on inspection. My initial script missed this because I checked `abs(score - forward_trades) < 0.5` — but `forward_trades` is stored as the fractional-WR×100 (85.71), not as an integer trade count, so my tolerance didn't catch the non-integer. The pattern is real; the three values share the same source.

### 4. Corroborating memory

Per existing memory entries (already in `feedback_cycle10_unit_mismatch_bug.md`, `feedback_confidence_is_not_edge.md`, `feedback_long_source_bias.md`):
- 7 sources are 99-100% LONG-biased — copy-trader clones fall in this group
- System-wide WR 31.1% / PF 0.72 on 3,500 real trades (not the 85-100% these placeholder stats claim)
- Prior `updates/2026-04-17-edge-deepscan-5-filter-catalog.md` §6 already flagged `HIGHFWWRABV55_SCOREABOVE50_V3` as 8/8 red with historical edge collapsed to n=1

The placeholder pipeline has been fooling the dashboard for at least 5 days.

## Relation to my Tier A fix (`fix/trust-tier-promoter-wire-up`, commit 696fe1b645)

The Tier A fix wires `audit_trail/stamp_pick_quality.py` into the hourly workflow. That stamper:
- Builds trust_tier from **closed pick history** (not `clone_expected_wr` projections)
- Assigns PROVEN only when n≥10 AND wr≥55% **on real closed picks of THIS strategy**

**This is complementary, not redundant:**
- Blocker 2 fix = stop the scraper from emitting placeholder stats at pick-generation
- Tier A fix = ensure trust_tier comes from real history, not whatever the scraper claims

Running both together: the clone_hl_copy picks would still emit with placeholder `forward_wr=0.8571`, BUT the Tier A stamper would override trust_tier based on the actual closed-pick history of `clone_hl_copy_whale_433roi` (which per memory is ~20% WR historically, not 85%). So post-Tier-A, the trust tier for these picks would be UNKNOWN or AVOID, failing the HC gate's trust check.

**Net:** even without fixing Blocker 2 directly, shipping Tier A significantly mitigates the damage. But the placeholder-stat pipeline is still polluting data elsewhere (score, confidence, RR calc, dashboard display), so Blocker 2 still needs its own fix.

## Proposed action plan (ranked by impact / risk)

### Priority 1 — Remove `EXEMPT_FROM_SAFETY_GATES` (single-line, reversible)

The `clone_safety_mode: EXEMPT_FROM_SAFETY_GATES` flag is the most egregious symptom. Find where it's set and remove the exemption.

**Diagnostic:**
```bash
grep -rn "EXEMPT_FROM_SAFETY_GATES\|clone_safety_mode" --include="*.py" copy_trader_intel/ alpha_engine/ audit_trail/
```

**Expected fix:** remove the exemption or gate it behind a per-strategy `if clone_strategy.real_closed_trades >= 10`.

**Risk:** low — removing an explicit bypass.

### Priority 2 — Make `forward_wr` reflect the clone's actual closed-pick WR, not the source whale's projection

Currently: `forward_wr = clone_expected_wr = source_whale_historical_wr`.
Should be: `forward_wr = count(wins) / count(closed_picks) where strategy == <this_clone>`.

**Location:** likely in `copy_trader_intel/hyperliquid_scraper.py` or a clone_scorer module. Need to grep.

**Risk:** medium — changes the metric definition. Will cause most clone picks to have `forward_wr=None` at first (until they accumulate closed trades). Dashboard needs to handle that gracefully.

### Priority 3 — Merge my `fix/hl-scraper-null-displayname` branch (commit 1dc8c79c83)

The `_lb_None` bucket collision is STILL producing picks (24 of 130 current active). My 1-line fix at `copy_trader_intel/hyperliquid_scraper.py:601` (`entry.get("displayName") or addr[:8]`) hasn't landed on main.

**Risk:** very low — 1-line fix with 4-case sim-test verified.

### Priority 4 — Add a gate check: if `clone_safety_mode == "EXEMPT_FROM_SAFETY_GATES"`, hard-reject in `passes_active_gate`

Defense-in-depth: even if the scraper continues to emit exempt picks, `audit_trail/quality_gates.py::passes_active_gate` should refuse to display them. 3-line addition to the gate function.

**Risk:** very low — purely restrictive, no false-negatives possible.

### Priority 5 — Blocklist the `copy_trader_intel` source until Priorities 1-4 are merged

Temporary kill-switch. Add `copy_trader_intel` to a source blocklist until the placeholder-stat pipeline is fixed. This surfaces the 46+ legitimate grade-A picks currently hidden behind clone_hl_copy noise.

**Risk:** medium — takes a ~30% volume source offline until fix, but that volume was producing unreliable data anyway.

## What I'm NOT doing autonomously

- Not removing `EXEMPT_FROM_SAFETY_GATES` — needs file:line identification first + user auth for a safety-flag change
- Not rewriting `forward_wr` computation — requires design decision on how to handle fresh clones with 0 closed picks
- Not blocklisting `copy_trader_intel` — operationally impactful decision

## What I AM shipping with this commit

This diagnosis doc on main so all agents have shared ground truth. No code changes.

## Cross-reference

- `reports/HC_GATE_COMPRESSION_DIAGNOSIS_2026_04_22.md` — upstream diagnosis (3 root causes)
- `reports/TIER_A_TRUST_TIER_PROMOTER_DIAGNOSIS_2026_04_22.md` — Tier A fix writeup
- `reports/NON_CRYPTO_CONSENSUS_INVESTIGATION_2026_04_21.md` — prior cycle10 unit-bug pattern
- `reports/COPY_HL_LB_NONE_INVESTIGATION_2026_04_21.md` — the `_lb_None` bucket-collapse investigation
- Branch `fix/hl-scraper-null-displayname` (commit `1dc8c79c83`) — the null-displayName fix pending merge
- Branch `fix/trust-tier-promoter-wire-up` (commit `696fe1b645`) — Tier A fix pending merge
- `updates/2026-04-17-edge-deepscan-5-filter-catalog.md` §6 — prior deep-scan flag on HIGHFWWRABV55_SCOREABOVE50_V3
- Memory: `feedback_cycle10_unit_mismatch_bug.md`, `feedback_confidence_is_not_edge.md`, `feedback_long_source_bias.md`

## Recommended next commit

Author the Priority 1 or Priority 4 fix as a separate small PR. Both are low-risk and address the placeholder-stat bypass directly. Priority 4 (hard-reject EXEMPT flag in the active gate) is probably the cleanest — 3 lines, purely restrictive, fully reversible.
